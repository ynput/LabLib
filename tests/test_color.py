import pytest
import logging
from pathlib import Path
import PyOpenColorIO as OCIO

from lablib.operators import (
    OCIOFileTransform,
    OCIOColorSpace,
    OCIOCDLTransform,
)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


@pytest.mark.parametrize(
    "data",
    [
        {
            "file": "resources/public/effectPlateMain/v000/resources/BLD_Ext_D_2-Sin709.cube",
            "cccid": "TEST_CCCID",
            "direction": 0,
            "interpolation": "linear",
        },
    ],
)
def test_OCIOFileTransform(data: dict):
    lut_file = Path(data["file"]).as_posix()
    lut = OCIOFileTransform.from_node_data(data)
    lut_obj = lut.to_ocio_obj()
    expected_direction = OCIO.TransformDirection.TRANSFORM_DIR_FORWARD
    expected_interpolation = OCIO.Interpolation.INTERP_LINEAR
    assert len(lut_obj) == 1
    assert lut_obj[0].getSrc() == lut_file
    assert lut_obj[0].getCCCId() == "TEST_CCCID"
    assert lut_obj[0].getDirection() == expected_direction
    assert lut_obj[0].getInterpolation() == expected_interpolation

    log.info(f"{lut = }")


@pytest.mark.parametrize(
    "data",
    [
        {
            "in_colorspace": "ACES - ACEScg",
            "out_colorspace": "ACES - ACEScc",
        },
    ],
)
def test_OCIOColorSpace(data: dict):
    colorspace = OCIOColorSpace.from_node_data(data)
    colorspace_obj = colorspace.to_ocio_obj()

    assert len(colorspace_obj) == 1
    assert colorspace_obj[0].getSrc() == data["in_colorspace"]
    assert colorspace_obj[0].getDst() == data["out_colorspace"]

    log.info(f"{colorspace_obj = }")


@pytest.mark.parametrize(
    "data",
    [
        {
            "file": "resources/public/effectPlateMain/v000/resources/BLD_010_0010.cc",
            "slope": [1.0, 1.0, 1.0],
            "offset": [0.0, 0.0, 0.0],
            "power": [1.0, 1.0, 1.0],
            "saturation": 1.0,
            "interpolation": "nearest",
        },
        {
            "slope": [1.0, 1.0, 1.0],
            "offset": [0.0, 0.0, 0.0],
            "power": [1.0, 1.0, 1.0],
            "saturation": 1.0,
        },
    ],
)
def test_OCIOCDLTransform(data: dict):
    cdl = OCIOCDLTransform.from_node_data(data)
    cdl_obj = cdl.to_ocio_obj()

    expected_len = 1
    if data.get("file"):
        expected_len = 2
        file_transform = cdl_obj[0]
        cdl_transform = cdl_obj[1]
        expected_interpolation = OCIO.Interpolation.INTERP_NEAREST
        assert file_transform.getSrc() == data["file"]
        assert file_transform.getInterpolation() == expected_interpolation
    else:
        cdl_transform = cdl_obj[0]

    print(f"{cdl_obj = }")
    assert len(cdl_obj) == expected_len
    assert cdl_transform.getSlope() == data["slope"]
    assert cdl_transform.getOffset() == data["offset"]
    assert cdl_transform.getPower() == data["power"]
    assert cdl_transform.getSat() == data["saturation"]

    log.info(f"{cdl_obj = }")
