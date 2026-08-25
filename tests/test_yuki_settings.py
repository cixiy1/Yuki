"""Yuki 示例默认配置契约。"""

from yuki.settings import load_settings


def test_persona_preload_default():
    settings = load_settings()
    assert "yuki_persona" in settings.packages_preload
