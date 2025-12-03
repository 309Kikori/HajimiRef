from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QColorDialog, QSpinBox, QCheckBox, QTabWidget, QWidget, QComboBox)
from Config import Config, tr

class SettingsDialog(QDialog):
    """
    设置对话框类 / Settings dialog class
    """
    def __init__(self, parent=None):
        """
        初始化设置对话框 / Initialize settings dialog
        """
        super().__init__(parent)
        self.setWindowTitle(tr("preferences"))
        self.resize(400, 300)
        self.setup_ui()

    def setup_ui(self):
        """
        设置 UI 布局和控件 / Setup UI layout and widgets
        """
        main_layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # --- Tab 1: Appearance ---
        tab_appearance = QWidget()
        self.tabs.addTab(tab_appearance, tr("preferences")) # Using "preferences" as tab name for now or "Appearance"
        
        layout_app = QVBoxLayout(tab_appearance)

        # Background Color
        bg_layout = QHBoxLayout()
        bg_layout.addWidget(QLabel(tr("bg_color")))
        self.btn_bg_color = QPushButton()
        self.btn_bg_color.setFixedSize(50, 25)
        self.update_color_btn(self.btn_bg_color, Config.bg_color)
        self.btn_bg_color.clicked.connect(self.pick_bg_color)
        bg_layout.addWidget(self.btn_bg_color)
        layout_app.addLayout(bg_layout)

        # Grid Color
        grid_c_layout = QHBoxLayout()
        grid_c_layout.addWidget(QLabel(tr("grid_color")))
        self.btn_grid_color = QPushButton()
        self.btn_grid_color.setFixedSize(50, 25)
        self.update_color_btn(self.btn_grid_color, Config.grid_color)
        self.btn_grid_color.clicked.connect(self.pick_grid_color)
        grid_c_layout.addWidget(self.btn_grid_color)
        layout_app.addLayout(grid_c_layout)

        # Grid Size
        grid_s_layout = QHBoxLayout()
        grid_s_layout.addWidget(QLabel(tr("grid_size")))
        self.spin_grid_size = QSpinBox()
        self.spin_grid_size.setRange(10, 200)
        self.spin_grid_size.setValue(Config.grid_size)
        self.spin_grid_size.valueChanged.connect(self.set_grid_size)
        grid_s_layout.addWidget(self.spin_grid_size)
        layout_app.addLayout(grid_s_layout)

        # Show Grid
        self.chk_grid = QCheckBox(tr("show_grid"))
        self.chk_grid.setChecked(Config.grid_enabled)
        self.chk_grid.toggled.connect(self.set_grid_enabled)
        layout_app.addWidget(self.chk_grid)

        layout_app.addStretch()
        
        # --- Tab 2: Language ---
        tab_lang = QWidget()
        self.tabs.addTab(tab_lang, tr("language"))
        
        layout_lang = QVBoxLayout(tab_lang)
        
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel(tr("language")))
        self.combo_lang = QComboBox()
        self.combo_lang.addItem("English", "en")
        self.combo_lang.addItem("中文", "zh_cn")
        
        # Set current index
        index = self.combo_lang.findData(Config.language)
        if index >= 0:
            self.combo_lang.setCurrentIndex(index)
            
        self.combo_lang.currentIndexChanged.connect(self.change_language)
        lang_layout.addWidget(self.combo_lang)
        layout_lang.addLayout(lang_layout)
        
        layout_lang.addStretch()

        # --- Bottom Buttons ---
        btn_layout = QHBoxLayout()
        
        btn_reset = QPushButton(tr("reset_defaults") if "reset_defaults" in tr("reset_defaults") else "Reset Defaults") # Fallback if key missing
        btn_reset.clicked.connect(self.reset_defaults)
        btn_layout.addWidget(btn_reset)
        
        btn_layout.addStretch()
        
        btn_ok = QPushButton(tr("ok"))
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_ok)
        
        main_layout.addLayout(btn_layout)

    def update_color_btn(self, btn, color):
        """
        更新颜色按钮样式 / Update color button style
        """
        btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #555;")

    def pick_bg_color(self):
        """
        选择背景颜色 / Pick background color
        """
        color = QColorDialog.getColor(Config.bg_color, self, tr("pick_color"))
        if color.isValid():
            Config.bg_color = color
            self.update_color_btn(self.btn_bg_color, color)
            self.parent().view.viewport().update()

    def pick_grid_color(self):
        """
        选择网格颜色 / Pick grid color
        """
        color = QColorDialog.getColor(Config.grid_color, self, tr("pick_color"))
        if color.isValid():
            Config.grid_color = color
            self.update_color_btn(self.btn_grid_color, color)
            self.parent().view.viewport().update()

    def set_grid_size(self, val):
        """
        设置网格大小 / Set grid size
        """
        Config.grid_size = val
        self.parent().view.viewport().update()

    def set_grid_enabled(self, val):
        """
        设置是否显示网格 / Set grid enabled
        """
        Config.grid_enabled = val
        self.parent().view.viewport().update()
        
    def change_language(self, index):
        """
        更改语言 / Change language
        """
        lang_code = self.combo_lang.itemData(index)
        Config.language = lang_code
        # Notify parent to update UI text if needed, or just rely on restart/reopen
        # For immediate effect on title/menu, we can call a method on parent
        if self.parent():
            self.parent().change_language(lang_code)
            # Refresh this dialog title/tabs
            self.setWindowTitle(tr("preferences"))
            self.tabs.setTabText(0, tr("preferences")) # Or "Appearance"
            self.tabs.setTabText(1, tr("language"))

    def reset_defaults(self):
        """
        重置为默认设置 / Reset to defaults
        """
        Config.reset_defaults()
        # Update UI elements
        self.update_color_btn(self.btn_bg_color, Config.bg_color)
        self.update_color_btn(self.btn_grid_color, Config.grid_color)
        self.spin_grid_size.setValue(Config.grid_size)
        self.chk_grid.setChecked(Config.grid_enabled)
        
        index = self.combo_lang.findData(Config.language)
        if index >= 0:
            self.combo_lang.setCurrentIndex(index)
            
        self.parent().view.viewport().update()
        if self.parent():
            self.parent().change_language(Config.language)
