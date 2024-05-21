import pytest
import logging
from pathlib import Path

from lablib.processors import AYONHieroEffectsFileProcessor

log = logging.getLogger(__name__)


class TestAYONHieroEffectFileProcessor:

    @pytest.mark.parametrize(
        "path",
        [
            "resources/public/effectPlateMain/v000/"
            "BLD_010_0010_effectPlateMain_v000.json"
        ]
    )
    def test_EffectsFileProcessor(self, path):  # noqa: F811

        effect_processor = AYONHieroEffectsFileProcessor(
            Path(path)
        )
        log.debug(f"{effect_processor = }")
        effect_processor.load()

        log.debug(effect_processor.color_operators)
        assert effect_processor.filepath == Path(path)
        # 5 because CDLTransform is converted into CDLTransform and
        # FileTransform
        assert len(effect_processor.color_operators) == 5
