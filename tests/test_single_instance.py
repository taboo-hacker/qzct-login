"""
utils/single_instance.py 测试

单实例控制：首个实例监听，后续实例触发显示回调并返回 None。
基于 QLocalServer/QLocalSocket 本地命名管道实现，测试使用真实管道通信
（第一个用例创建 server，第二个用例在其后模拟"二次启动"场景）。
"""

from PySide6.QtWidgets import QApplication

from tests.conftest import ensure_qapp as _ensure_qapp


class TestSingleInstance:
    """单实例机制测试：覆盖"首实例监听成功"与"第二实例通知退出"两类场景。"""

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
        for _ in range(20):
            QApplication.processEvents()

        assert shown == ["show"]
        server.close()
