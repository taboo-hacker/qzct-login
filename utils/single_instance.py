"""
单实例控制模块

基于 QLocalServer/QLocalSocket（本地命名管道）实现单例：
- 首个实例监听固定管道名；
- 后续实例启动时检测到已有实例在运行，通知其显示主窗口后自行退出。

用法（main.py）：

    _single_server = listen_single_instance(window.show_from_tray)
    if _single_server is None:
        return  # 已有实例在运行，本进程直接退出
    window.show()
"""

from collections.abc import Callable

from PySide6.QtNetwork import QLocalServer, QLocalSocket

SERVER_NAME = "qzct-login-single-instance"


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
        # 已有实例：发送"显示"通知后断开
        socket.write(b"show")
        socket.flush()
        socket.waitForBytesWritten(200)
        socket.disconnectFromServer()
        return None

    # 清理可能残留的陈旧管道后开始监听
    QLocalServer.removeServer(SERVER_NAME)
    server = QLocalServer()
    if not server.listen(SERVER_NAME):
        return None

    def _on_new_connection() -> None:
        """收到连接请求：清理连接并通知调用方显示主窗口。"""
        while server.hasPendingConnections():
            conn = server.nextPendingConnection()
            if conn is not None:
                conn.disconnectFromServer()
        show_callback()

    server.newConnection.connect(_on_new_connection)
    return server
