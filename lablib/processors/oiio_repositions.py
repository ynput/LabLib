from __future__ import annotations

from typing import List
from dataclasses import dataclass, field

from .. import utils


@dataclass
class OIIORepositionProcessor:
    operators: List = field(default_factory=list)
    source_width: int = None
    source_height: int = None
    dest_width: int = None
    dest_height: int = None

    def __post_init__(self):
        self._raw_matrix: List[List[float]] = [[]]
        self._class_search_key = "class"

    def set_source_size(self, width: int, height: int) -> None:
        self.source_width = width
        self.source_height = height

    def set_destination_size(self, width: int, height: int) -> None:
        self.dest_width = width
        self.dest_height = height

    def get_raw_matrix(self) -> List[List[float]]:
        return self._raw_matrix

    def add_operators(self, *args) -> None:
        for a in args:
            if isinstance(a, list):
                self.add_operators(*a)
            else:
                self.operators.append(a)

    def get_matrix_chained(
        self, flip: bool = False, flop: bool = True, reverse_chain: bool = True
    ) -> str:
        chain = []
        tlist = list(self.operators)
        if reverse_chain:
            tlist.reverse()

        if flip:
            chain.append(utils.flip_matrix(self.source_width))

        if flop:
            chain.append(utils.flop_matrix(self.source_height))

        for xform in tlist:
            chain.append(
                utils.calculate_matrix(
                    t=xform.translate, r=xform.rotate, s=xform.scale, c=xform.center
                )
            )

        if flop:
            chain.append(utils.flop_matrix(self.source_height))

        if flip:
            chain.append(utils.flip_matrix(self.source_width))

        result = utils.identity_matrix()
        for m in chain:
            result = utils.mult_matrix(result, m)
        self._raw_matrix = result
        return result

    def get_cornerpin_data(self, matrix: List[List[float]]) -> List:
        return utils.matrix_to_cornerpin(
            m=matrix, w=self.source_width, h=self.source_height, origin_upperleft=False
        )

    def get_oiiotool_cmd(self) -> List:
        if not self.source_width:
            raise ValueError(f"Missing source width!")
        if not self.source_height:
            raise ValueError(f"Missing source height!")
        if not self.dest_width:
            raise ValueError(f"Missing destination width!")
        if not self.dest_height:
            raise ValueError(f"Missing destination height!")

        matrix = self.get_matrix_chained()
        matrix_tr = utils.transpose_matrix(matrix)
        warp_cmd = utils.matrix_to_csv(matrix_tr)

        src_aspect = self.source_width / self.source_height
        dest_aspect = self.dest_width / self.dest_height

        fitted_width = self.source_width
        fitted_height = self.source_height

        x_offset = 0
        y_offset = 0
        if src_aspect > dest_aspect:
            fitted_height = int(self.source_width / dest_aspect)
            y_offset = int((fitted_height - self.source_height) / 2)

        elif src_aspect < dest_aspect:
            fitted_width = int(self.source_height * dest_aspect)
            x_offset = int((fitted_width - self.source_width) / 2)

        cropped_area = "{}x{}-{}-{}".format(
            fitted_width, fitted_height, x_offset, y_offset
        )
        dest_size = f"{self.dest_width}x{self.dest_height}"

        return [
            "--warp:filter=cubic:recompute_roi=1",
            warp_cmd,
            "--crop",
            cropped_area,
            "--fullsize",
            cropped_area,
            "--resize",
            dest_size,
        ]
