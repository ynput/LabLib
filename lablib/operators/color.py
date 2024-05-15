from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

import PyOpenColorIO as OCIO

from ..lib.imageio import ImageIOBase


def get_direction(direction: Union[str, int]) -> int:
    if direction == "inverse":
        return OCIO.TransformDirection.TRANSFORM_DIR_INVERSE
    return OCIO.TransformDirection.TRANSFORM_DIR_FORWARD


def get_interpolation(interpolation: str) -> int:
    if interpolation == "linear":
        return OCIO.Interpolation.INTERP_LINEAR
    elif interpolation == "best":
        return OCIO.Interpolation.INTERP_BEST
    elif interpolation == "nearest":
        return OCIO.Interpolation.INTERP_NEAREST
    elif interpolation == "tetrahedral":
        return OCIO.Interpolation.INTERP_TETRAHEDRAL
    elif interpolation == "cubic":
        return OCIO.Interpolation.INTERP_CUBIC
    return OCIO.Interpolation.INTERP_DEFAULT


class OCIOFileTransform(ImageIOBase):
    _ocio_obj: OCIO.FileTransform = OCIO.FileTransform()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if not kwargs.get("file"):
            raise ValueError("file is required")
        self.path = kwargs["file"]

        self.log.info(f"{self._ocio_obj = }")
        self.log.info(f"{dir(self._ocio_obj) = }")

    @property
    def source(self):
        return self.path

    @source.setter
    def source(self, value: str):
        self.path = value
        self._ocio_obj.setSrc(value)

    @property
    def file(self):
        return self._ocio_obj.getSrc()

    @file.setter
    def file(self, value: str):
        self.source = value

    @property
    def cccid(self):
        return self._ocio_obj.getCCCId()

    @cccid.setter
    def cccid(self, value: str):
        self._ocio_obj.setCCCId(value)

    @property
    def direction(self):
        self.log.debug(f"{self._ocio_obj.getDirection() = }")
        return self._ocio_obj.getDirection()

    @direction.setter
    def direction(self, value: str):
        self._ocio_obj.setDirection(get_direction(value))

    @property
    def interpolation(self):
        return self._ocio_obj.getInterpolation()

    @interpolation.setter
    def interpolation(self, value: str):
        self._ocio_obj.setInterpolation(get_interpolation(value))


@dataclass
class OCIOColorSpace:
    in_colorspace: str = "ACES - ACEScg"
    out_colorspace: str = "ACES - ACEScg"

    def to_ocio_obj(self):
        return [
            OCIO.ColorSpaceTransform(
                src=self.in_colorspace,
                dst=self.out_colorspace,
            )
        ]

    @classmethod
    def from_node_data(cls, data):
        return cls(
            in_colorspace=data.get("in_colorspace", ""),
            out_colorspace=data.get("out_colorspace", ""),
        )


@dataclass
class OCIOCDLTransform:
    file: Optional[str] = None
    direction: int = 0
    offset: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    power: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    slope: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    saturation: float = 1.0
    interpolation: str = "linear"

    def to_ocio_obj(self):
        effects = []

        # define direction
        direction = get_direction(self.direction)

        if self.file:
            # define interpolation
            interpolation = get_interpolation(self.interpolation)
            lut_file = Path(self.file)

            effects.append(
                OCIO.FileTransform(
                    src=lut_file.as_posix(),
                    interpolation=interpolation,
                    direction=direction,
                )
            )

        effects.append(
            OCIO.CDLTransform(
                slope=self.slope,
                offset=self.offset,
                power=self.power,
                sat=self.saturation,
                direction=direction,
            )
        )

        return effects

    @classmethod
    def from_node_data(cls, data):
        if data.get("file"):
            return cls(
                file=data.get("file", ""),
                interpolation=data.get("interpolation", "linear"),
                direction=data.get("direction", 0),
                offset=data.get("offset", [0.0, 0.0, 0.0]),
                power=data.get("power", [1.0, 1.0, 1.0]),
                slope=data.get("slope", [0.0, 0.0, 0.0]),
                saturation=data.get("saturation", 1.0),
            )
        else:
            return cls(
                direction=data.get("direction", 0),
                offset=data.get("offset", [0.0, 0.0, 0.0]),
                power=data.get("power", [1.0, 1.0, 1.0]),
                slope=data.get("slope", [0.0, 0.0, 0.0]),
                saturation=data.get("saturation", 1.0),
            )
