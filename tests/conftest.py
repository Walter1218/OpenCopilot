"""共享 fixtures"""
import os
import pytest
import tempfile



@pytest.fixture
def temp_dir():
    """临时目录 fixture"""
    tmp = tempfile.mkdtemp(prefix="opencopilot_test_")
    yield tmp
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
