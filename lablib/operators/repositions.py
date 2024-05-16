from dataclasses import dataclass, field
from typing import List

from lablib.lib.utils import flip_matrix


@dataclass
class Transform:
    translate: List[float] = field(default_factory=lambda: [0.0, 0.0])
    rotate: float = 0.0
    # needs to be treated as a list of floats but can be single float
    scale: List[float] = field(default_factory=lambda: [0.0, 0.0])
    center: List[float] = field(default_factory=lambda: [0.0, 0.0])
    invert: bool = False
    skewX: float = 0.0
    skewY: float = 0.0
    skew_order: str = "XY"

    def to_oiio_args(self):
        # TODO: use utils.py to convert to matrix
        return [
            # TODO: make sure this is correct for oiio
            f"--translate {self.translate[0]} {self.translate[1]}",
            f"--rotate {self.rotate}",
            f"--scale {self.scale[0]} {self.scale[1]}",
            f"--center {self.center[0]} {self.center[1]}",
        ]

    @classmethod
    def from_node_data(cls, data):
        scale = data.get("scale", [0.0, 0.0])
        if isinstance(scale, (int, float)):
            scale = [scale, scale]

        return cls(
            translate=data.get("translate", [0.0, 0.0]),
            rotate=data.get("rotate", 0.0),
            scale=scale,
            center=data.get("center", [0.0, 0.0]),
            invert=data.get("invert", False),
            skewX=data.get("skewX", 0.0),
            skewY=data.get("skewY", 0.0),
            skew_order=data.get("skew_order", "XY"),
        )


@dataclass
class Crop:
    box: List[int] = field(default_factory=lambda: [0, 0, 1920, 1080])

    def to_oiio_args(self):
        return [
            # using xmin,ymin,xmax,ymax
            f"--crop {self.box[0]},{self.box[1]},{self.box[2]},{self.box[3]}",
        ]

    @classmethod
    def from_node_data(cls, data):
        return cls(box=data.get("box", [0, 0, 1920, 1080]))


@dataclass
class Mirror2:
    flop: bool = False
    flip: bool = False

    def to_oiio_args(self):
        args = []
        if self.flop:
            args.append("--flop")
        if self.flip:
            args.append("--flip")
        return args

    @classmethod
    def from_node_data(cls, data):
        return cls(flop=data.get("flop", False), flip=data.get("flip", False))


@dataclass
class CornerPin2D:
    from1: List[float] = field(default_factory=lambda: [0.0, 0.0])
    from2: List[float] = field(default_factory=lambda: [0.0, 0.0])
    from3: List[float] = field(default_factory=lambda: [0.0, 0.0])
    from4: List[float] = field(default_factory=lambda: [0.0, 0.0])
    to1: List[float] = field(default_factory=lambda: [0.0, 0.0])
    to2: List[float] = field(default_factory=lambda: [0.0, 0.0])
    to3: List[float] = field(default_factory=lambda: [0.0, 0.0])
    to4: List[float] = field(default_factory=lambda: [0.0, 0.0])

    def to_oiio_args(self):
        # TODO: use matrix operation from utils.py
        return []

    @classmethod
    def from_node_data(cls, data):
        return cls(
            from1=data.get("from1", [0.0, 0.0]),
            from2=data.get("from2", [0.0, 0.0]),
            from3=data.get("from3", [0.0, 0.0]),
            from4=data.get("from4", [0.0, 0.0]),
            to1=data.get("to1", [0.0, 0.0]),
            to2=data.get("to2", [0.0, 0.0]),
            to3=data.get("to3", [0.0, 0.0]),
            to4=data.get("to4", [0.0, 0.0]),
        )
