import pytest
from pathlib import Path
import shutil

STAGING_DIR = "test_results"
KEEP_TEST_RESULTS = False


@pytest.fixture(scope="session")
def test_staging_dir():
    test_parent_dir = Path(__file__).resolve().parent.parent.parent
    staging_dir_path = Path(test_parent_dir, STAGING_DIR)
    staging_dir_path.mkdir(exist_ok=True)
    print(f"Created staging directory: {staging_dir_path.as_posix()}")
    yield staging_dir_path

    if not KEEP_TEST_RESULTS:
        shutil.rmtree(staging_dir_path, ignore_errors=False)
