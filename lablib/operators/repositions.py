from abc import abstractmethod
from dataclasses import dataclass, field
from typing import List

from lablib.lib.utils import (
    identity_matrix,
    transpose_matrix,
    matrix_to_csv,
    calculate_matrix,
    mult_matrix,
)

from .base import BaseOperator


class RepositionOperator(BaseOperator):
    """Base class for reposition operators.

    Currently this is only used for type checking.
    """

    @classmethod
    @abstractmethod
    def from_node_data(cls, data) -> "RepositionOperator":
        """An abstract method for returning a reposition operator from node data.

        Attributes:
            data (dict): The node data.

        Returns:
            RepositionOperator: The reposition operator.
        """
        pass

    @abstractmethod
    def to_oiio_args(self) -> List[str]:
        """An abstract method for returning the arguments for ``oiiotool``.

        Returns:
            List[str]: Arguments for OIIO.
        """
        pass


@dataclass
class Transform(RepositionOperator):
    """Transform operator for repositioning images.

    Note:
        The transformations are applied in the following order:
        ``translate, rotate, scale, center, invert, skewX, skewY``.

        The :obj:`Transform.skew_order` parameter determines the order in which the skewX and skewY transformations are applied.

    Attributes:
        translate (List[float]): The translation vector.
        rotate (float): The rotation angle in degrees.
        scale (List[float]): The scaling vector.
        center (List[float]): The center of the transformation.
        invert (bool): Invert the transformation.
        skewX (float): The skew in the X direction.
        skewY (float): The skew in the Y direction.
        skew_order (str): The order in which the skewX and skewY
            transformations are applied.
    """

    translate: List[float] = field(default_factory=lambda: [0.0, 0.0])
    rotate: float = 0.0
    # needs to be treated as a list of floats but can be single float
    scale: List[float] = field(default_factory=lambda: [1.0, 1.0])
    center: List[float] = field(default_factory=lambda: [0.0, 0.0])
    invert: bool = False
    skewX: float = 0.0
    skewY: float = 0.0
    skew_order: str = "XY"

    def to_oiio_args(self) -> List[str]:
        """Gets the arguments for ``oiiotool``.

        Uses :obj:`lablib.lib` to work with transformation matrices.

        Returns:
            List[str]: Arguments for OIIO.
        """
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
    def from_node_data(cls, data) -> "Transform":
        """Create a :obj:`Transform` object from node data.

        Attributes:
            data (dict): The node data.

        Returns:
            Transform: The transform object.
        """
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
class Crop(RepositionOperator):
    """Operator for cropping images.

    Attributes:
        box (List[int]): The crop box.
    """

    box: List[int] = field(default_factory=lambda: [0, 0, 1920, 1080])
    # NOTE: could also be called with width, height, x, y

    def to_oiio_args(self) -> List[str]:
        """Gets the arguments for ``oiiotool``.

        Returns:
            List[int]: Arguments for OIIO.
        """
        return [
            "--crop",
            # using xmin,ymin,xmax,ymax
            f"{self.box[0]},{self.box[1]},{self.box[2]},{self.box[3]}",
        ]

    @classmethod
    def from_node_data(cls, data) -> "Crop":
        """Create a :obj:`Crop` object from node data.

        Attributes:
            data (dict): The node data.

        Returns:
            Crop: The crop object.
        """
        return cls(box=data.get("box", [0, 0, 1920, 1080]))


@dataclass
class Mirror2(RepositionOperator):
    """Operator for mirroring images.

    TODO:
        This should be ``Mirror2 -> Mirror2D`` looking at :obj:`CornerPin2D`.

    Attributes:
        flop (bool): Mirror vertically.
        flip (bool): Mirror horizontally.
    """

    flop: bool = False
    flip: bool = False

    def to_oiio_args(self):
        """Gets the arguments for ``oiiotool``.

        Returns:
            List[str]: Arguments for OIIO.
        """
        args = []
        if self.flop:
            args.append("--flop")
        if self.flip:
            args.append("--flip")
        return args

    @classmethod
    def from_node_data(cls, data) -> "Mirror2":
        """Create :obj:`Mirror2` from node data.

        Attributes:
            data (dict): The node data.

        Returns:
            Mirror2: The mirror object.
        """
        return cls(flop=data.get("flop", False), flip=data.get("flip", False))


@dataclass
class CornerPin2D(RepositionOperator):
    """Operator for corner pinning images.

    Danger:
        This operator is not yet tested or used in the codebase.

    Attributes:
        from1 (List[float]): The first corner of the source image.
        from2 (List[float]): The second corner of the source image.
        from3 (List[float]): The third corner of the source image.
        from4 (List[float]): The fourth corner of the source image.
        to1 (List[float]): The first corner of the destination image.
        to2 (List[float]): The second corner of the destination image.
        to3 (List[float]): The third corner of the destination image.
        to4 (List[float]): The fourth corner of the destination image.
    """

    from1: List[float] = field(default_factory=lambda: [0.0, 0.0])
    from2: List[float] = field(default_factory=lambda: [0.0, 0.0])
    from3: List[float] = field(default_factory=lambda: [0.0, 0.0])
    from4: List[float] = field(default_factory=lambda: [0.0, 0.0])
    to1: List[float] = field(default_factory=lambda: [0.0, 0.0])
    to2: List[float] = field(default_factory=lambda: [0.0, 0.0])
    to3: List[float] = field(default_factory=lambda: [0.0, 0.0])
    to4: List[float] = field(default_factory=lambda: [0.0, 0.0])

    def to_oiio_args(self):
        """Gets the arguments for ``oiiotool``.

        Returns:
            List[str]: Arguments for OIIO.
        """
        # TODO: use matrix operation from utils.py
        return []

    @classmethod
    def from_node_data(cls, data) -> "CornerPin2D":
        """Create :obj:`CornerPin2D` from node data.

        Attributes:
            data (dict): The node data.

        Returns:
            CornerPin2D: The corner pin object.
        """
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
