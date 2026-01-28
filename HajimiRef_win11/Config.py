"""
Configuration Management Module
"""

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
    active_area_padding = 200  # 活动区域边距（像素）

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

def tr(key):
    """
    Translate a key to the current language.
    """
    # 翻译函数 / Translation function
    return LANGUAGES.get(Config.language, LANGUAGES["en"]).get(key, key)
