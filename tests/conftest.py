"""测试共享 fixture。"""

import shutil
from pathlib import Path

import pytest

from yuki_kernel.config import Settings
from yuki_kernel.core.session import SessionStore

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def settings(tmp_path):
    settings = Settings.load()
    settings.data_dir = tmp_path / "data"
    settings.packages_dir = tmp_path / "packages"
    settings.retry_max = 2
    settings.retry_base = 0.01
    settings.max_context_tokens = 100000
    settings.keep_recent_messages = 2
    return settings


@pytest.fixture
def store(settings):
    return SessionStore(settings.data_dir)


@pytest.fixture
def example_packages(tmp_path):
    dest = tmp_path / "packages"
    shutil.copytree(PROJECT_ROOT / "packages", dest)
    return dest
