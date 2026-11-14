"""Run tests against a disposable data directory, never the developer profile."""
import atexit
import os
import shutil
import tempfile

TEST_DATA_DIR = tempfile.mkdtemp(prefix="deckedge-tests-")
os.environ.setdefault("DECKEDGE_DATA_DIR", TEST_DATA_DIR)
atexit.register(shutil.rmtree, TEST_DATA_DIR, True)
