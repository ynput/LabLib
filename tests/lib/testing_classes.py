import logging
import pytest
from pathlib import Path

from lablib import AYONHieroEffectsFileProcessor


class BaseTestClass:
    pass


class MainTestClass(BaseTestClass):
    STAGING_DIR = "results"
    _logger = {}

    @property
    def log(self) -> logging.Logger:
        if not self._logger.get(__name__):
            self._logger[__name__] = logging.getLogger(__name__)
            self._logger[__name__].setLevel(logging.DEBUG)

        return self._logger.get(__name__)

    @pytest.fixture()
    def effect_processor(self):
        path = Path(
            "resources/public/effectPlateMain/v000/"
            "BLD_010_0010_effectPlateMain_v000.json"
        )
        effect_processor = AYONHieroEffectsFileProcessor(path)
        self.log.debug(f"{effect_processor = }")
        effect_processor.load()
        yield effect_processor
