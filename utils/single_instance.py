"""
单实例控制模块

基于 QLocalServer/QLocalSocket（本地命名管道）实现单例：
- 首个实例监听固定管道名；
- 后续实例启动时检测到已有实例在运行，通知其显示主窗口后自行退出。

已知限制：本地同用户进程可调用 removeServer 抢占管道名，使后续实例误判已有实例在
运行（DoS 级风险；管道内不传输敏感数据，接受该风险）。

用法（main.py）：

    _single_server = listen_single_instance(window.show_from_tray)
    if _single_server is None:
        return  # 已有实例在运行，本进程直接退出
    window.show()
"""

import time
from collections.abc import Callable

from PySide6.QtCore import QCoreApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket

SERVER_NAME = "qzct-login-single-instance"

# 等待"show"消息写入管道的最长时间（秒）。写缓冲正常毫秒级排空；
# 超过该时长说明管道异常，此时放弃等待直接断开，避免二次启动卡住。
_SEND_TIMEOUT_SEC = 1.0


def listen_single_instance(show_callback: Callable[[], None]) -> QLocalServer | None:
    """尝试成为单例监听者。

    Args:
        show_callback: 收到"显示主窗口"请求时调用（无参数回调）

    Returns:
        QLocalServer | None:
            - 本进程成为唯一实例：返回服务器对象（调用方需持有引用防止被回收）
            - 已有实例在运行：通知对方显示主窗口后返回 None（调用方应直接退出）
            - 极端情况下监听失败：返回 None
    """
    # 先探测是否已有实例在监听
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if socket.waitForConnected(200):
        # 已有实例：发送"显示"通知后断开。
        # 必须等写缓冲真正排空再断开，否则 disconnectFromServer 会丢弃尚未
        # 写入管道的数据，用户双击图标唤不起已运行实例的窗口。
        # 排空只能靠 processEvents 推进（实测 QLocalSocket.waitForBytesWritten
        # 在 Windows 上返回 False 且不减少 bytesToWrite），因此等待用**墙钟截止**
        # 而非固定轮次：事件队列繁忙时每轮 processEvents 可能被其他事件占用，
        # 固定 10 轮会在消息尚未发出时提前放弃（该缺陷在测试套件加速后才稳定复现）。
        socket.write(b"show")
        socket.flush()
        app = QCoreApplication.instance()
        deadline = time.monotonic() + _SEND_TIMEOUT_SEC
        while socket.bytesToWrite() > 0 and time.monotonic() < deadline:
            if app is None:
                break
            app.processEvents()
            time.sleep(0.002)
        socket.disconnectFromServer()
        return None

    # 清理可能残留的陈旧管道后开始监听
    QLocalServer.removeServer(SERVER_NAME)
    server = QLocalServer()
    if not server.listen(SERVER_NAME):
        return None

    def _on_new_connection() -> None:
        """收到连接请求：读取并校验消息，仅当任一连接发送 "show" 时才显示主窗口。

        该路径仅在第二个实例启动时发生，短暂阻塞等待消息可接受；
        其余消息（含空消息）一律忽略，防止本地任意进程连接即抢夺焦点。
        """
        should_show = False
        while server.hasPendingConnections():
            conn = server.nextPendingConnection()
            if conn is None:
                continue
            # 客户端写完消息后才断开，150ms 足够取到完整消息
            conn.waitForReadyRead(150)
            # QByteArray.data() 直接返回 bytes（bytes(QByteArray) 在真实存根下无匹配重载）
            data = bytes(conn.readAll().data())
            conn.disconnectFromServer()
            if data.strip() == b"show":
                should_show = True
        if should_show:
            show_callback()

    server.newConnection.connect(_on_new_connection)
    return server
