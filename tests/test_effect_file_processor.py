import logging
import pytest
from pathlib import Path

from fixtures import effect_processor  # noqa: F401


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


@pytest.mark.parametrize(
    "path",
    [
        "resources/public/effectPlateMain/v000/BLD_010_0010_effectPlateMain_v000.json"]
)
def test_EffectsFileProcessor(path, effect_processor):

    log.info(effect_processor.color_operators)
    assert effect_processor.filepath == Path(path)
    # 5 because CDLTransform is converted into CDLTransform and FileTransform
    assert len(effect_processor.color_operators) == 5
