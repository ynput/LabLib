# This file contains utility functions for the operators.
from typing import Union

import PyOpenColorIO as OCIO


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
