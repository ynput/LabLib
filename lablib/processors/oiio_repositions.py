from __future__ import annotations

import inspect
import logging
from typing import Any, List
from dataclasses import dataclass, field


from ..operators import repositions


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


@dataclass
class OIIORepositionProcessor:
    operators: List[Any] = field(default_factory=list)

    # this is basically a Reformat operator
    src_width: int = 0
    dst_width: int = 0
    src_height: int = 0
    dst_height: int = 0
    fit: str = False

    _wrapper_class_members = dict(inspect.getmembers(repositions, inspect.isclass))

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
