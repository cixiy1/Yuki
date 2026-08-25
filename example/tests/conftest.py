"""示例测试共享 fixture。"""

import pytest

from yuki_kernel.config import Settings
from yuki_kernel.core.memory import SessionStore
from yuki_kernel.providers import register_provider

from tests.fake_provider import FakeProvider

register_provider(
    "fake",
    lambda model, settings: FakeProvider(settings=settings, model=model),
)


@pytest.fixture
def settings(tmp_path):
    return Settings(
        provider="fake",
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
