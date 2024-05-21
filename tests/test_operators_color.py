import pytest
import logging
from pathlib import Path
import PyOpenColorIO as OCIO

from lablib.operators import (
    OCIOFileTransform,
    OCIOColorSpace,
    OCIOCDLTransform,
    AYONOCIOLookProduct,
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
        lut = OCIOFileTransform.from_node_data(data)
        lut_obj = lut.to_ocio_obj()
        expected_direction = OCIO.TransformDirection.TRANSFORM_DIR_FORWARD
        expected_interpolation = OCIO.Interpolation.INTERP_LINEAR
        assert len(lut_obj) == 1

        # get the ocio object
        ocio_obj = lut_obj.pop()

        assert ocio_obj.getSrc() == lut_file
        assert ocio_obj.getCCCId() == "TEST_CCCID"
        assert ocio_obj.getDirection() == expected_direction
        assert ocio_obj.getInterpolation() == expected_interpolation

        log.debug(f"{lut = }")

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
        colorspace = OCIOColorSpace.from_node_data(data)
        colorspace_obj = colorspace.to_ocio_obj()

        assert len(colorspace_obj) == 1
        # get the ocio object
        ocio_obj = colorspace_obj.pop()

        assert ocio_obj.getSrc() == data["in_colorspace"]
        assert ocio_obj.getDst() == data["out_colorspace"]

        log.debug(f"{colorspace_obj = }")

    @pytest.mark.parametrize(
        "data",
        [
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
                "slope": [1.0, 1.0, 1.0],
                "offset": [0.0, 0.0, 0.0],
                "power": [1.0, 1.0, 1.0],
                "saturation": 1.0,
            },
        ],
    )
    def test_OCIOCDLTransform(self, data: dict):
        cdl = OCIOCDLTransform.from_node_data(data)
        cdl_obj = cdl.to_ocio_obj()

        expected_len = 1
        # sourcery skip: no-conditionals-in-tests
        if data.get("file"):
            expected_len = 2
            file_transform = cdl_obj[0]
            cdl_transform = cdl_obj[1]
            expected_interpolation = OCIO.Interpolation.INTERP_NEAREST
            assert file_transform.getSrc() == data["file"]
            assert file_transform.getInterpolation() == expected_interpolation
        else:
            cdl_transform = cdl_obj[0]

        log.debug(f"{cdl_obj = }")
        assert len(cdl_obj) == expected_len
        assert cdl_transform.getSlope() == data["slope"]
        assert cdl_transform.getOffset() == data["offset"]
        assert cdl_transform.getPower() == data["power"]
        assert cdl_transform.getSat() == data["saturation"]

        log.debug(f"{cdl_obj = }")

    @pytest.mark.parametrize(
        "data, expected_len",
        [
            (
                {
                    "ocioLookItems": [
                        {
                            "file": "path/to/lut1.cube",
                            "input_colorspace": {
                                "colorspace": "Output - sRGB"
                            },
                            "output_colorspace": {
                                "colorspace": "ACES - ACEScc"
                            },
                            "direction": "forward",
                            "interpolation": "tetrahedral"
                        }
                    ],
                    "ocioLookWorkingSpace": {
                        "colorspace": "ACES - ACEScg"
                    },
                },
                3
            ),
            (
                {
                    "ocioLookItems": [
                        {
                            "file": "path/to/lut1.cube",
                            "input_colorspace": {
                                "colorspace": "Output - sRGB"
                            },
                            "output_colorspace": {
                                "colorspace": "ACES - ACEScc"
                            },
                            "direction": "forward",
                            "interpolation": "tetrahedral"
                        },
                        {
                            "file": "path/to/lut2.cube",
                            "input_colorspace": {
                                "colorspace": "Output - Rec.709"
                            },
                            "output_colorspace": {
                                "colorspace": "ACES - ACEScc"
                            },
                            "direction": "forward",
                            "interpolation": "tetrahedral"
                        },
                    ],
                    "ocioLookWorkingSpace": {
                        "colorspace": "ACES - ACEScg"
                    },
                },
                5
            ),
        ],
    )
    def test_AYONOCIOLookProduct(self, data: dict, expected_len: int):
        cdl = AYONOCIOLookProduct.from_node_data(data)
        cdl_obj = cdl.to_ocio_obj()

        log.debug(f"{cdl_obj = }")
        assert len(cdl_obj) == expected_len
