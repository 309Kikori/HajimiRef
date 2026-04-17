"""
自适应色深管理器 / Adaptive Color Depth Manager
负责检测图像位深、自适应选择渲染格式、管理 OpenGL surface 配置。
Handles image bit-depth detection, adaptive rendering format selection,
and OpenGL surface configuration.
"""

from enum import Enum
from PySide6.QtGui import QImage, QSurfaceFormat
from PySide6.QtCore import QObject, Signal


class ColorDepthMode(Enum):
    """
    色深模式枚举 / Color depth mode enumeration
    """
    AUTO = "auto"          # 自适应：根据图像源自动选择最佳色深
    FORCE_8BIT = "8bit"    # 强制 8bit：所有图像以 8bit/通道 渲染（省内存）
    FORCE_10BIT = "10bit"  # 强制 10bit：所有图像以 10bit/通道 渲染（需硬件支持）
    FORCE_16BIT = "16bit"  # 强制 16bit：所有图像以 16bit/通道 渲染（最高精度）


class ImageColorDepthInfo:
    """
    图像色深信息 / Image color depth information
    存储单张图像的位深检测结果。
    """
    def __init__(self, bits_per_channel: int = 8, has_alpha: bool = False,
                 original_format: QImage.Format = QImage.Format.Format_ARGB32):
        self.bits_per_channel = bits_per_channel  # 每通道位深 (8, 10, 16)
        self.has_alpha = has_alpha                # 是否包含 alpha 通道
        self.original_format = original_format    # 原始 QImage 格式

    @property
    def is_high_bit_depth(self) -> bool:
        """是否为高位深图像（>8bit）"""
        return self.bits_per_channel > 8

    def __repr__(self):
        return (f"ImageColorDepthInfo(bits={self.bits_per_channel}, "
                f"alpha={self.has_alpha}, format={self.original_format})")


