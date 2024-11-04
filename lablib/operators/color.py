from abc import abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

import PyOpenColorIO as OCIO

from .base import BaseOperator


class ColorOperator(BaseOperator):
    """Base class for color operators.

    Currently this is only used for type checking.
    """

    @classmethod
    @abstractmethod
    def from_node_data(cls, data) -> "ColorOperator":
        """An abstract classmethod for returning a :obj:`ColorOperator` from node data.

        Args:
            data (dict): The node data.

        Returns:
            ColorOperator: The color operator object.
        """
        pass

    @abstractmethod
    def to_ocio_obj(self) -> OCIO.Transform:
        """Converts the object to native OCIO object.

        Raises:
            NotImplementedError: This method must be implemented in the
                subclass.
        """
        pass


@dataclass
class OCIOColorSpace(ColorOperator):
    """Foundry Hiero Timeline soft effect node class.

    Attributes:
        in_colorspace (str): The input colorspace.
            Defaults to "ACES - ACEScg".
        out_colorspace (str): The output colorspace.
            Defaults to "ACES - ACEScg".
    """

    in_colorspace: str = "ACES - ACEScg"
    out_colorspace: str = "ACES - ACEScg"

    def to_ocio_obj(self) -> OCIO.ColorSpaceTransform:
        """Returns native OCIO ColorSpaceTransform object.

        Returns:
            OCIO.ColorSpaceTransform: The OCIO ColorSpaceTransform object.
        """
        return OCIO.ColorSpaceTransform(
            src=self.in_colorspace,
            dst=self.out_colorspace,
        )

    @classmethod
    def from_node_data(cls, data) -> "OCIOColorSpace":
        """Create :obj:`OCIOColorSpace` from node data.

        Arguments:
            data (dict): The node data.

        Returns:
            OCIOColorSpace:
        """
        return cls(
            in_colorspace=data.get("in_colorspace", ""),
            out_colorspace=data.get("out_colorspace", ""),
        )


@dataclass
class OCIOFileTransform(ColorOperator):
    """Class for handling OCIO FileTransform effects.

    Note:
        Reads Foundry Hiero Timeline soft effect node class.

    Attributes:
        file (str): Path to the LUT file.
        cccid (str): Path to the cccid file.
        direction (int): The direction. Defaults to 0.
        interpolation (str): The interpolation. Defaults to "linear".
    """

    file: str = ""
    cccid: str = ""
    direction: int = 0
    interpolation: str = "linear"

    def to_ocio_obj(self) -> OCIO.FileTransform:
        """Converts the object to native OCIO object.

        Returns:
            OCIO.FileTransform: The OCIO FileTransform object in a list.
        """
        # define direction
        direction = get_direction(self.direction)

        # define interpolation
        interpolation = get_interpolation(self.interpolation)

        return OCIO.FileTransform(
            src=Path(self.file).as_posix(),
            cccId=self.cccid,
            direction=direction,
            interpolation=interpolation,
        )

    @classmethod
    def from_node_data(cls, data) -> "OCIOFileTransform":
        """Create :obj:`OCIOFileTransform` from node data.

        Note:
            Reads Foundry Hiero Timeline soft effect node data.

            Would it be cool if we'd had a way to interface other DCC node
            data? Would they even be so much different?

        Args:
            data (dict): The node data. List of expected but not required keys:
                - file (str): Path to the LUT file.
                - cccid (str): Path to the cccid file.
                - direction (int): The direction. Defaults to 0.
                - interpolation (str): The interpolation. Defaults to "linear".


        Returns:
            OCIOFileTransform: The OCIOFileTransform object.
        """
        return cls(
            file=data.get("file", ""),
            cccid=data.get("cccid", ""),
            direction=data.get("direction", 0),
            interpolation=data.get("interpolation", "linear"),
        )


@dataclass
class OCIOCDLTransform(OCIOFileTransform):
    """Foundry Hiero Timeline soft effect node class.

    Note:
        Since this node class combines two of OCIO classes (FileTransform and
        CDLTransform), we will separate them here within
        :obj:`OCIOCDLTransform.to_ocio_obj()`.

    Attributes:
        file (Optional[str]): Path to the LUT file.
        direction (int): The direction. Defaults to 0.
        cccid (str): The cccid. Defaults to "".
        offset (List[float]): The offset. Defaults to [0.0, 0.0, 0.0].
        power (List[float]): The power. Defaults to [1.0, 1.0, 1.0].
        slope (List[float]): The slope. Defaults to [0.0, 0.0, 0.0].
        saturation (float): The saturation. Defaults to 1.0.
        interpolation (str): The interpolation. Defaults to "linear".
    """

    file: Optional[str] = None
    direction: int = 0
    cccid: str = ""
    offset: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    power: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    slope: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    saturation: float = 1.0
    interpolation: str = "linear"

    def to_ocio_obj(self) -> Union[OCIO.FileTransform, OCIO.CDLTransform]:  # noqa: E501
        """Returns native OCIO FileTransform and CDLTransform object.

        Returns:
            Union[OCIO.FileTransform, OCIO.CDLTransform]: Either OCIO
                CDLTransform or FileTransform object.
                If file is not provided, CDLTransform will be returned.
        """

        # define direction
        direction = get_direction(self.direction)

        if self.file:
            # define interpolation
            interpolation = get_interpolation(self.interpolation)
            lut_file = Path(self.file)

            return OCIO.FileTransform(
                src=lut_file.as_posix(),
                cccId=(self.cccid or "0"),
                interpolation=interpolation,
                direction=direction,
            )

        return OCIO.CDLTransform(
            slope=self.slope,
            offset=self.offset,
            power=self.power,
            sat=self.saturation,
            direction=direction,
        )

    @classmethod
    def from_node_data(cls, data) -> "OCIOCDLTransform":
        """Create :obj:`OCIOCDLTransform` from node data.

        Args:
            data (dict): The node data. List of expected but not required keys:
                - file (str): Path to the LUT file.
                - direction (int): The direction.
                    Defaults to 0.
                - cccid (str): The cccid.
                    Defaults to "".
                - offset (List[float]): The offset.
                    Defaults to [0.0, 0.0, 0.0].
                - power (List[float]): The power.
                    Defaults to [1.0, 1.0, 1.0].
                - slope (List[float]): The slope.
                    Defaults to [0.0, 0.0, 0.0].
                - saturation (float): The saturation.
                    Defaults to 1.0.
                - interpolation (str): The interpolation.
                    Defaults to "linear".

        Returns:
            OCIOCDLTransform: The OCIOCDLTransform object.
        """
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


def get_direction(direction: Union[str, int]) -> int:
    """Get the direction for OCIO FileTransform.

    Attributes:
        direction (Union[str, int]): The direction.

    Returns:
        int: The direction.
    """
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
