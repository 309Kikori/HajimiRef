from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QColorDialog, QSpinBox, QCheckBox, QTabWidget, QWidget, QComboBox, QGroupBox, QSlider, QMessageBox)
from PySide6.QtCore import Qt
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
        self.resize(400, 350)
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
        self.tabs.addTab(tab_appearance, tr("appearance"))
        
        layout_app = QVBoxLayout(tab_appearance)

        # === 画板主题选择（顶层） / Canvas Theme Selector (Top Level) ===
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel(tr("canvas_theme")))
        self.combo_canvas_theme = QComboBox()
        self.combo_canvas_theme.addItem(tr("theme_dot_grid"), "dot_grid")
        self.combo_canvas_theme.addItem(tr("theme_ue5_blueprint"), "ue5_blueprint")
        theme_index = self.combo_canvas_theme.findData(Config.canvas_theme)
        if theme_index >= 0:
            self.combo_canvas_theme.setCurrentIndex(theme_index)
        self.combo_canvas_theme.currentIndexChanged.connect(self.set_canvas_theme)
        theme_layout.addWidget(self.combo_canvas_theme)
        layout_app.addLayout(theme_layout)

        # Show Grid（通用选项，两种主题都有）
        self.chk_grid = QCheckBox(tr("show_grid"))
        self.chk_grid.setChecked(Config.grid_enabled)
        self.chk_grid.toggled.connect(self.set_grid_enabled)
        layout_app.addWidget(self.chk_grid)

        # Grid Size（通用选项，两种主题都有）
        grid_s_layout = QHBoxLayout()
        grid_s_layout.addWidget(QLabel(tr("grid_size")))
        self.spin_grid_size = QSpinBox()
        self.spin_grid_size.setRange(10, 200)
        self.spin_grid_size.setValue(Config.grid_size)
        self.spin_grid_size.valueChanged.connect(self.set_grid_size)
        grid_s_layout.addWidget(self.spin_grid_size)
        layout_app.addLayout(grid_s_layout)

        # === 点阵主题选项组 / Dot Grid Theme Options Group ===
        self.dot_grid_group = QGroupBox(tr("theme_dot_grid"))
        dot_grid_layout = QVBoxLayout(self.dot_grid_group)

        # Background Color
        bg_layout = QHBoxLayout()
        bg_layout.addWidget(QLabel(tr("bg_color")))
        self.btn_bg_color = QPushButton()
        self.btn_bg_color.setFixedSize(50, 25)
        self.update_color_btn(self.btn_bg_color, Config.bg_color)
        self.btn_bg_color.clicked.connect(self.pick_bg_color)
        bg_layout.addWidget(self.btn_bg_color)
        dot_grid_layout.addLayout(bg_layout)

        # Grid Color
        grid_c_layout = QHBoxLayout()
        grid_c_layout.addWidget(QLabel(tr("grid_color")))
        self.btn_grid_color = QPushButton()
        self.btn_grid_color.setFixedSize(50, 25)
        self.update_color_btn(self.btn_grid_color, Config.grid_color)
        self.btn_grid_color.clicked.connect(self.pick_grid_color)
        grid_c_layout.addWidget(self.btn_grid_color)
        dot_grid_layout.addLayout(grid_c_layout)

        # Dot Size
        dot_size_layout = QHBoxLayout()
        dot_size_layout.addWidget(QLabel(tr("dot_size")))
        self.spin_dot_size = QSpinBox()
        self.spin_dot_size.setRange(1, 10)
        self.spin_dot_size.setValue(Config.dot_size)
        self.spin_dot_size.valueChanged.connect(self.set_dot_size)
        dot_size_layout.addWidget(self.spin_dot_size)
        dot_grid_layout.addLayout(dot_size_layout)

        layout_app.addWidget(self.dot_grid_group)

        # === UE5 蓝图主题选项组 / UE5 Blueprint Theme Options Group ===
        self.ue5_group = QGroupBox(tr("theme_ue5_blueprint"))
        ue5_layout = QVBoxLayout(self.ue5_group)

        # UE5 Background Color
        ue5_bg_layout = QHBoxLayout()
        ue5_bg_layout.addWidget(QLabel(tr("ue5_bg_color")))
        self.btn_ue5_bg_color = QPushButton()
        self.btn_ue5_bg_color.setFixedSize(50, 25)
        self.update_color_btn(self.btn_ue5_bg_color, Config.ue5_bg_color)
        self.btn_ue5_bg_color.clicked.connect(self.pick_ue5_bg_color)
        ue5_bg_layout.addWidget(self.btn_ue5_bg_color)
        ue5_layout.addLayout(ue5_bg_layout)

        # UE5 Small Grid Color
        ue5_sg_layout = QHBoxLayout()
        ue5_sg_layout.addWidget(QLabel(tr("ue5_small_grid_color")))
        self.btn_ue5_small_grid = QPushButton()
        self.btn_ue5_small_grid.setFixedSize(50, 25)
        self.update_color_btn(self.btn_ue5_small_grid, Config.ue5_small_grid_color)
        self.btn_ue5_small_grid.clicked.connect(self.pick_ue5_small_grid_color)
        ue5_sg_layout.addWidget(self.btn_ue5_small_grid)
        ue5_layout.addLayout(ue5_sg_layout)

        # UE5 Large Grid Color
        ue5_lg_layout = QHBoxLayout()
        ue5_lg_layout.addWidget(QLabel(tr("ue5_large_grid_color")))
        self.btn_ue5_large_grid = QPushButton()
        self.btn_ue5_large_grid.setFixedSize(50, 25)
        self.update_color_btn(self.btn_ue5_large_grid, Config.ue5_large_grid_color)
        self.btn_ue5_large_grid.clicked.connect(self.pick_ue5_large_grid_color)
        ue5_lg_layout.addWidget(self.btn_ue5_large_grid)
        ue5_layout.addLayout(ue5_lg_layout)

        # UE5 Large Grid Multiplier
        ue5_mult_layout = QHBoxLayout()
        ue5_mult_layout.addWidget(QLabel(tr("ue5_large_grid_multiplier")))
        self.spin_ue5_multiplier = QSpinBox()
        self.spin_ue5_multiplier.setRange(2, 20)
        self.spin_ue5_multiplier.setValue(Config.ue5_large_grid_multiplier)
        self.spin_ue5_multiplier.valueChanged.connect(self.set_ue5_large_grid_multiplier)
        ue5_mult_layout.addWidget(self.spin_ue5_multiplier)
        ue5_layout.addLayout(ue5_mult_layout)

        # UE5 Small Line Width
        ue5_slw_layout = QHBoxLayout()
        ue5_slw_layout.addWidget(QLabel(tr("ue5_small_line_width")))
        self.spin_ue5_small_lw = QSpinBox()
        self.spin_ue5_small_lw.setRange(1, 5)
        self.spin_ue5_small_lw.setValue(int(Config.ue5_small_line_width))
        self.spin_ue5_small_lw.valueChanged.connect(self.set_ue5_small_line_width)
        ue5_slw_layout.addWidget(self.spin_ue5_small_lw)
        ue5_layout.addLayout(ue5_slw_layout)

        # UE5 Large Line Width
        ue5_llw_layout = QHBoxLayout()
        ue5_llw_layout.addWidget(QLabel(tr("ue5_large_line_width")))
        self.spin_ue5_large_lw = QSpinBox()
        self.spin_ue5_large_lw.setRange(1, 8)
        self.spin_ue5_large_lw.setValue(int(Config.ue5_large_line_width))
        self.spin_ue5_large_lw.valueChanged.connect(self.set_ue5_large_line_width)
        ue5_llw_layout.addWidget(self.spin_ue5_large_lw)
        ue5_layout.addLayout(ue5_llw_layout)

        # UE5 Small Line Alpha
        ue5_sla_layout = QHBoxLayout()
        ue5_sla_layout.addWidget(QLabel(tr("ue5_small_line_alpha")))
        self.slider_ue5_small_alpha = QSlider(Qt.Horizontal)
        self.slider_ue5_small_alpha.setRange(0, 255)
        self.slider_ue5_small_alpha.setValue(Config.ue5_small_line_alpha)
        self.slider_ue5_small_alpha.valueChanged.connect(self.set_ue5_small_line_alpha)
        ue5_sla_layout.addWidget(self.slider_ue5_small_alpha)
        ue5_layout.addLayout(ue5_sla_layout)

        # UE5 Large Line Alpha
        ue5_lla_layout = QHBoxLayout()
        ue5_lla_layout.addWidget(QLabel(tr("ue5_large_line_alpha")))
        self.slider_ue5_large_alpha = QSlider(Qt.Horizontal)
        self.slider_ue5_large_alpha.setRange(0, 255)
        self.slider_ue5_large_alpha.setValue(Config.ue5_large_line_alpha)
        self.slider_ue5_large_alpha.valueChanged.connect(self.set_ue5_large_line_alpha)
        ue5_lla_layout.addWidget(self.slider_ue5_large_alpha)
        ue5_layout.addLayout(ue5_lla_layout)

        layout_app.addWidget(self.ue5_group)

        # 根据当前主题显示/隐藏选项组 / Show/hide option groups based on current theme
        self._update_theme_options_visibility()

        # --- Win11 窗口特效分组 / Win11 Window Effects Group ---
        win11_group = QGroupBox(tr("win11_effects"))
        win11_layout = QVBoxLayout(win11_group)

        # 背景不透明度滑条 / Background Opacity Slider (alpha channel 0~255)
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel(tr("bg_opacity")))
        self.slider_opacity = QSlider(Qt.Horizontal)
        self.slider_opacity.setRange(0, 255)  # alpha 通道 0~255
        self.slider_opacity.setValue(Config.bg_opacity)
        self.slider_opacity.setTickInterval(25)
        self.slider_opacity.setTickPosition(QSlider.TicksBelow)
        self.lbl_opacity_val = QLabel(str(Config.bg_opacity))
        self.lbl_opacity_val.setFixedWidth(40)
        self.slider_opacity.valueChanged.connect(self.set_bg_opacity)
        opacity_layout.addWidget(self.slider_opacity)
        opacity_layout.addWidget(self.lbl_opacity_val)
        win11_layout.addLayout(opacity_layout)

        # 亚克力效果开关 / Acrylic Effect Toggle
        self.chk_acrylic = QCheckBox(tr("acrylic_effect"))
        self.chk_acrylic.setChecked(Config.acrylic_enabled)
        self.chk_acrylic.toggled.connect(self.set_acrylic_enabled)
        win11_layout.addWidget(self.chk_acrylic)

        layout_app.addWidget(win11_group)

        # --- 色深模式分组 / Color Depth Mode Group ---
        color_depth_group = QGroupBox(tr("color_depth"))
        cd_layout = QVBoxLayout(color_depth_group)

        # 色深模式下拉框 / Color Depth Mode Combo
        cd_mode_layout = QHBoxLayout()
        cd_mode_layout.addWidget(QLabel(tr("color_depth_mode")))
        self.combo_color_depth = QComboBox()
        self.combo_color_depth.addItem(tr("color_depth_auto"), "auto")
        self.combo_color_depth.addItem(tr("color_depth_8bit"), "8bit")
        self.combo_color_depth.addItem(tr("color_depth_10bit"), "10bit")
        self.combo_color_depth.addItem(tr("color_depth_16bit"), "16bit")
        cd_index = self.combo_color_depth.findData(Config.color_depth_mode)
        if cd_index >= 0:
            self.combo_color_depth.setCurrentIndex(cd_index)
        self.combo_color_depth.currentIndexChanged.connect(self.set_color_depth_mode)
        cd_mode_layout.addWidget(self.combo_color_depth)
        cd_layout.addLayout(cd_mode_layout)

        # 提示标签 / Tip label
        self.lbl_color_depth_tip = QLabel(tr("color_depth_tip"))
        self.lbl_color_depth_tip.setWordWrap(True)
        self.lbl_color_depth_tip.setStyleSheet("color: #888; font-size: 11px;")
        cd_layout.addWidget(self.lbl_color_depth_tip)

        layout_app.addWidget(color_depth_group)
        layout_app.addStretch()
        
        # --- Tab 2: Board Settings ---
        tab_board = QWidget()
        self.tabs.addTab(tab_board, tr("board_settings"))
        
        layout_board = QVBoxLayout(tab_board)
        
        # Auto Reset Board Group
        auto_reset_group = QGroupBox(tr("auto_reset_board"))
        auto_reset_layout = QVBoxLayout(auto_reset_group)
        
        # Enable Auto Reset
        self.chk_auto_reset = QCheckBox(tr("auto_reset_board"))
        self.chk_auto_reset.setChecked(Config.auto_reset_board_enabled)
        self.chk_auto_reset.toggled.connect(self.set_auto_reset_enabled)
        auto_reset_layout.addWidget(self.chk_auto_reset)
        
        # Auto Reset Interval
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel(tr("auto_reset_interval")))
        self.spin_auto_reset_interval = QSpinBox()
        self.spin_auto_reset_interval.setRange(1, 60)
        self.spin_auto_reset_interval.setValue(Config.auto_reset_interval)
        self.spin_auto_reset_interval.valueChanged.connect(self.set_auto_reset_interval)
        interval_layout.addWidget(self.spin_auto_reset_interval)
        auto_reset_layout.addLayout(interval_layout)
        
        layout_board.addWidget(auto_reset_group)
        layout_board.addStretch()
        
        # --- Tab 3: Language ---
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
        
        btn_reset = QPushButton(tr("reset_defaults"))
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

    def _update_theme_options_visibility(self):
        """
        根据当前画板主题显示/隐藏对应的选项组
        Show/hide option groups based on current canvas theme
        """
        is_dot_grid = (Config.canvas_theme == "dot_grid")
        self.dot_grid_group.setVisible(is_dot_grid)
        self.ue5_group.setVisible(not is_dot_grid)

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

    def pick_ue5_bg_color(self):
        """选择 UE5 蓝图背景颜色 / Pick UE5 blueprint background color"""
        color = QColorDialog.getColor(Config.ue5_bg_color, self, tr("pick_color"))
        if color.isValid():
            Config.ue5_bg_color = color
            self.update_color_btn(self.btn_ue5_bg_color, color)
            self.parent().view.viewport().update()

    def pick_ue5_small_grid_color(self):
        """选择 UE5 小网格颜色 / Pick UE5 small grid color"""
        color = QColorDialog.getColor(Config.ue5_small_grid_color, self, tr("pick_color"))
        if color.isValid():
            Config.ue5_small_grid_color = color
            self.update_color_btn(self.btn_ue5_small_grid, color)
            self.parent().view.viewport().update()

    def pick_ue5_large_grid_color(self):
        """选择 UE5 大网格颜色 / Pick UE5 large grid color"""
        color = QColorDialog.getColor(Config.ue5_large_grid_color, self, tr("pick_color"))
        if color.isValid():
            Config.ue5_large_grid_color = color
            self.update_color_btn(self.btn_ue5_large_grid, color)
            self.parent().view.viewport().update()

    def set_ue5_large_grid_multiplier(self, val):
        """设置 UE5 大网格倍数 / Set UE5 large grid multiplier"""
        Config.ue5_large_grid_multiplier = val
        self.parent().view.viewport().update()

    def set_ue5_small_line_width(self, val):
        """设置 UE5 小网格线宽 / Set UE5 small grid line width"""
        Config.ue5_small_line_width = float(val)
        self.parent().view.viewport().update()

    def set_ue5_large_line_width(self, val):
        """设置 UE5 大网格线宽 / Set UE5 large grid line width"""
        Config.ue5_large_line_width = float(val)
        self.parent().view.viewport().update()

    def set_ue5_small_line_alpha(self, val):
        """设置 UE5 小网格线透明度 / Set UE5 small grid line alpha"""
        Config.ue5_small_line_alpha = val
        self.parent().view.viewport().update()

    def set_ue5_large_line_alpha(self, val):
        """设置 UE5 大网格线透明度 / Set UE5 large grid line alpha"""
        Config.ue5_large_line_alpha = val
        self.parent().view.viewport().update()

    def set_dot_size(self, val):
        """设置点阵点大小 / Set dot grid dot size"""
        Config.dot_size = val
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

    def set_canvas_theme(self, index):
        """
        设置画板主题 / Set canvas theme
        """
        theme = self.combo_canvas_theme.itemData(index)
        if theme:
            Config.canvas_theme = theme
            self._update_theme_options_visibility()
            self.parent().view.viewport().update()

    def set_bg_opacity(self, val):
        """
        设置背景不透明度（alpha 通道 0~255）/ Set background opacity (alpha channel 0~255)
        """
        Config.bg_opacity = val
        self.lbl_opacity_val.setText(str(val))
        if self.parent():
            self.parent().apply_win11_effects()

    def set_acrylic_enabled(self, val):
        """
        设置是否启用亚克力效果 / Set acrylic effect enabled
        同时切换画布 viewport 模式（亚克力穿透 vs GPU 加速）
        Also switch canvas viewport mode (acrylic passthrough vs GPU acceleration)
        """
        Config.acrylic_enabled = val
        if self.parent():
            # 切换画布 viewport 模式 / Switch canvas viewport mode
            self.parent().view.set_acrylic_mode(val)
            # 应用窗口级亚克力效果 / Apply window-level acrylic effects
            self.parent().apply_win11_effects()

    def set_color_depth_mode(self, index):
        """
        设置色深模式 / Set color depth mode
        切换后需重启应用（因为 OpenGL Surface Format 必须在 QApplication 创建前配置）
        Restart required after change (OpenGL Surface Format must be configured before QApplication creation)
        """
        mode = self.combo_color_depth.itemData(index)
        if mode and mode != Config.color_depth_mode:
            Config.color_depth_mode = mode
            # 提示用户需要重启 / Notify user restart is needed
            QMessageBox.information(self, tr("color_depth"), tr("color_depth_restart"))

    def set_auto_reset_enabled(self, val):
        """
        设置是否启用自动重置画板 / Set auto reset board enabled
        """
        Config.auto_reset_board_enabled = val
        if self.parent():
            self.parent().update_auto_reset_timer()
    
    def set_auto_reset_interval(self, val):
        """
        设置自动重置间隔 / Set auto reset interval
        """
        Config.auto_reset_interval = val
        if self.parent():
            self.parent().update_auto_reset_timer()
        
    def change_language(self, index):
        """
        更改语言 / Change language
        """
        lang_code = self.combo_lang.itemData(index)
        Config.language = lang_code
        if self.parent():
            self.parent().change_language(lang_code)
            # Refresh this dialog title/tabs
            self.setWindowTitle(tr("preferences"))
            self.tabs.setTabText(0, tr("appearance"))
            self.tabs.setTabText(1, tr("board_settings"))
            self.tabs.setTabText(2, tr("language"))
            # 刷新控件文本
            self.chk_grid.setText(tr("show_grid"))
            self.chk_acrylic.setText(tr("acrylic_effect"))
            # 刷新选项组标题
            self.dot_grid_group.setTitle(tr("theme_dot_grid"))
            self.ue5_group.setTitle(tr("theme_ue5_blueprint"))
            # 刷新画板主题下拉框文本 / Refresh canvas theme combo text
            current_theme_data = self.combo_canvas_theme.currentData()
            self.combo_canvas_theme.clear()
            self.combo_canvas_theme.addItem(tr("theme_dot_grid"), "dot_grid")
            self.combo_canvas_theme.addItem(tr("theme_ue5_blueprint"), "ue5_blueprint")
            idx = self.combo_canvas_theme.findData(current_theme_data)
            if idx >= 0:
                self.combo_canvas_theme.setCurrentIndex(idx)

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
        # 重置画板主题下拉框 / Reset canvas theme combo
        theme_idx = self.combo_canvas_theme.findData(Config.canvas_theme)
        if theme_idx >= 0:
            self.combo_canvas_theme.setCurrentIndex(theme_idx)
        self._update_theme_options_visibility()
        # 重置 UE5 蓝图选项 / Reset UE5 blueprint options
        self.update_color_btn(self.btn_ue5_bg_color, Config.ue5_bg_color)
        self.update_color_btn(self.btn_ue5_small_grid, Config.ue5_small_grid_color)
        self.update_color_btn(self.btn_ue5_large_grid, Config.ue5_large_grid_color)
        self.spin_ue5_multiplier.setValue(Config.ue5_large_grid_multiplier)
        self.spin_ue5_small_lw.setValue(int(Config.ue5_small_line_width))
        self.spin_ue5_large_lw.setValue(int(Config.ue5_large_line_width))
        self.slider_ue5_small_alpha.setValue(Config.ue5_small_line_alpha)
        self.slider_ue5_large_alpha.setValue(Config.ue5_large_line_alpha)
        self.spin_dot_size.setValue(Config.dot_size)
        self.slider_opacity.setValue(Config.bg_opacity)
        self.lbl_opacity_val.setText(str(Config.bg_opacity))
        self.chk_acrylic.setChecked(Config.acrylic_enabled)
        self.chk_auto_reset.setChecked(Config.auto_reset_board_enabled)
        self.spin_auto_reset_interval.setValue(Config.auto_reset_interval)
        # 重置色深模式 / Reset color depth mode
        cd_idx = self.combo_color_depth.findData(Config.color_depth_mode)
        if cd_idx >= 0:
            self.combo_color_depth.setCurrentIndex(cd_idx)
        if self.parent():
            self.parent().apply_win11_effects()
        
        index = self.combo_lang.findData(Config.language)
        if index >= 0:
            self.combo_lang.setCurrentIndex(index)
            
        self.parent().view.viewport().update()
        if self.parent():
            self.parent().change_language(Config.language)
