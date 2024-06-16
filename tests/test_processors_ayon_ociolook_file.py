import pytest
import logging
from pathlib import Path

from lablib.processors import AYONOCIOLookFileProcessor

log = logging.getLogger(__name__)


class TestAYONOCIOLookFileProcessor:
    @pytest.mark.parametrize(
        "path,length",
        [
            (
                (
                    "resources/public/ociolookMain/v005/"
                    "jp03_john_ociolookMain_v005.json"
                ),
                3,
            )
        ],
    )
    def test_EffectsFileProcessor(self, path, length):
        look_processor = AYONOCIOLookFileProcessor(Path(path))
        log.debug(f"{look_processor = }")
        look_processor.load()

        log.debug(look_processor.color_operators)
        assert look_processor.filepath == Path(path)
        # 5 because CDLTransform is converted into CDLTransform and
        # FileTransform
        assert len(look_processor.color_operators) == length