class ColorDepthManager(QObject):
    """
    自适应色深管理器 / Adaptive Color Depth Manager

    核心职责：
    1. 检测图像的原始位深
    2. 根据当前模式决定最佳渲染格式
    3. 配置 OpenGL surface format 以支持高位深输出
    4. 提供图像格式转换工具方法

    设计原则：
    - AUTO 模式下，高位深图像保持高位深渲染，低位深图像使用 8bit 渲染（节省内存）
    - 用户可手动强制指定色深模式
    - 所有转换均保持最大精度，不做不必要的降级
    """

    # 信号：色深模式变更时发出 / Signal emitted when color depth mode changes
    mode_changed = Signal(str)

    # ── QImage 格式 → 每通道位深 映射表 ──
    # 覆盖 Qt6 所有常见图像格式
    _FORMAT_BIT_DEPTH = {
        # 8bit 格式
        QImage.Format.Format_RGB32: 8,
        QImage.Format.Format_ARGB32: 8,
        QImage.Format.Format_ARGB32_Premultiplied: 8,
        QImage.Format.Format_RGB888: 8,
        QImage.Format.Format_RGBA8888: 8,
        QImage.Format.Format_RGBA8888_Premultiplied: 8,
        QImage.Format.Format_RGB444: 4,
        QImage.Format.Format_RGB555: 5,
        QImage.Format.Format_RGB16: 5,  # RGB565
        QImage.Format.Format_Indexed8: 8,
        QImage.Format.Format_Grayscale8: 8,
        # 16bit 格式 (Qt 5.12+)
        QImage.Format.Format_RGBX64: 16,
        QImage.Format.Format_RGBA64: 16,
        QImage.Format.Format_RGBA64_Premultiplied: 16,
        QImage.Format.Format_Grayscale16: 16,
    }

    # ── QImage 格式 → 是否含 alpha 通道 映射表 ──
    _FORMAT_HAS_ALPHA = {
        QImage.Format.Format_ARGB32: True,
        QImage.Format.Format_ARGB32_Premultiplied: True,
        QImage.Format.Format_RGBA8888: True,
        QImage.Format.Format_RGBA8888_Premultiplied: True,
        QImage.Format.Format_RGBA64: True,
        QImage.Format.Format_RGBA64_Premultiplied: True,
        QImage.Format.Format_RGB32: False,
        QImage.Format.Format_RGB888: False,
        QImage.Format.Format_RGBX64: False,
        QImage.Format.Format_Grayscale8: False,
        QImage.Format.Format_Grayscale16: False,
    }

    def __init__(self, mode: ColorDepthMode = ColorDepthMode.AUTO):
        super().__init__()
        self._mode = mode

    @property
    def mode(self) -> ColorDepthMode:
        return self._mode

    @mode.setter
    def mode(self, value: ColorDepthMode):
        if self._mode != value:
            self._mode = value
            self.mode_changed.emit(value.value)
            print(f"[ColorDepthManager] 色深模式已切换为: {value.value}")

    # ────────────────────────────────────────────
    # 1. 图像位深检测 / Image bit-depth detection
    # ────────────────────────────────────────────

    @classmethod
    def detect_image_depth(cls, image: QImage) -> ImageColorDepthInfo:
        """
        检测 QImage 的原始色深信息。
        Detect the original color depth of a QImage.

        Args:
            image: 待检测的 QImage

        Returns:
            ImageColorDepthInfo 包含位深、alpha、原始格式信息
        """
        fmt = image.format()
        bits = cls._FORMAT_BIT_DEPTH.get(fmt, 8)
        has_alpha = cls._FORMAT_HAS_ALPHA.get(fmt, False)
        return ImageColorDepthInfo(
            bits_per_channel=bits,
            has_alpha=has_alpha,
            original_format=fmt
        )

    @classmethod
    def detect_depth_from_data(cls, data: bytes) -> ImageColorDepthInfo:
        """
        从二进制图像数据检测色深（不完全解码，仅加载头部信息）。
        Detect color depth from raw image data (header-only, minimal decoding).

        Args:
            data: 图像的原始二进制数据

        Returns:
            ImageColorDepthInfo
        """
        image = QImage()
        if image.loadFromData(data):
            return cls.detect_image_depth(image)
        return ImageColorDepthInfo()  # 默认 8bit

    # ────────────────────────────────────────────
    # 2. 渲染格式选择 / Rendering format selection
    # ────────────────────────────────────────────

    def get_optimal_format(self, depth_info: ImageColorDepthInfo,
                           need_alpha: bool = True) -> QImage.Format:
        """
        根据当前色深模式和图像信息，返回最佳 QImage 渲染格式。
        Select the optimal QImage format based on current mode and image info.

        自适应逻辑：
        - AUTO: 高位深图像 → RGBA64，低位深图像 → ARGB32
        - FORCE_8BIT: 始终 ARGB32
        - FORCE_10BIT: 高位深图像 → RGBA64（10bit 在 Qt 中用 16bit 容器承载）
        - FORCE_16BIT: 始终 RGBA64

        Args:
            depth_info: 图像色深信息
            need_alpha: 是否需要 alpha 通道

        Returns:
            最佳 QImage.Format
        """
        if self._mode == ColorDepthMode.FORCE_8BIT:
            return QImage.Format.Format_ARGB32 if need_alpha else QImage.Format.Format_RGB32

        if self._mode == ColorDepthMode.FORCE_16BIT:
            return QImage.Format.Format_RGBA64 if need_alpha else QImage.Format.Format_RGBX64

        if self._mode == ColorDepthMode.FORCE_10BIT:
            # 10bit 在 Qt 中没有原生格式，使用 16bit 容器承载
            # 实际 10bit 精度由 OpenGL surface format 控制
            if depth_info.is_high_bit_depth:
                return QImage.Format.Format_RGBA64 if need_alpha else QImage.Format.Format_RGBX64
            return QImage.Format.Format_ARGB32 if need_alpha else QImage.Format.Format_RGB32

        # AUTO 模式：根据图像原始位深自适应
        if depth_info.is_high_bit_depth:
            return QImage.Format.Format_RGBA64 if need_alpha else QImage.Format.Format_RGBX64
        return QImage.Format.Format_ARGB32 if need_alpha else QImage.Format.Format_RGB32

    def get_export_format(self, depth_info: ImageColorDepthInfo,
                          file_format: str = "png",
                          need_alpha: bool = True) -> QImage.Format:
        """
        根据导出文件格式和色深模式，返回最佳导出 QImage 格式。
        Select the optimal export QImage format.

        注意：JPEG 不支持 16bit，会自动降级到 8bit。
        Note: JPEG doesn't support 16bit, will auto-downgrade to 8bit.

        Args:
            depth_info: 图像色深信息
            file_format: 目标文件格式 ("png", "jpg", "bmp", "tiff")
            need_alpha: 是否需要 alpha 通道

        Returns:
            最佳导出 QImage.Format
        """
        fmt_lower = file_format.lower()

        # JPEG/BMP 不支持 16bit，强制降级
        if fmt_lower in ("jpg", "jpeg", "bmp"):
            if need_alpha:
                return QImage.Format.Format_ARGB32
            return QImage.Format.Format_RGB32

        # PNG/TIFF 支持 16bit
        return self.get_optimal_format(depth_info, need_alpha)

    # ────────────────────────────────────────────
    # 3. OpenGL Surface 配置 / OpenGL Surface configuration
    # ────────────────────────────────────────────

    def configure_surface_format(self, need_alpha: bool = False) -> QSurfaceFormat:
        """
        根据当前色深模式配置 OpenGL surface format。
        Configure OpenGL surface format based on current color depth mode.

        Args:
            need_alpha: 是否需要完整 alpha 通道（亚克力透明穿透需要 ≥ 8bit alpha）
                        When True, ensures alphaBufferSize >= 8 for DWM acrylic passthrough.

        Returns:
            配置好的 QSurfaceFormat
        """
        fmt = QSurfaceFormat()

        if self._mode == ColorDepthMode.FORCE_8BIT:
            # 标准 8bit RGBA
            fmt.setRedBufferSize(8)
            fmt.setGreenBufferSize(8)
            fmt.setBlueBufferSize(8)
            fmt.setAlphaBufferSize(8)
            print("[ColorDepthManager] OpenGL Surface: 8-8-8-8 (32bit)")

        elif self._mode == ColorDepthMode.FORCE_10BIT:
            # 10bit RGB + alpha（亚克力需要 8bit alpha，否则 2bit）
            # 10bit RGB + alpha (acrylic needs 8bit alpha, otherwise 2bit)
            alpha_bits = 8 if need_alpha else 2
            fmt.setRedBufferSize(10)
            fmt.setGreenBufferSize(10)
            fmt.setBlueBufferSize(10)
            fmt.setAlphaBufferSize(alpha_bits)
            print(f"[ColorDepthManager] OpenGL Surface: 10-10-10-{alpha_bits} ({'acrylic' if need_alpha else 'standard'})")

        elif self._mode == ColorDepthMode.FORCE_16BIT:
            # 16bit RGBA（需要 GPU 支持 RGBA16F 或 RGBA16）
            fmt.setRedBufferSize(16)
            fmt.setGreenBufferSize(16)
            fmt.setBlueBufferSize(16)
            fmt.setAlphaBufferSize(16)
            print("[ColorDepthManager] OpenGL Surface: 16-16-16-16 (64bit)")

        else:
            # AUTO 模式：默认请求 10bit，驱动会自动降级到硬件支持的最高位深
            # 亚克力模式需要 8bit alpha 以支持 DWM 透明穿透
            alpha_bits = 8 if need_alpha else 2
            fmt.setRedBufferSize(10)
            fmt.setGreenBufferSize(10)
            fmt.setBlueBufferSize(10)
            fmt.setAlphaBufferSize(alpha_bits)
            print(f"[ColorDepthManager] OpenGL Surface: AUTO (请求 10-10-10-{alpha_bits}，驱动自适应)")

        # 通用设置
        fmt.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)
        fmt.setSamples(4)  # 4x MSAA 抗锯齿

        return fmt

    @staticmethod
    def apply_surface_format(fmt: QSurfaceFormat):
        """
        将 surface format 应用为全局默认。
        Apply surface format as global default.
        必须在 QApplication 创建之前调用。
        Must be called BEFORE QApplication is created.
        """
        QSurfaceFormat.setDefaultFormat(fmt)
        print("[ColorDepthManager] 已应用全局 OpenGL Surface Format")

    # ────────────────────────────────────────────
    # 4. 图像转换工具 / Image conversion utilities
    # ────────────────────────────────────────────

    def convert_image(self, image: QImage) -> QImage:
        """
        根据当前色深模式转换图像格式。
        Convert image format based on current color depth mode.

        如果图像已经是目标格式，直接返回（零拷贝）。
        If image is already in target format, return as-is (zero-copy).

        Args:
            image: 源 QImage

        Returns:
            转换后的 QImage（可能是同一对象）
        """
        if image.isNull():
            return image

        depth_info = self.detect_image_depth(image)
        target_format = self.get_optimal_format(depth_info, depth_info.has_alpha)

        # 如果已经是目标格式，零拷贝返回
        if image.format() == target_format:
            return image

        converted = image.convertToFormat(target_format)
        print(f"[ColorDepthManager] 图像格式转换: {image.format()} → {target_format} "
              f"(原始 {depth_info.bits_per_channel}bit)")
        return converted

    @staticmethod
    def get_display_depth_info(mode: ColorDepthMode) -> str:
        """
        获取色深模式的人类可读描述。
        Get human-readable description of color depth mode.
        """
        descriptions = {
            ColorDepthMode.AUTO: "自适应 (Auto)",
            ColorDepthMode.FORCE_8BIT: "8bit (标准色深)",
            ColorDepthMode.FORCE_10BIT: "10bit (高色深)",
            ColorDepthMode.FORCE_16BIT: "16bit (最高精度)",
        }
        return descriptions.get(mode, "未知")

    @staticmethod
    def get_mode_from_string(mode_str: str) -> ColorDepthMode:
        """
        从字符串解析色深模式。
        Parse color depth mode from string.
        """
        for mode in ColorDepthMode:
            if mode.value == mode_str:
                return mode
        return ColorDepthMode.AUTO  # 默认自适应
