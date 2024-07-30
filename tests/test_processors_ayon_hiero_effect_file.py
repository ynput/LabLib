import pytest
import logging
from pathlib import Path

from lablib.processors import AYONHieroEffectsFileProcessor

log = logging.getLogger(__name__)

ABS_MODULE_PATH = Path(__file__).resolve().parent.parent.as_posix()


class TestAYONHieroEffectFileProcessor:

    @pytest.mark.parametrize(
        "kwargs,results",
        [
            (
                {
                    "filepath": Path(
                        "resources/public/effectPlateMain/v000/"
                        "BLD_010_0010_effectPlateMain_v000.json"
                    ),
                    "target_path": Path(
                        "published/ociolookMain/v006/"
                        "john_ociolookMain_v006.json"
                    ),
                    "logger": log,
                },
                {
                    "expected_path": Path(
                        "resources/public/ociolookMain/v005/"
                        "jp03_john_ociolookMain_v005.json"
                    ),
                    "expected_length": 5,
                    "expected_target_file": "john_ociolookMain_v006.cube",
                    "expected_cmd": [
                        "--colorconvert",
                        "ACES - ACEScg",
                        "Output - sRGB",
                        "--ociofiletransform",
                        "john_ociolookMain_v006.cube",
                        "--colorconvert",
                        "ACES - ACEScc",
                        "ACES - ACEScg",
                    ],
                },
            ),
            (
                {
                    "filepath": Path(
                        "resources/public/effectPlateMain/v000/"
                        "BLD_010_0010_effectPlateMain_v000.json"
                    )
                },
                {
                    "expected_path": Path(
                        "resources/public/ociolookMain/v005/"
                        "jp03_john_ociolookMain_v005.json"
                    ),
                    "expected_length": 5,
                    "expected_target_file": (
                        f"{ABS_MODULE_PATH}/resources/public/ociolookMain/"
                        "v005/jp03_john_ociolookMain_v005.cube"
                    ),
                    "expected_cmd": [
                        "--colorconvert",
                        "ACES - ACEScg",
                        "Output - sRGB",
                        "--ociofiletransform",
                        (
                            f"{ABS_MODULE_PATH}/resources/public/ociolookMain/"
                            "v005/jp03_john_ociolookMain_v005.cube"
                        ),
                        "--colorconvert",
                        "ACES - ACEScc",
                        "ACES - ACEScg",
                    ],
                },
            ),
        ],
    )
    def test_EffectsFileProcessor(self, kwargs, results):

        processor = AYONHieroEffectsFileProcessor(**kwargs)
        log.debug(f"Processor: {processor = }")

        log.debug(processor.operator)
        assert processor.filepath == results["expected_path"]
        assert processor.get_oiiotool_cmd() == results["expected_cmd"]
        # FileTransform
        assert len(processor.operator.to_ocio_obj()) == results[
            "expected_length"]
        assert (
            processor.operator.ocioLookItems[0]["file"]
            == results["expected_target_file"]
        )
