from dataclasses import dataclass, field
from typing import List


@dataclass
class Transform:
    translate: List[float] = field(default_factory=lambda: [0.0, 0.0])
    rotate: float = 0.0
    scale: List[float] = field(default_factory=lambda: [0.0, 0.0])
    center: List[float] = field(default_factory=lambda: [0.0, 0.0])


@dataclass
class Crop:
    top: int = 0
    left: int = 0
    bottom: int = 0
    right: int = 0


@dataclass
class Resize:
    width: int = 0
    height: int = 0


@dataclass
class CornerPin:
    tl: List[float] = field(default_factory=lambda: [0.0, 0.0])
    tr: List[float] = field(default_factory=lambda: [0.0, 0.0])
    bl: List[float] = field(default_factory=lambda: [0.0, 0.0])
    br: List[float] = field(default_factory=lambda: [0.0, 0.0])