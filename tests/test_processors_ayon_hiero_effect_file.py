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
                    "target_dir_path": Path(
                        "published/effectPlateMain/v020/resources"),
                    "logger": log,
                },
                {
                    "expected_path": Path(
                        "resources/public/effectPlateMain/v000/"
                        "BLD_010_0010_effectPlateMain_v000.json"
                    ),
                    "expected_length": 5,
                    "expected_cmd": [
                        "--colorconvert",
                        "scene_linear",
                        "Input - Sony - S-Log3 - S-Gamut3.Cine",
                        "--ociofiletransform",
                        "published/effectPlateMain/v020/resources/BLD_010_0010.cc",
                        "--ociofiletransform",
                        "published/effectPlateMain/v020/resources/BLD_Ext_D_2-Sin709.cube",
                        "--ociofiletransform",
                        "published/effectPlateMain/v020/resources/Sony_to_709.cube",
                        "--warp:filter=cubic:recompute_roi=1",
                        "1.075,0.0,0.0,0.0,1.075,0.0,-164.32499999999982,-86.625,1.0",
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
                        "resources/public/effectPlateMain/v000/"
                        "BLD_010_0010_effectPlateMain_v000.json"
                    ),
                    "expected_length": 5,
                    "expected_cmd": [
                        "--colorconvert",
                        "scene_linear",
                        "Input - Sony - S-Log3 - S-Gamut3.Cine",
                        "--ociofiletransform",
                        f"{ABS_MODULE_PATH}/resources/public/effectPlateMain/v000/resources/BLD_010_0010.cc",
                        "--ociofiletransform",
                        f"{ABS_MODULE_PATH}/resources/public/effectPlateMain/v000/resources/BLD_Ext_D_2-Sin709.cube",
                        "--ociofiletransform",
                        f"{ABS_MODULE_PATH}/resources/public/effectPlateMain/v000/resources/Sony_to_709.cube",
                        "--warp:filter=cubic:recompute_roi=1",
                        "1.075,0.0,0.0,0.0,1.075,0.0,-164.32499999999982,-86.625,1.0",
                    ],
                },
            ),
        ],
    )
    def test_EffectsFileProcessor(self, kwargs, results):

        processor = AYONHieroEffectsFileProcessor(**kwargs)
        log.debug(f"Processor: {processor = }")

        log.debug(processor.color_operators)
        log.debug(processor.repo_operators)
        log.debug(processor.get_oiiotool_cmd())
        assert processor.filepath == results["expected_path"]
        assert processor.get_oiiotool_cmd() == results["expected_cmd"]
        # FileTransform
        assert (
            len(processor.color_operators) == results["expected_length"]
        )
