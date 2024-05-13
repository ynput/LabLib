from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Union

import PyOpenColorIO as ocio


@dataclass
class OCIOFileTransform:
    file: str = ""
    cccid: str = ""
    direction: int = 0
    interpolation: str = "linear"

    def to_ocio_obj(self):
        return [
            ocio.FileTransform(
                src=Path(self.file).as_posix(),
                cccid=self.cccid,
                interpolation=self.interpolation,
                direction=self.direction,
            )
        ]

    @classmethod
    def from_node_data(cls, data):
        return cls(
            src=data.get("file", ""),
            cccid=data.get("cccid", ""),
            direction=data.get("direction", 0),
            interpolation=data.get("interpolation", "linear")
        )


@dataclass
class OCIOColorSpace:
    in_colorspace: str = "ACES - ACEScg"
    out_colorspace: str = "ACES - ACEScg"

    def to_ocio_obj(self):
        return [
            ocio.ColorSpaceTransform(
                src=self.in_colorspace,
                dst=self.out_colorspace,
            )
        ]

    @classmethod
    def from_node_data(cls, data):
        return cls(
            src=data.get("in_colorspace", ""),
            dst=data.get("out_colorspace", ""),
        )


@dataclass
class OCIOCDLTransform:
    file: str = ""
    direction: int = 0
    offset: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    power: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    slope: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    saturation: float = 1.0

    def to_ocio_obj(self):
        effects = []
        lut_file = Path(self.file)

        # add LUT file file attr was used
        if lut_file.exists():
            effects.append(
                ocio.FileTransform(
                    src=lut_file.as_posix(),
                    interpolation="linear",
                    direction=self.direction,
                )
            )

        effects.append(
            ocio.CDLTransform(
                slope=self.slope,
                offset=self.offset,
                power=self.power,
                sat=self.saturation,
                direction=self.direction,
            )
        )

        return effects
