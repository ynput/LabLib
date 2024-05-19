from dataclasses import dataclass, field
from typing import List

from lablib.lib.utils import (
    identity_matrix,
    transpose_matrix,
    matrix_to_csv,
    calculate_matrix,
    mult_matrix,
)


@dataclass
class Transform:
    translate: List[float] = field(default_factory=lambda: [0.0, 0.0])
    rotate: float = 0.0
    # needs to be treated as a list of floats but can be single float
    scale: List[float] = field(default_factory=lambda: [1.0, 1.0])
    center: List[float] = field(default_factory=lambda: [0.0, 0.0])
    invert: bool = False
    skewX: float = 0.0
    skewY: float = 0.0
    skew_order: str = "XY"

    def to_oiio_args(self):
        matrix = calculate_matrix(
            t=self.translate, r=self.rotate, s=self.scale, c=self.center
        )
        identity = identity_matrix()
        matrix_xfm = mult_matrix(identity, matrix)
        matrix_tr = transpose_matrix(matrix_xfm)
        warp_cmd = matrix_to_csv(matrix_tr)
        warp_flag = "--warp:filter=cubic:recompute_roi=1"  # TODO: expose filter
        return [warp_flag, warp_cmd]

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
    # NOTE: could also be called with width, height, x, y

    def to_oiio_args(self):
        return [
            "--crop",
            # using xmin,ymin,xmax,ymax
            f"{self.box[0]},{self.box[1]},{self.box[2]},{self.box[3]}",
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
