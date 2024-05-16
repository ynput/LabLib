import logging
import pytest
from pathlib import Path

from lablib import AYONHieroEffectsFileProcessor

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

# TODO: convert to fixture for OCIOConfigFileProcessor
@pytest.mark.parametrize(
    "path",
    [
        "resources/public/effectPlateMain/v000/"
        "BLD_010_0010_effectPlateMain_v000.json"
    ],
)
def test_EffectsFileProcessor(path: str):
    path = Path(path)
    effect_processor = AYONHieroEffectsFileProcessor(path)
    effect_processor.load()

    log.info(effect_processor.color_operators)
    assert effect_processor.filepath == path
    # 5 because CDLTransform is converted into CDLTransform and FileTransform
    assert len(effect_processor.color_operators) == 5
