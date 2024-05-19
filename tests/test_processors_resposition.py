import logging

import pytest

from lablib.lib import SequenceInfo
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
                self.log.warning(f"{op = }")
            if "Mirror" in k:
                ops.append(repositions.Mirror2.from_node_data(v))
            if "Crop" in k:
                ops.append(repositions.Crop.from_node_data(v))

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

