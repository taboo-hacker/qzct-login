"""
基础列表编辑器组件

提供通用的表格 + 增删改清 CRUD 骨架，子类只需实现数据操作钩子。
"""

from typing import Any

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.styling.widgets import create_button, create_section_title, create_tip_label


class BaseListEditorWidget(QWidget):
    """带表格的列表编辑器基类。

    子类需实现以下方法：
        - _get_items() -> List[dict]:  返回当前行数据列表
        - _set_items(items):           写回行数据列表
        - _row_to_cells(item) -> list: 将一行数据转为 QTableWidgetItem 列表
        - _add_item():                 添加一行（子类自定义交互）
        - _edit_item(row):             编辑指定行
        - _get_delete_confirm_text() -> str
        - _get_clear_confirm_text() -> str
        - _sort_items(items):          排序（可选，默认不排序）
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        title: str = "",
        tip: str = "",
        columns: list[str] | None = None,
    ) -> None:
        super().__init__(parent)
        self._columns = columns or []
        self.table: QTableWidget | None = None
        self._init_ui(title, tip)

    def _init_ui(self, title: str, tip: str) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(16, 16, 16, 16)

        if title:
            header_layout = QVBoxLayout()
            header_layout.setSpacing(5)
            header_layout.addWidget(create_section_title(title))
            if tip:
                header_layout.addWidget(create_tip_label(tip))
            main_layout.addLayout(header_layout)

        self._setup_edit_area(main_layout)
        self._setup_table(main_layout)
        self._setup_button_bar(main_layout)
        self.refresh()

    def _setup_edit_area(self, layout: QVBoxLayout) -> None:
        """编辑区域 — 子类可覆盖以添加自定义输入控件。"""
        pass

    def _setup_table(self, layout: QVBoxLayout) -> None:
        """创建数据表格：整行选择、禁用双击编辑（编辑走对话框）、列等宽拉伸。"""
        self.table = QTableWidget()
        self.table.setColumnCount(len(self._columns))
        self.table.setHorizontalHeaderLabels(self._columns)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        assert header is not None
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setVisible(False)
        self.table.setAlternatingRowColors(True)
        # 双击行等同点"编辑"（表格本身禁用单元格直接编辑，编辑走对话框）
        self.table.cellDoubleClicked.connect(lambda row, _col: self._edit_item(row))
        layout.addWidget(self.table)

    def _setup_button_bar(self, layout: QVBoxLayout) -> None:
        """创建底部按钮栏：添加 / 编辑 / 删除 …… 清空所有。"""
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        add_btn = create_button("\u2795 添加", btn_type="success", min_width=100)
        add_btn.clicked.connect(self.add_item)
        btn_layout.addWidget(add_btn)

        edit_btn = create_button("\u270f\ufe0f 编辑", btn_type="primary", min_width=100)
        edit_btn.clicked.connect(self.edit_item)
        btn_layout.addWidget(edit_btn)

        delete_btn = create_button("\u274c 删除", btn_type="danger", min_width=100)
        delete_btn.clicked.connect(self.delete_item)
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()

        clear_btn = create_button("\U0001f5d1\ufe0f 清空所有", btn_type="gray", min_width=100)
        clear_btn.clicked.connect(self.clear_all)
        btn_layout.addWidget(clear_btn)

        layout.addLayout(btn_layout)

    # ------------------------------------------------------------------
    # 表格刷新
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """从数据源重新加载表格内容。"""
        if self.table is None:
            return
        self.table.setRowCount(0)
        for row, item in enumerate(self._get_items()):
            self.table.insertRow(row)
            for col, cell in enumerate(self._row_to_cells(item)):
                self.table.setItem(row, col, cell)

    # ------------------------------------------------------------------
    # CRUD 操作（模板方法，调用子类钩子）
    # ------------------------------------------------------------------

    def add_item(self) -> None:
        """添加按钮入口：调用子类 _add_item 后统一排序刷新。"""
        self._add_item()
        self._post_modify()

    def edit_item(self) -> None:
        """编辑按钮入口：需先选中一行，调用子类 _edit_item 后刷新。"""
        if self.table is None:
            return
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "提示", self._get_select_warning_text())
            return
        self._edit_item(selected[0].row())
        self._post_modify()

    def delete_item(self) -> None:
        """删除按钮入口：删除选中行（无二次确认，删除单行影响小）。

        删除后把选中移动到相邻行，连续删除多行时不必反复点选。
        """
        if self.table is None:
            return
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "提示", self._get_select_warning_text())
            return
        row = selected[0].row()
        items = self._get_items()
        items.pop(row)
        self._set_items(items)
        self._post_modify()
        self._select_row(min(row, len(items) - 1))

    def _select_row(self, row: int) -> None:
        """选中指定行（表格为空或行号越界时不做任何事）。"""
        if self.table is None or not 0 <= row < self.table.rowCount():
            return
        self.table.selectRow(row)

    def clear_all(self) -> None:
        """清空按钮入口：弹确认框后清空全部数据（破坏性操作需确认）。"""
        reply = QMessageBox.question(
            self,
            "确认",
            self._get_clear_confirm_text(),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            # 破坏性操作默认聚焦"否"，防止回车误触清空全部数据
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._set_items([])
            self._post_modify()

    def _post_modify(self) -> None:
        """修改数据后的统一处理：排序 + 刷新。"""
        items = self._get_items()
        sorted_items = self._sort_items(items)
        if sorted_items is not None:
            self._set_items(sorted_items)
        self.refresh()

    # ------------------------------------------------------------------
    # 子类必须实现的钩子（数据源绑定 + 行为定制）
    # ------------------------------------------------------------------

    def _get_items(self) -> list[Any]:
        """返回表格数据源列表（子类从自身状态/配置提供）。"""
        raise NotImplementedError

    def _set_items(self, items: list[Any]) -> None:
        """整体写回数据源（增删/排序/清空后调用）。"""
        raise NotImplementedError

    def _row_to_cells(self, item: Any) -> list[QTableWidgetItem]:
        """把一条数据渲染为一行单元格（列数须与 columns 一致）。"""
        raise NotImplementedError

    def _add_item(self) -> None:
        """添加一条数据（子类自定义交互，如内联表单或弹窗）。"""
        raise NotImplementedError

    def _edit_item(self, row: int) -> None:
        """编辑指定行（通常弹出编辑对话框后写回）。"""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # 子类可覆盖的可选钩子
    # ------------------------------------------------------------------

    def _sort_items(self, items: list[Any]) -> list[Any] | None:
        """排序钩子，返回排序后的列表或 None 表示不排序。"""
        return None

    def _get_select_warning_text(self) -> str:
        """未选中行点编辑/删除时的提示文案。"""
        return "请先选择要操作的行"

    def _get_clear_confirm_text(self) -> str:
        """清空按钮的确认文案。"""
        return "确定要清空所有数据吗？"
