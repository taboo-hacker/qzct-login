"""
utils/single_instance.py 测试

单实例控制：首个实例监听，后续实例触发显示回调并返回 None。
基于 QLocalServer/QLocalSocket 本地命名管道实现，测试使用真实管道通信
（第一个用例创建 server，其余用例在其后模拟"二次启动"场景）。
契约：服务端仅当连接写入 b"show" 消息时才触发显示回调，其余消息（含空）忽略。
"""

import time
from collections.abc import Callable

import pytest
from PySide6.QtNetwork import QLocalSocket
from PySide6.QtWidgets import QApplication

from tests.conftest import ensure_qapp as _ensure_qapp

# 等待管道事件送达的默认超时（秒）：真实失败时快速返回，正常情况毫秒级完成
_WAIT_TIMEOUT_S = 2.0


def _wait_until(predicate: Callable[[], bool], timeout_s: float = _WAIT_TIMEOUT_S) -> bool:
    """泵事件循环直到条件成立或超时，返回条件最终是否成立。

    不能用固定次数的 processEvents 等待：processEvents 不推进墙钟时间，
    当管道数据还在内核缓冲里时，再多的轮次也无济于事——测试会随机器负载
    与套件整体速度随机失败。改用"泵事件 + 短暂睡眠"的截止时间等待，
    既不受机器快慢影响，又能在真正失败时快速返回。
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        QApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.005)
    return predicate()


def _flush_client(client: QLocalSocket, timeout_s: float = _WAIT_TIMEOUT_S) -> None:
    """泵事件循环直至客户端写缓冲清空，确保消息真正写入命名管道。

    Windows 下 QLocalSocket 的阻塞等待不会推进写缓冲，直接断开可能丢弃数据。
    带超时兜底，避免缓冲异常时测试无限挂起。
    """
    _wait_until(lambda: client.bytesToWrite() == 0, timeout_s)


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

        # newConnection 信号经 QueuedConnection 投递，需泵事件循环才能送达回调
        assert _wait_until(lambda: shown == ["show"])
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

        assert _wait_until(lambda: shown == ["show"])
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

        # 负向断言：给足送达时间后仍不应有回调
        assert not _wait_until(lambda: shown != [], timeout_s=0.5)
        server.close()


class TestSecondInstanceDeliveryUnderBusyEventLoop:
    """二次启动的消息送达不受事件队列繁忙影响。

    回归：旧实现用固定 10 轮 processEvents 等待写缓冲排空，而 processEvents
    不推进墙钟时间——事件队列被其他事件占满时每轮都可能被占用，轮次耗尽后
    disconnectFromServer 丢弃尚未写入的数据，用户双击图标唤不起窗口。
    """

    def test_message_delivered_under_starved_event_loop(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """每 20 次 processEvents 才真正处理一次事件时，消息仍应送达。

        用"稀疏泵事件"模拟繁忙事件队列：旧实现的固定 10 轮在此模型下
        一次真实事件处理都拿不到（10 < 20），必然丢弃消息；墙钟截止的实现
        会持续泵到缓冲排空或超时。
        """
        _ensure_qapp()
        import utils.single_instance as si

        shown: list[str] = []
        server = si.listen_single_instance(lambda: shown.append("show"))
        assert server is not None

        class _StarvedApp:
            """模拟事件队列被占满：每 20 次调用才真正处理一次事件。"""

            def __init__(self) -> None:
                self.calls = 0

            def processEvents(self, *args: object, **kwargs: object) -> bool:
                self.calls += 1
                if self.calls % 20 == 0:
                    QApplication.processEvents()
                return True

        # 只影响 single_instance 模块内看到的 QCoreApplication，
        # 测试自身仍可用真实 QApplication 泵事件等待服务端回调
        starved = _StarvedApp()
        monkeypatch.setattr(
            si,
            "QCoreApplication",
            type("_NS", (), {"instance": staticmethod(lambda: starved)}),
        )

        second = si.listen_single_instance(lambda: shown.append("never"))
        assert second is None

        assert _wait_until(lambda: shown == ["show"])
        server.close()
