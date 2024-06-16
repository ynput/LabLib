from __future__ import annotations

import inspect
import logging
from typing import Any, List

from ..operators import repositions


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class OIIORepositionProcessor:
    _wrapper_class_members = dict(inspect.getmembers(repositions, inspect.isclass))

    def __init__(
        self,
        operators: List[Any],
        src_width: int = 0,
        dst_width: int = 0,
        src_height: int = 0,
        dst_height: int = 0,
        fit: str = False,
    ) -> None:
        self.operators = operators
        self.src_width = src_width
        self.dst_width = dst_width
        self.src_height = src_height
        self.dst_height = dst_height
        self.fit = fit

    def __repr__(self) -> str:
        exposed_props = ["operators", "dst_width", "dst_height", "fit"]
        props = ""
        for prop in exposed_props:
            props = props + f"{prop}={getattr(self, prop)}, "

        return f"{self.__class__.__name__}({props[:-2]})"

    def get_oiiotool_cmd(self) -> List:
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
