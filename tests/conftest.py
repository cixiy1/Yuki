"""测试共享 fixture。"""

import shutil
from pathlib import Path

import pytest

from yuki_kernel.config import Settings
from yuki_kernel.core.session import SessionStore

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def settings(tmp_path):
    return Settings(
        provider="ollama",
        model="fake",
        data_dir=tmp_path / "data",
        packages_dir=tmp_path / "packages",
        retry_max=2,
        retry_base=0.01,
        max_context_tokens=100000,
        keep_recent_messages=2,
    )


@pytest.fixture
def store(settings):
    assert settings.data_dir is not None
    return SessionStore(settings.data_dir)


@pytest.fixture
def example_packages(tmp_path):
    dest = tmp_path / "packages"
    shutil.copytree(PROJECT_ROOT / "packages", dest)
    return dest
