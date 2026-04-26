"""
关于对话框模块
使用组件工厂和主题系统重构的关于对话框
"""
from typing import Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QMessageBox,
    QApplication,
)
from PyQt5.QtCore import Qt, QTimer

from utils.version import get_project_version
from gui.style_helpers import (
    create_button, create_label, create_section_title,
    create_card_widget, create_tip_label, create_header_widget,
)
from gui.style_manager import StyleManager, ThemeManager
from gui.styles import FontSize, FontStyle, StyleConstants


class AboutDialog(QDialog):
    """现代化关于对话框"""

    def __init__(self, parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self.version: str = get_project_version()
        self.version_btn: Optional[QPushButton] = None
        self._init_ui()
        self._apply_styles()

    def _init_ui(self) -> None:
        """初始化 UI"""
        self.setWindowTitle("关于我们")
        self.setMinimumSize(520, 520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 顶部区域
        self._create_top_section(main_layout)

        # 信息卡片区域
        self._create_info_section(main_layout)

        # 功能特性区域
        self._create_features_section(main_layout)

        # 链接区域
        self._create_links_section(main_layout)

        # 底部区域
        self._create_bottom_section(main_layout)

    def _create_top_section(self, parent_layout: QVBoxLayout) -> None:
        """创建顶部应用信息区域"""
        top_frame = QFrame()
        top_frame.setObjectName("topFrame")
        top_frame.setMinimumHeight(180)

        top_layout = QVBoxLayout(top_frame)
        top_layout.setSpacing(StyleConstants.SPACING_NORMAL)
        top_layout.setContentsMargins(24, 24, 24, 24)

        # 应用图标
        icon_label = QLabel("\U0001F310")
        icon_label.setFont(FontStyle.emoji(48))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setObjectName("appIcon")
        top_layout.addWidget(icon_label)

        # 应用名称
        title_label = create_label(
            "校园网自动登录 + 定时关机",
            font_size=FontSize.MAIN_TITLE,
            bold=True,
        )
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setObjectName("appTitle")
        top_layout.addWidget(title_label)

        # 版本号（可点击复制）
        self.version_btn = create_button(
            f"版本 {self.version}", btn_type="primary", font_size=10
        )
        self.version_btn.setObjectName("versionButton")
        self.version_btn.setToolTip("点击复制版本号")
        self.version_btn.clicked.connect(self._copy_version)
        top_layout.addWidget(self.version_btn)

        parent_layout.addWidget(top_frame)

    def _create_info_section(self, parent_layout: QVBoxLayout) -> None:
        """创建信息卡片区域"""
        info_frame = create_card_widget()
        info_frame.setObjectName("infoCard")

        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(StyleConstants.SPACING_LOOSE)
        info_layout.setContentsMargins(24, 16, 24, 16)

        # 描述标题
        desc_title = create_section_title("\U0001F4D6 应用简介")
        desc_title.setObjectName("sectionTitle")
        info_layout.addWidget(desc_title)

        # 描述内容
        desc_label = create_label(
            "这是一个用于自动连接校园网并定时关机的智能工具。"
            "程序支持同步国务院节假日规则，自动识别工作日与节假日，"
            "实现智能化的网络登录和电源管理。",
            word_wrap=True,
        )
        desc_label.setObjectName("descText")
        info_layout.addWidget(desc_label)

        parent_layout.addSpacing(10)
        parent_layout.addWidget(info_frame)

    def _create_features_section(self, parent_layout: QVBoxLayout) -> None:
        """创建功能特性区域"""
        features_frame = create_card_widget()
        features_frame.setObjectName("featuresCard")

        features_layout = QVBoxLayout(features_frame)
        features_layout.setSpacing(StyleConstants.SPACING_NORMAL)
        features_layout.setContentsMargins(24, 16, 24, 16)

        # 特性标题
        features_title = create_section_title("\u2728 主要功能")
        features_title.setObjectName("sectionTitle")
        features_layout.addWidget(features_title)

        # 功能列表
        features = [
            ("\U0001F510", "自动校园网登录", "支持移动、电信、联通运营商"),
            ("\U0001F4F6", "智能WiFi连接", "自动检测并连接校园WiFi"),
            ("\u23F0", "定时关机", "自动设置关机任务，节能环保"),
            ("\U0001F4C5", "节假日同步", "同步国务院2025/2026节假日规则"),
            ("\U0001F4CA", "运行日志", "实时记录程序运行状态"),
        ]

        grid_layout = QGridLayout()
        grid_layout.setSpacing(StyleConstants.SPACING_LOOSE)
        grid_layout.setContentsMargins(0, 10, 0, 0)

        theme = ThemeManager.current_theme()
        for idx, (icon, title, desc) in enumerate(features):
            row = idx // 2
            col = idx % 2

            # 创建功能项容器
            feature_frame = QFrame()
            feature_frame.setObjectName("featureItem")
            feature_layout = QHBoxLayout(feature_frame)
            feature_layout.setSpacing(StyleConstants.SPACING_NORMAL)
            feature_layout.setContentsMargins(0, 5, 0, 5)

            # 图标
            icon_label = QLabel(icon)
            icon_label.setFont(FontStyle.emoji(18))
            icon_label.setAlignment(
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter
            )
            icon_label.setFixedWidth(35)
            feature_layout.addWidget(icon_label)

            # 文字容器
            text_layout = QVBoxLayout()
            text_layout.setSpacing(3)

            # 标题
            title_label = create_label(title, font_size=12, bold=True)
            text_layout.addWidget(title_label)

            # 描述
            desc_label = create_label(desc, font_size=FontSize.CONTENT_SMALL)
            desc_label.setStyleSheet(
                f"color: {theme.text_secondary}; background: transparent;"
            )
            desc_label.setWordWrap(True)
            text_layout.addWidget(desc_label)

            feature_layout.addLayout(text_layout)
            feature_layout.addStretch()

            grid_layout.addWidget(feature_frame, row, col)

        features_layout.addLayout(grid_layout)

        parent_layout.addSpacing(10)
        parent_layout.addWidget(features_frame)

    def _create_links_section(self, parent_layout: QVBoxLayout) -> None:
        """创建链接区域"""
        links_frame = create_card_widget()
        links_frame.setObjectName("linksCard")

        links_layout = QHBoxLayout(links_frame)
        links_layout.setSpacing(StyleConstants.SPACING_WIDE)
        links_layout.setContentsMargins(24, 16, 24, 16)

        # GitHub 链接
        github_label = create_label("\U0001F4BB GitHub", font_size=12, bold=True)

        github_link = QLabel(
            '<a href="https://github.com/taboo-hacker">访问仓库</a>'
        )
        github_link.setFont(FontStyle.normal(FontSize.BUTTON_SECONDARY))
        github_link.setObjectName("linkLabel")
        github_link.setOpenExternalLinks(True)
        github_link.setCursor(Qt.CursorShape.PointingHandCursor)

        links_layout.addWidget(github_label)
        links_layout.addSpacing(10)
        links_layout.addWidget(github_link)
        links_layout.addStretch()

        parent_layout.addSpacing(10)
        parent_layout.addWidget(links_frame)

    def _create_bottom_section(self, parent_layout: QVBoxLayout) -> None:
        """创建底部区域"""
        bottom_frame = QFrame()
        bottom_frame.setObjectName("bottomFrame")

        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.setSpacing(StyleConstants.SPACING_LOOSE)
        bottom_layout.setContentsMargins(24, 16, 24, 16)

        # 版权信息
        copyright_label = create_label(
            "\u00A9 2026 校园网自动登录工具 \u00B7 All Rights Reserved",
            font_size=FontSize.COPYRIGHT,
        )
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copyright_label.setObjectName("copyrightText")
        bottom_layout.addWidget(copyright_label)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(StyleConstants.SPACING_NORMAL)

        ok_btn = create_button("关闭", btn_type="primary", min_width=120)
        ok_btn.setObjectName("closeButton")
        ok_btn.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addStretch()

        bottom_layout.addLayout(btn_layout)

        parent_layout.addSpacing(10)
        parent_layout.addWidget(bottom_frame)

    def _apply_styles(self) -> None:
        """应用 QSS 样式"""
        qss = StyleManager.get_global_stylesheet()
        dialog_qss = StyleManager.get_dialog_stylesheet()
        self.setStyleSheet(qss + dialog_qss)

    def _copy_version(self) -> None:
        """复制版本号到剪贴板"""
        if self.version_btn is None:
            return

        clipboard = QApplication.instance().clipboard()
        if clipboard:
            clipboard.setText(self.version)

        # 保存按钮原始样式
        original_text = self.version_btn.text()

        # 显示已复制状态
        self.version_btn.setText("\u2713 已复制")

        # 2 秒后恢复
        QTimer.singleShot(2000, lambda: self._restore_version_button(original_text))

    def _restore_version_button(self, original_text: str) -> None:
        """恢复版本按钮文本"""
        if self.version_btn:
            self.version_btn.setText(original_text)
