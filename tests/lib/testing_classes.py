import logging
import pytest
from pathlib import Path
import shutil


class BaseTestClass:
    pass


class MainTestClass(BaseTestClass):
    STAGING_DIR = "test_results"
    KEEP_TEST_RESULTS = True

    _logger = {}

    @property
    def log(self) -> logging.Logger:
        if not self._logger.get(__name__):
            self._logger[__name__] = logging.getLogger(__name__)
            self._logger[__name__].setLevel(logging.DEBUG)

        return self._logger.get(__name__)

    @pytest.fixture(scope="session")
    def test_staging_dir(self):
        test_parent_dir = Path(__file__).resolve().parent.parent.parent
        staging_dir_path = Path(test_parent_dir, self.STAGING_DIR)
        staging_dir_path.mkdir(exist_ok=True)
        yield staging_dir_path

        if not self.KEEP_TEST_RESULTS:
            shutil.rmtree(
                staging_dir_path, ignore_errors=False)
