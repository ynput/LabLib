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


class TestColorOperators:

    @pytest.mark.parametrize(
        "data",
        [
            {
                "file": (
                    "resources/public/effectPlateMain/v000/"
                    "resources/BLD_Ext_D_2-Sin709.cube"
                ),
                "cccid": "TEST_CCCID",
                "direction": 0,
                "interpolation": "linear",
            },
        ],
    )
    def test_OCIOFileTransform(self, data: dict):
        lut_file = Path(data["file"]).as_posix()
        op_obj = OCIOFileTransform.from_node_data(data)
        ocio_obj = op_obj.to_ocio_obj()
        expected_direction = OCIO.TransformDirection.TRANSFORM_DIR_FORWARD
        expected_interpolation = OCIO.Interpolation.INTERP_LINEAR

        assert ocio_obj.getSrc() == lut_file
        assert ocio_obj.getCCCId() == "TEST_CCCID"
        assert ocio_obj.getDirection() == expected_direction
        assert ocio_obj.getInterpolation() == expected_interpolation

        log.debug(f"{op_obj = }")

    @pytest.mark.parametrize(
        "data",
        [
            {
                "in_colorspace": "ACES - ACEScg",
                "out_colorspace": "ACES - ACEScc",
            },
        ],
    )
    def test_OCIOColorSpace(self, data: dict):
        op_obj = OCIOColorSpace.from_node_data(data)
        ocio_obj = op_obj.to_ocio_obj()

        assert ocio_obj.getSrc() == data["in_colorspace"]
        assert ocio_obj.getDst() == data["out_colorspace"]

        log.debug(f"{ocio_obj = }")

    @pytest.mark.parametrize(
        "data,expected",
        [
            (
                {
                    "file": (
                        "resources/public/effectPlateMain/v000/"
                        "resources/BLD_010_0010.cc"
                    ),
                    "slope": [1.0, 1.0, 1.0],
                    "offset": [0.0, 0.0, 0.0],
                    "power": [1.0, 1.0, 1.0],
                    "saturation": 1.0,
                    "interpolation": "nearest",
                },
                {
                    "file": (
                        "resources/public/effectPlateMain/v000/"
                        "resources/BLD_010_0010.cc"
                    ),
                    "interpolation": OCIO.Interpolation.INTERP_NEAREST,
                },
            ),
            (
                {
                    "slope": [1.0, 1.0, 1.0],
                    "offset": [0.0, 0.0, 0.0],
                    "power": [1.0, 1.0, 1.0],
                    "saturation": 1.0,
                },
                {
                    "slope": [1.0, 1.0, 1.0],
                    "offset": [0.0, 0.0, 0.0],
                    "power": [1.0, 1.0, 1.0],
                    "saturation": 1.0,
                },
            ),
        ],
    )
    def test_OCIOCDLTransform(self, data: dict, expected: dict):
        op_obj = OCIOCDLTransform.from_node_data(data)
        ocio_obj = op_obj.to_ocio_obj()

        # sourcery skip: no-conditionals-in-tests
        if data.get("file"):
            assert ocio_obj.getSrc() == expected["file"]
            assert ocio_obj.getInterpolation() == expected["interpolation"]
        else:
            assert ocio_obj.getSlope() == expected["slope"]
            assert ocio_obj.getOffset() == expected["offset"]
            assert ocio_obj.getPower() == expected["power"]
            assert ocio_obj.getSat() == expected["saturation"]

        log.debug(f"{ocio_obj = }")
