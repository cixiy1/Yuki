"""示例测试共享 fixture。"""

# noinspection PyUnresolvedReferences
import pytest

# noinspection PyUnresolvedReferences
from yuki_kernel.config import Settings
# noinspection PyUnresolvedReferences
from yuki_kernel.core.memory import SessionStore
# noinspection PyUnresolvedReferences
from yuki_kernel.testing import make_weather_package, register_fake_provider

register_fake_provider()


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


@pytest.fixture
def weather_package(tmp_path):
    dest = tmp_path / "source"
    make_weather_package(dest)
    return dest
