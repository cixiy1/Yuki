"""测试共享 fixture。"""

import json
from pathlib import Path

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


@pytest.fixture
def weather_package(tmp_path):
    dest = tmp_path / "packages"
    weather = dest / "weather"
    weather.mkdir(parents=True)
    (weather / "manifest.json").write_text(
        json.dumps(
            {
                "id": "weather",
                "name": "天气工具包",
                "version": "1.0.0",
                "description": "查询指定城市当前气温",
                "tools": [
                    {
                        "name": "weather_now",
                        "description": "查询指定城市当前气温",
                        "parameters": {
                            "type": "object",
                            "required": ["city"],
                            "properties": {
                                "city": {"type": "string", "description": "城市英文名"}
                            },
                        },
                        "entry": {
                            "type": "python",
                            "module": "tool.py",
                            "handler": "weather_now",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (weather / "tool.py").write_text(
        "def weather_now(city):\n    return '22°C'\n",
        encoding="utf-8",
    )
    return dest
