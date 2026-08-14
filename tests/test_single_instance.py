"""
utils/single_instance.py 测试

单实例控制：首个实例监听，后续实例触发显示回调并返回 None。
"""

from PySide6.QtWidgets import QApplication


def _ensure_qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


class TestSingleInstance:
    """单实例机制测试"""

    def test_first_instance_listens(self):
        """首个实例成功监听，返回服务器对象"""
        _ensure_qapp()
        from utils.single_instance import listen_single_instance

        server = listen_single_instance(lambda: None)
        assert server is not None
        server.close()

    def test_second_instance_notifies_and_returns_none(self):
        """已有实例时返回 None，并触发首个实例的显示回调"""
        _ensure_qapp()
        from utils.single_instance import listen_single_instance

        shown: list[str] = []
        server = listen_single_instance(lambda: shown.append("show"))
        assert server is not None

        second = listen_single_instance(lambda: shown.append("never"))
        assert second is None

        # 事件循环投递 newConnection 信号
        for _ in range(20):
            QApplication.processEvents()

        assert shown == ["show"]
        server.close()
