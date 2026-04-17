"""
Configuration Management Module
"""

import os
import json
from PySide6.QtGui import QColor
from localization import LANGUAGES

class Config:
    """
    Global configuration settings for the application.
    """
    # 配置类 / Configuration class
    language = "zh_cn"
    bg_color = QColor(40, 40, 40)  # 活动区域背景色
    inactive_bg_color = QColor(25, 25, 25)  # 非活动区域背景色（更深）
    grid_color = QColor(60, 60, 60)
    grid_size = 40
    grid_enabled = True
    dot_size = 2  # 点阵网格点大小（像素）/ Dot grid dot size (px)
    active_area_padding = 200  # 活动区域边距（像素）
    # 画板初始大小（世界坐标）/ Initial board size (world coordinates)
    initial_board_width = 2000
    initial_board_height = 1500
    # 自动重置画板设置 / Auto reset board settings
    auto_reset_board_enabled = False  # 是否启用自动重置画板
    auto_reset_interval = 10  # 自动重置间隔（分钟）
    # 画板主题 / Canvas theme ('dot_grid' = 点阵网格, 'ue5_blueprint' = UE5蓝图风格)
    canvas_theme = "dot_grid"
    # UE5 蓝图主题专属配置 / UE5 Blueprint theme specific settings
    # 颜色说明：UE5 源码使用 16 位线性色彩空间 FLinearColor，
    # 需经 gamma 校正 sRGB = pow(linear, 1/2.2) 转换为屏幕显示色。
    # 背景 linear ~0.04 → sRGB ~0.23 → RGB(59,59,59) #3B3B3B
    # 小网格 linear ~0.07 → sRGB ~0.30 → RGB(77,77,77) #4D4D4D
    # 大网格 linear ~0.09 → sRGB ~0.34 → RGB(87,87,87) #575757
    # 所有颜色均为纯灰色（R=G=B），无蓝色分量。
    ue5_bg_color = QColor(59, 59, 59)          # 深灰底色 #3B3B3B（gamma 校正后）
    ue5_small_grid_color = QColor(77, 77, 77)  # 小网格线色 #4D4D4D（纯灰）
    ue5_large_grid_color = QColor(87, 87, 87)  # 大网格线色 #575757（纯灰）
    ue5_large_grid_multiplier = 8             # 大网格倍数（每8个小格一条粗线）
    ue5_small_line_width = 1.5                # 小网格线宽（屏幕像素，加粗）
    ue5_large_line_width = 3.0                # 大网格线宽（屏幕像素，加粗）
    ue5_small_line_alpha = 80                 # 小网格线透明度 0~255（约31%，清晰可辨）
    ue5_large_line_alpha = 160                # 大网格线透明度 0~255（约63%，醒目但不刺眼）
    # 色深模式 / Color Depth Mode
    # 'auto' = 自适应（默认），'8bit' = 强制8bit，'10bit' = 强制10bit，'16bit' = 强制16bit
    color_depth_mode = "auto"
    # Win11 窗口特效 / Win11 window effects
    acrylic_enabled = True  # 是否启用亚克力背景效果
    bg_opacity = 200  # 背景不透明度 0~255（越低越透明，控制背景色 alpha 通道）

    @classmethod
    def reset_defaults(cls):
        """
        Reset configuration to default values.
        """
        cls.language = "zh_cn"
        cls.bg_color = QColor(40, 40, 40)
        cls.inactive_bg_color = QColor(25, 25, 25)
        cls.grid_color = QColor(60, 60, 60)
        cls.grid_size = 40
        cls.grid_enabled = True
        cls.active_area_padding = 200
        cls.initial_board_width = 2000
        cls.initial_board_height = 1500
        cls.auto_reset_board_enabled = False
        cls.auto_reset_interval = 10
        cls.canvas_theme = "dot_grid"
        cls.dot_size = 2
        cls.ue5_bg_color = QColor(59, 59, 59)
        cls.ue5_small_grid_color = QColor(77, 77, 77)
        cls.ue5_large_grid_color = QColor(87, 87, 87)
        cls.ue5_large_grid_multiplier = 8
        cls.ue5_small_line_width = 1.5
        cls.ue5_large_line_width = 3.0
        cls.ue5_small_line_alpha = 80
        cls.ue5_large_line_alpha = 160
        cls.color_depth_mode = "auto"
        cls.acrylic_enabled = True
        cls.bg_opacity = 200

    @classmethod
    def _get_config_path(cls):
        """获取配置文件路径（程序所在目录下的 config.json）"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, "config.json")

    @classmethod
    def save(cls):
        """
        将当前配置保存到 config.json（持久化）。
        Save current configuration to config.json (persistence).
        """
        data = {
            "language": cls.language,
            "bg_color": cls.bg_color.name(),
            "inactive_bg_color": cls.inactive_bg_color.name(),
            "grid_color": cls.grid_color.name(),
            "grid_size": cls.grid_size,
            "grid_enabled": cls.grid_enabled,
            "dot_size": cls.dot_size,
            "active_area_padding": cls.active_area_padding,
            "initial_board_width": cls.initial_board_width,
            "initial_board_height": cls.initial_board_height,
            "auto_reset_board_enabled": cls.auto_reset_board_enabled,
            "auto_reset_interval": cls.auto_reset_interval,
            "canvas_theme": cls.canvas_theme,
            "ue5_bg_color": cls.ue5_bg_color.name(),
            "ue5_small_grid_color": cls.ue5_small_grid_color.name(),
            "ue5_large_grid_color": cls.ue5_large_grid_color.name(),
            "ue5_large_grid_multiplier": cls.ue5_large_grid_multiplier,
            "ue5_small_line_width": cls.ue5_small_line_width,
            "ue5_large_line_width": cls.ue5_large_line_width,
            "ue5_small_line_alpha": cls.ue5_small_line_alpha,
            "ue5_large_line_alpha": cls.ue5_large_line_alpha,
            "color_depth_mode": cls.color_depth_mode,
            "acrylic_enabled": cls.acrylic_enabled,
            "bg_opacity": cls.bg_opacity,
        }
        try:
            with open(cls._get_config_path(), 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[Config] 保存配置失败: {e}")

    @classmethod
    def load(cls):
        """
        从 config.json 加载配置（启动时调用）。
        Load configuration from config.json (called at startup).
        """
        config_path = cls._get_config_path()
        if not os.path.exists(config_path):
            return
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 逐项恢复，缺失的键保持默认值
            if "language" in data:
                cls.language = data["language"]
            if "bg_color" in data:
                cls.bg_color = QColor(data["bg_color"])
            if "inactive_bg_color" in data:
                cls.inactive_bg_color = QColor(data["inactive_bg_color"])
            if "grid_color" in data:
                cls.grid_color = QColor(data["grid_color"])
            if "grid_size" in data:
                cls.grid_size = data["grid_size"]
            if "grid_enabled" in data:
                cls.grid_enabled = data["grid_enabled"]
            if "dot_size" in data:
                cls.dot_size = data["dot_size"]
            if "active_area_padding" in data:
                cls.active_area_padding = data["active_area_padding"]
            if "initial_board_width" in data:
                cls.initial_board_width = data["initial_board_width"]
            if "initial_board_height" in data:
                cls.initial_board_height = data["initial_board_height"]
            if "auto_reset_board_enabled" in data:
                cls.auto_reset_board_enabled = data["auto_reset_board_enabled"]
            if "auto_reset_interval" in data:
                cls.auto_reset_interval = data["auto_reset_interval"]
            if "canvas_theme" in data:
                cls.canvas_theme = data["canvas_theme"]
            if "ue5_bg_color" in data:
                cls.ue5_bg_color = QColor(data["ue5_bg_color"])
            if "ue5_small_grid_color" in data:
                cls.ue5_small_grid_color = QColor(data["ue5_small_grid_color"])
            if "ue5_large_grid_color" in data:
                cls.ue5_large_grid_color = QColor(data["ue5_large_grid_color"])
            if "ue5_large_grid_multiplier" in data:
                cls.ue5_large_grid_multiplier = data["ue5_large_grid_multiplier"]
            if "ue5_small_line_width" in data:
                cls.ue5_small_line_width = data["ue5_small_line_width"]
            if "ue5_large_line_width" in data:
                cls.ue5_large_line_width = data["ue5_large_line_width"]
            if "ue5_small_line_alpha" in data:
                cls.ue5_small_line_alpha = data["ue5_small_line_alpha"]
            if "ue5_large_line_alpha" in data:
                cls.ue5_large_line_alpha = data["ue5_large_line_alpha"]
            if "color_depth_mode" in data:
                cls.color_depth_mode = data["color_depth_mode"]
            if "acrylic_enabled" in data:
                cls.acrylic_enabled = data["acrylic_enabled"]
            if "bg_opacity" in data:
                cls.bg_opacity = data["bg_opacity"]
            print(f"[Config] 已加载配置: {config_path}")
        except (json.JSONDecodeError, IOError) as e:
            print(f"[Config] 加载配置失败，使用默认值: {e}")

def tr(key):
    """
    Translate a key to the current language.
    """
    # 翻译函数 / Translation function
    return LANGUAGES.get(Config.language, LANGUAGES["en"]).get(key, key)
