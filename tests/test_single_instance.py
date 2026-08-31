"""
utils/single_instance.py 测试

单实例控制：首个实例监听，后续实例触发显示回调并返回 None。
基于 QLocalServer/QLocalSocket 本地命名管道实现，测试使用真实管道通信
（第一个用例创建 server，其余用例在其后模拟"二次启动"场景）。
契约：服务端仅当连接写入 b"show" 消息时才触发显示回调，其余消息（含空）忽略。
"""

from PySide6.QtNetwork import QLocalSocket
from PySide6.QtWidgets import QApplication

from tests.conftest import ensure_qapp as _ensure_qapp


def _pump_events(times: int = 20) -> None:
    """手动泵事件循环，使 QueuedConnection 投递的 newConnection 信号送达回调。"""
    for _ in range(times):
        QApplication.processEvents()


def _flush_client(client: QLocalSocket) -> None:
    """泵事件循环直至客户端写缓冲清空，确保消息真正写入命名管道。

    Windows 下 QLocalSocket 的阻塞等待不会推进写缓冲，直接断开可能丢弃数据。
    """
    while client.bytesToWrite() > 0:
        QApplication.processEvents()


class TestSingleInstance:
    """单实例机制测试：覆盖"首实例监听成功"、"第二实例通知退出"与消息校验场景。"""

    def test_first_instance_listens(self) -> None:
        """无已有实例时首次监听成功，应返回非 None 的服务器对象。"""
        _ensure_qapp()
        from utils.single_instance import listen_single_instance

        server = listen_single_instance(lambda: None)
        assert server is not None
        server.close()

    def test_second_instance_notifies_and_returns_none(self) -> None:
        """已有实例占用管道时，第二次调用应返回 None 并触发首实例的显示回调。"""
        _ensure_qapp()
        from utils.single_instance import listen_single_instance

        shown: list[str] = []
        server = listen_single_instance(lambda: shown.append("show"))
        assert server is not None

        # 模拟二次启动：传入的回调不应被调用（第二实例直接返回 None）
        second = listen_single_instance(lambda: shown.append("never"))
        assert second is None

        # newConnection 信号经 QueuedConnection 投递，需手动泵事件循环才能送达回调
        _pump_events()

        assert shown == ["show"]
        server.close()

    def test_show_message_triggers_callback(self) -> None:
        """客户端连接并写入 b"show" 消息时，应触发首实例的显示回调。"""
        _ensure_qapp()
        from utils.single_instance import SERVER_NAME, listen_single_instance

        shown: list[str] = []
        server = listen_single_instance(lambda: shown.append("show"))
        assert server is not None

        client = QLocalSocket()
        client.connectToServer(SERVER_NAME)
        assert client.waitForConnected(200)
        client.write(b"show")
        client.flush()
        _flush_client(client)
        client.disconnectFromServer()

        _pump_events()
        assert shown == ["show"]
        server.close()

    def test_garbage_or_empty_message_ignored(self) -> None:
        """客户端写入非法消息或不写消息时不触发显示回调（防任意进程抢夺焦点）。"""
        _ensure_qapp()
        from utils.single_instance import SERVER_NAME, listen_single_instance

        shown: list[str] = []
        server = listen_single_instance(lambda: shown.append("show"))
        assert server is not None

        # 场景 1：连接并写入非法消息（确保送达服务端，验证消息内容被校验）
        garbage = QLocalSocket()
        garbage.connectToServer(SERVER_NAME)
        assert garbage.waitForConnected(200)
        garbage.write(b"garbage")
        garbage.flush()
        _flush_client(garbage)
        garbage.disconnectFromServer()

        # 场景 2：连接后不写入任何消息
        silent = QLocalSocket()
        silent.connectToServer(SERVER_NAME)
        assert silent.waitForConnected(200)
        silent.disconnectFromServer()

        _pump_events()
        assert shown == []
        server.close()
