"""
全局 QSS 样式表生成

统一的简洁商务风样式：卡片、徽标、按钮变体、输入控件、菜单、标签页。
主题切换时由 ThemeManager 重新生成并应用到 QApplication，
使全部窗口与对话框立即重绘（真实主题切换，而非仅记录主题名）。
"""

from gui.styling.themes import ThemeColors


def build_qss(t: ThemeColors) -> str:
    """根据主题配色生成全局样式表。"""
    return f"""
QMainWindow, QDialog, QWidget#appRoot {{
    background: {t.window_bg};
}}
QWidget {{
    color: {t.text_primary};
}}

/* ---- 卡片 ---- */
QFrame#card {{
    background: {t.card_bg};
    border: 1px solid {t.card_border};
    border-radius: 8px;
}}
QFrame#divider {{
    background: {t.card_border};
    border: none;
    max-height: 1px;
}}

/* ---- 标签 ---- */
QLabel {{
    background: transparent;
    color: {t.text_primary};
}}
QLabel[role="cardTitle"] {{
    font-size: 10.5pt;
    font-weight: 600;
}}
QLabel[role="sectionTitle"] {{
    font-size: 9pt;
    font-weight: 600;
    color: {t.text_secondary};
}}
QLabel[role="dateBig"] {{
    font-size: 11pt;
    font-weight: 600;
}}
QLabel[role="muted"] {{
    font-size: 9pt;
    color: {t.text_secondary};
}}
QLabel[role="tip"] {{
    color: {t.text_tertiary};
}}
QLabel[role="badge"] {{
    font-size: 9pt;
    border-radius: 9px;
    padding: 2px 8px;
    font-weight: 600;
}}
QLabel[role="badge"][state="work"] {{
    background: {t.primary_bg};
    color: {t.primary};
}}
QLabel[role="badge"][state="rest"] {{
    background: {t.card_border};
    color: {t.text_secondary};
}}

/* ---- 按钮 ---- */
QPushButton {{
    background: {t.card_bg};
    color: {t.text_primary};
    border: 1px solid {t.input_border};
    border-radius: 5px;
    padding: 4px 10px;
    font-size: 9.5pt;
}}
QPushButton:hover {{
    background: {t.hover_bg};
}}
QPushButton:pressed {{
    background: {t.card_border};
}}
QPushButton:disabled {{
    color: {t.text_tertiary};
    border-color: {t.card_border};
}}
QPushButton[btnType="primary"] {{
    background: {t.primary};
    color: #FFFFFF;
    border: none;
    font-weight: 600;
}}
QPushButton[btnType="primary"]:hover {{
    background: {t.primary_hover};
}}
QPushButton[btnType="primary"]:pressed {{
    background: {t.primary_pressed};
}}
QPushButton[btnType="primary"]:disabled {{
    background: {t.primary_disabled};
    color: #FFFFFF;
}}
QPushButton[btnType="success"] {{
    background: {t.success};
    color: #FFFFFF;
    border: none;
}}
QPushButton[btnType="success"]:hover {{
    background: {t.success_hover};
}}
QPushButton[btnType="success"]:disabled {{
    background: {t.success_bg};
    color: {t.success};
}}
QPushButton[btnType="danger"] {{
    background: {t.danger};
    color: #FFFFFF;
    border: none;
}}
QPushButton[btnType="danger"]:hover {{
    background: {t.danger_hover};
}}
QPushButton[btnType="danger"]:disabled {{
    background: {t.danger_bg};
    color: {t.danger};
}}
QPushButton[btnType="warning"] {{
    background: {t.warning};
    color: #FFFFFF;
    border: none;
}}
QPushButton[btnType="warning"]:hover {{
    background: {t.warning_hover};
}}
QPushButton[btnType="warning"]:disabled {{
    background: {t.warning_bg};
    color: {t.warning};
}}
QPushButton[btnType="gray"] {{
    background: {t.hover_bg};
    color: {t.text_primary};
    border: 1px solid {t.input_border};
}}
QPushButton[btnType="outline"] {{
    background: transparent;
    color: {t.primary_fg};
    border: 1px solid {t.primary_fg};
}}
QPushButton[btnType="outline"]:hover {{
    background: {t.primary_bg};
}}
QPushButton[btnType="outline_danger"] {{
    background: transparent;
    color: {t.danger};
    border: 1px solid {t.danger};
}}
QPushButton[btnType="outline_danger"]:hover {{
    background: {t.danger_bg};
}}
QPushButton[btnType="text"] {{
    background: transparent;
    border: none;
    color: {t.text_secondary};
}}
QPushButton[btnType="text"]:hover {{
    background: {t.hover_bg};
    color: {t.text_primary};
}}
/* 键盘焦点：全局 QSS 会抑制 Fusion 原生焦点矩形，需显式绘制焦点边框。
   规则置于全部按钮变体之后（同特异性时后序生效），使 border: none 的
   实色按钮聚焦时也能显示焦点框；primary_fg 与各按钮底色均不同色。 */
QPushButton:focus {{
    border: 2px solid {t.primary_fg};
}}

/* ---- 输入控件 ---- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit {{
    background: {t.input_bg};
    border: 1px solid {t.input_border};
    border-radius: 4px;
    padding: 3px 6px;
    color: {t.text_primary};
    font-size: 9.5pt;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QDateEdit:focus, QTimeEdit:focus {{
    border: 1px solid {t.primary};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background: {t.card_bg};
    border: 1px solid {t.card_border};
    selection-background-color: {t.primary_bg};
    selection-color: {t.text_primary};
}}
QCheckBox, QRadioButton {{
    background: transparent;
    color: {t.text_primary};
}}

/* ---- 分组与标签页 ---- */
QGroupBox {{
    background: transparent;
    border: 1px solid {t.card_border};
    border-radius: 6px;
    margin-top: 10px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {t.text_secondary};
}}
QTabWidget::pane {{
    border: 1px solid {t.card_border};
    border-radius: 4px;
}}
QTabBar::tab {{
    background: transparent;
    color: {t.text_secondary};
    padding: 4px 12px;
    border: none;
}}
QTabBar::tab:selected {{
    color: {t.primary_fg};
    border-bottom: 2px solid {t.primary_fg};
    font-weight: 600;
}}
QTabBar::tab:hover {{
    color: {t.text_primary};
}}
/* 键盘焦点：聚焦的 tab 用 primary_fg 下划线标出位置（选中+聚焦时
   后序规则生效，与选中态同色，视觉统一）。 */
QTabBar::tab:focus {{
    border-bottom: 2px solid {t.primary_fg};
}}

/* ---- 菜单 ---- */
QMenuBar {{
    background: {t.card_bg};
    border-bottom: 1px solid {t.card_border};
}}
QMenuBar::item {{
    background: transparent;
    padding: 5px 10px;
}}
QMenuBar::item:selected {{
    background: {t.hover_bg};
    border-radius: 4px;
}}
QMenu {{
    background: {t.card_bg};
    border: 1px solid {t.card_border};
}}
QMenu::item {{
    padding: 5px 24px 5px 20px;
}}
QMenu::item:selected {{
    background: {t.hover_bg};
}}

/* ---- 滚动区域（透明背景，卡片自行着色） ---- */
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

/* ---- 万年历 ---- */
QCalendarWidget {{
    background: {t.card_bg};
}}
QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background: {t.card_bg};
}}
QCalendarWidget QToolButton {{
    background: transparent;
    color: {t.text_primary};
    border: none;
    padding: 3px 8px;
}}
QCalendarWidget QToolButton:hover {{
    background: {t.hover_bg};
    border-radius: 4px;
}}
QCalendarWidget QAbstractItemView {{
    background: {t.card_bg};
    color: {t.text_primary};
    selection-background-color: {t.primary};
    selection-color: #FFFFFF;
}}

/* ---- 日志视图 ---- */
QTextEdit#logView {{
    background: {t.log_view_bg};
    border: none;
    color: {t.log_info};
    font-family: Consolas, "Microsoft YaHei";
    font-size: 10pt;
}}

/* ---- 表格/列表 ---- */
QTableWidget, QListWidget, QTreeWidget {{
    background: {t.card_bg};
    border: 1px solid {t.card_border};
    border-radius: 4px;
}}
QHeaderView::section {{
    background: {t.hover_bg};
    border: none;
    padding: 4px 8px;
    color: {t.text_secondary};
}}
"""
