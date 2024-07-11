"""Processors providing positional effect arguments for OIIO."""

from __future__ import annotations

import inspect
import logging
from typing import Any, List

from ..operators import repositions


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class OIIORepositionProcessor:
    """Processor for repositioning images.

    You can use this processor without operators only specifying ``dst_width`` or ``dst_height``.
    This way OIIORepositionProcessor will act as a basic reformat.

    Attributes:
        operators (List): The list of repositioning operators.
        src_width (int): The source image width.
        dst_width (int): The destination image width.
        src_height (int): The source image height.
        dst_height (int): The destination image height.
        fit (str): The fit mode for the image.
    """

    operators: List[Any] = []
    src_width: int = 0
    dst_width: int = 0
    src_height: int = 0
    dst_height: int = 0
    fit: str = None

    _wrapper_class_members = dict(inspect.getmembers(repositions, inspect.isclass))

    def __init__(self, **kwargs) -> None:
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def __repr__(self) -> str:
        exposed_props = ["operators", "dst_width", "dst_height", "fit"]
        props = ""
        for prop in exposed_props:
            props = props + f"{prop}={getattr(self, prop)}, "

        return f"{self.__class__.__name__}({props[:-2]})"

    def get_oiiotool_cmd(self) -> List:
        """Get the OIIO arguments for repositioning images.

        Returns:
            List[str]: The OIIO arguments.
        """
        result = []
        for op in self.operators:
            result.extend(op.to_oiio_args())

        if any([self.dst_height, self.dst_width]):
            dest_size = f"{self.dst_width}x{self.dst_height}"
            # TODO: check with renderer
            if self.fit in ["letterbox", "width", "height"]:
                result.extend([f"--fit:fillmode={self.fit}", dest_size])
            else:
                result.extend(["--resize", dest_size])

        log.debug(f"{result = }")
        return result
