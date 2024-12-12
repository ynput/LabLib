import json
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
                    "expected_length": 4,
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
                    "expected_length": 4,
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
            (
                {
                    "filepath": Path(
                        "resources/public/effectPlateMain/v001/"
                        "a01vfxd_sh020_effectPlateP01_v002.json"
                    )
                },
                {
                    "expected_path": Path(
                        "resources/public/effectPlateMain/v001/"
                        "a01vfxd_sh020_effectPlateP01_v002.json"
                    ),
                    "expected_length": 4,
                    "expected_cmd": [
                        "--colorconvert",
                        "scene_linear",
                        "Input - ARRI - V3 LogC (EI800) - Wide Gamut",
                        "--ociofiletransform",
                        f"{ABS_MODULE_PATH}/resources/public/effectPlateMain/v001/resources/sh020.cc",
                        "--ociofiletransform",
                        f"{ABS_MODULE_PATH}/resources/public/effectPlateMain/v001/resources/ARRI_LogC2Video.cube",
                        "--colorconvert",
                        "Output - Rec.709",
                        "scene_linear",
                        "--crop",
                        "0.0,0.0,1920.0,1080.0",
                        "--flip",
                        "--flop",
                    ],
                },
            ),
        ],
    )
    def test_EffectsFileProcessor(self, kwargs, results):

        processor = AYONHieroEffectsFileProcessor(**kwargs)
        log.debug(f"Processor: {processor = }")

        log.debug(processor.ocio_objects)
        log.debug(processor.repo_operators)
        log.debug(processor.get_oiiotool_cmd())
        assert processor.filepath == results["expected_path"]
        assert processor.get_oiiotool_cmd() == results["expected_cmd"]
        # FileTransform
        assert (
            len(processor.ocio_objects) == results["expected_length"]
        )

    def test_clear_operators(self):
        effect_processor = AYONHieroEffectsFileProcessor(
            Path("dummy.json")
        )
        effect_processor._color_ops = ["test"]
        effect_processor._repo_ops = ["test"]
        effect_processor.clear_operators()
        assert effect_processor.color_operators == []
        assert effect_processor.repo_operators == []

    def test_invalid_json(self, tmp_path):
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("{invalid json")
        processor = AYONHieroEffectsFileProcessor(invalid_json)
        with pytest.raises(json.JSONDecodeError):
            processor.load()

    def test_missing_file(self):
        processor = AYONHieroEffectsFileProcessor(Path("nonexistent.json"))
        with pytest.raises(FileNotFoundError):
            processor.load()

    def test_operation_sorting(self, tmp_path):
        test_data = {
            "op1": {"subTrackIndex": 2, "class": "ValidClass", "node": {}},
            "op2": {"subTrackIndex": 1, "class": "ValidClass", "node": {}}
        }
        test_file = tmp_path / "test.json"
        test_file.write_text(json.dumps(test_data))

        processor = AYONHieroEffectsFileProcessor(test_file)
        processor.load()

    def test_sanitize_file_path(self, tmp_path):
        test_file = tmp_path / "test.lut"
        test_file.touch()

        processor = AYONHieroEffectsFileProcessor(Path("dummy.json"))
        node_value = {"file": "test.lut"}  # Use same filename as test file
        all_relative_files = {test_file.name: test_file}

        processor._sanitize_file_path(node_value, all_relative_files)
        assert Path(node_value["file"]).exists()


    def test_empty_effects_file(self, tmp_path):
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("{}")

        processor = AYONHieroEffectsFileProcessor(empty_file)
        processor.load()
        assert processor.color_operators == []
        assert processor.repo_operators == []
