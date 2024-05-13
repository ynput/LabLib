from dataclasses import dataclass, field
from typing import List


@dataclass
class Transform:
    translate: List[float] = field(default_factory=lambda: [0.0, 0.0])
    rotate: float = 0.0
    scale: List[float] = field(default_factory=lambda: [0.0, 0.0])
    center: List[float] = field(default_factory=lambda: [0.0, 0.0])

    def to_oiio_args(self):
        # TODO: use utils.py to convert to matrix
        return [
            # TODO: make sure this is correct for oiio
            f"--translate {self.translate[0]} {self.translate[1]}",
            f"--rotate {self.rotate}",
            f"--scale {self.scale[0]} {self.scale[1]}",
            f"--center {self.center[0]} {self.center[1]}",
        ]


@dataclass
class Crop:
    top: int = 0
    left: int = 0
    bottom: int = 0
    right: int = 0

    def to_oiio_args(self):
        return [
            # TODO: make sure this is correct for oiio
            f"--crop {self.left}x{self.top}x{self.right}x{self.bottom}",
        ]


@dataclass
class Resize:
    width: int = 0
    height: int = 0

    def to_oiio_args(self):
        return [
            # TODO: make sure this is correct for oiio
            f"--resize {self.width}x{self.height}",
        ]


@dataclass
class CornerPin:
    tl: List[float] = field(default_factory=lambda: [0.0, 0.0])
    tr: List[float] = field(default_factory=lambda: [0.0, 0.0])
    bl: List[float] = field(default_factory=lambda: [0.0, 0.0])
    br: List[float] = field(default_factory=lambda: [0.0, 0.0])

    def to_oiio_args(self):
        # TODO: use matrix operation from utils.py
        pass
