import logging

import pytest

from lablib.operators import repositions
from lablib.processors import OIIORepositionProcessor
from tests.lib.testing_classes import MainTestClass

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class TestRepositionProcessor(MainTestClass):
    """Test reposition processor."""

    @pytest.mark.skip(reason="Not implemented")
    def test_OIIORepositionProcessor_fromEffectsfile(self):
        pass

    def test_OIIORepositionProcessor(self):
        proc = OIIORepositionProcessor()
        log.info(f"{proc = }")
        cmd = proc.get_oiiotool_cmd()
        assert cmd == []

    def test_OIIORepositionProcessor_withReformat(self):
        proc = OIIORepositionProcessor(
            dst_height=1080,
        )
        log.info(f"{proc = }")
        cmd = proc.get_oiiotool_cmd()
        assert cmd == ["--resize", "0x1080"]

    @pytest.mark.parametrize(
        "test_index, operators_data",
        (
            (i, operators)
            for i, operators in enumerate(
                [
                    {
                        "Transform": {
                            "scale": [0.5, 0.5],
                        },
                    },
                    {
                        "Mirror": {
                            "flip": True,
                            "flop": True,
                        },
                    },
                    {
                        "Crop": {
                            "box": [0, 0, 1920, 1080],
                        },
                    },
                ]
            )
        ),
    )
    def test_OIIORepositionProcessor_withOperators(self, test_index, operators_data):
        ops = []
        for k, v in operators_data.items():
            op = None
            if "Transform" in k:
                op = repositions.Transform.from_node_data(v)
            if "Mirror" in k:
                op = repositions.Mirror2.from_node_data(v)
            if "Crop" in k:
                op = repositions.Crop.from_node_data(v)

            if not op:
                self.log.warning(f"Skipping {k} with {v}...")
                continue
            ops.append(op)

        repo_processor = OIIORepositionProcessor(
            operators=ops,
        )
        repo_cmd = repo_processor.get_oiiotool_cmd()
        log.info(f"{repo_cmd = }")

        if test_index == 0:
            assert repo_cmd == [
                "--warp:filter=cubic:recompute_roi=1",
                "0.5,0.0,0.0,0.0,0.5,0.0,0.0,0.0,1.0",
            ]
        if test_index == 1:
            assert repo_cmd == ["--flop", "--flip"]
        if test_index == 2:
            assert repo_cmd == ["--crop", "0,0,1920,1080"]

    @pytest.mark.parametrize(  # TODO: this really should be a fixture
        "test_index, operators_data",
        (
            (i, operators)
            for i, operators in enumerate(
                [
                    {
                        "Transform": {
                            "rotate": 90,
                        },
                        "Reformat": {
                            "width": 1920,
                            "height": 1080,
                        },
                    },
                    {
                        "Mirror": {
                            "flip": False,
                            "flop": True,
                        },
                        "Reformat": {
                            "width": 1920,
                            "fit": "letterbox",  # width, height available
                        },
                    },
                    {
                        "Crop": {
                            "box": [0, 0, 1920, 1080],
                        },
                        "Reformat": {
                            "height": 1080,
                        },
                    },
                ]
            )
        ),
    )
    def test_OIIORepositionProcessor_withOperatorsAndReformat(
        self, test_index, operators_data
    ):  # NOTE: this treats reformat as a separate operator, testing if it fits better there
        ops = []
        reformat_op = None
        for k, v in operators_data.items():
            op = None
            if "Transform" in k:
                op = repositions.Transform.from_node_data(v)
            if "Mirror" in k:
                op = repositions.Mirror2.from_node_data(v)
            if "Crop" in k:
                op = repositions.Crop.from_node_data(v)
            if "Reformat" in k:
                reformat_op = v

            if not op:
                self.log.warning(f"Skipping {k} with {v}...")
                continue
            ops.append(op)

        repo_processor = OIIORepositionProcessor(
            operators=ops,
            dst_width=reformat_op.get("width", 0),
            dst_height=reformat_op.get("height", 0),
            fit=reformat_op.get("fit"),
        )
        proc_cmd = repo_processor.get_oiiotool_cmd()
        log.info(f"{proc_cmd = }")

        if test_index == 0:
            assert proc_cmd == [
                "--warp:filter=cubic:recompute_roi=1",
                "0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,1.0",
                "--resize",
                "1920x1080",
            ]
        if test_index == 1:
            assert proc_cmd == ["--flop", "--fit:fillmode=letterbox", "1920x0"]
        if test_index == 2:
            assert proc_cmd == ["--crop", "0,0,1920,1080", "--resize", "0x1080"]
