from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

import PyOpenColorIO as OCIO


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


@dataclass
class OCIOFileTransform:
    """Foundry Hiero Timeline soft effect node class"""

    file: str = ""
    cccid: str = ""
    direction: int = 0
    interpolation: str = "linear"

    def to_ocio_obj(self):
        # define direction
        direction = get_direction(self.direction)

        # define interpolation
        interpolation = get_interpolation(self.interpolation)

        return [
            OCIO.FileTransform(
                src=Path(self.file).as_posix(),
                cccId=self.cccid,
                direction=direction,
                interpolation=interpolation,
            )
        ]

    @classmethod
    def from_node_data(cls, data):
        return cls(
            file=data.get("file", ""),
            cccid=data.get("cccid", ""),
            direction=data.get("direction", 0),
            interpolation=data.get("interpolation", "linear"),
        )


@dataclass
class OCIOColorSpace:
    """Foundry Hiero Timeline soft effect node class"""

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
    """Foundry Hiero Timeline soft effect node class.

    Since this node class combines two of OCIO classes (FileTransform and
    CDLTransform), we will separate them here within `to_ocio_obj` method.
    """

    file: Optional[str] = None
    direction: int = 0
    cccid: str = ""
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
                    cccId=self.cccid,
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
                cccid=data.get("cccid", ""),
            )
        else:
            return cls(
                direction=data.get("direction", 0),
                offset=data.get("offset", [0.0, 0.0, 0.0]),
                power=data.get("power", [1.0, 1.0, 1.0]),
                slope=data.get("slope", [0.0, 0.0, 0.0]),
                saturation=data.get("saturation", 1.0),
            )


@dataclass
class AYONOCIOLookProduct:
    """AYON ocioLook product dataclass

    This class will hold all the necessary data for the ocioLook product, so
    it can be covered into FileTransform and ColorSpaceTransform during
    `to_ocio_obj` method.

    .. admonition:: Example of input data

        .. code-block::

            {
                "ocioLookItems": [
                    {
                        "name": "LUTfile",
                        "file: "path/to/lut.cube", # currently created via processor
                        "ext": "cube",
                        "input_colorspace": {
                            "colorspace": "Output - sRGB",
                            "name": "color_picking",
                            "type": "roles"
                        },
                        "output_colorspace": {
                            "colorspace": "ACES - ACEScc",
                            "name": "color_timing",
                            "type": "roles"
                        },
                        "direction": "forward",
                        "interpolation": "tetrahedral",
                        "config_data": {
                            "path": "path/to/config.ocio",
                            "template": "{BUILTIN_OCIO_ROOT}/aces_1.2/config.ocio",
                            "colorspace": "compositing_linear"
                        },
                    },
                ],
                "ocioLookWorkingSpace": {
                    "colorspace": "ACES - ACEScg",
                    "name": "compositing_linear",
                    "type": "roles"
                },
            },
    """

    ocioLookItems: List[dict] = field(default_factory=list)
    ocioLookWorkingSpace: dict = field(default_factory=dict)

    def to_ocio_obj(self):
        look_working_colorspace = self.ocioLookWorkingSpace["colorspace"]
        all_transformations = []
        for index, item in enumerate(self.ocioLookItems):
            filepath = item["file"]
            lut_in_colorspace = item["input_colorspace"]["colorspace"]
            lut_out_colorspace = item["output_colorspace"]["colorspace"]
            direction = item["direction"]
            interpolation = item["interpolation"]

            if index == 0:
                # set the first colorspace as the current working colorspace
                current_working_colorspace = look_working_colorspace

            if current_working_colorspace != lut_in_colorspace:
                all_transformations.append(
                    OCIO.ColorSpaceTransform(
                        src=current_working_colorspace,
                        dst=lut_in_colorspace,
                    )
                )

            all_transformations.append(
                OCIO.FileTransform(
                    src=Path(filepath).as_posix(),
                    interpolation=get_interpolation(interpolation),
                    direction=get_direction(direction),
                )
            )

            current_working_colorspace = lut_out_colorspace

        # making sure we are back in the working colorspace
        if current_working_colorspace != look_working_colorspace:
            all_transformations.append(
                OCIO.ColorSpaceTransform(
                    src=current_working_colorspace,
                    dst=look_working_colorspace,
                )
            )

        return all_transformations

    @classmethod
    def from_node_data(cls, data):
        return cls(
            ocioLookItems=data.get("ocioLookItems", []),
            ocioLookWorkingSpace=data.get("ocioLookWorkingSpace", {}),
        )
