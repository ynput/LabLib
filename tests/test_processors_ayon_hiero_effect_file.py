import pytest
from pathlib import Path


from tests.lib.testing_classes import MainTestClass


class TestAYONHieroEffectFileProcessor(MainTestClass):

    @pytest.mark.parametrize(
        "path",
        [
            "resources/public/effectPlateMain/v000/"
            "BLD_010_0010_effectPlateMain_v000.json"
        ]
    )
    def test_EffectsFileProcessor(self, path, effect_processor):  # noqa: F811

        self.log.debug(effect_processor.color_operators)
        assert effect_processor.filepath == Path(path)
        # 5 because CDLTransform is converted into CDLTransform and
        # FileTransform
        assert len(effect_processor.color_operators) == 5
