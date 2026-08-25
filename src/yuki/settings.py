"""Yuki 示例的默认配置：自动预加载人格包。"""

from yuki_kernel.config import Settings


def load_settings() -> Settings:
    settings = Settings.load()
    persona = settings.packages_dir / "yuki_persona"
    if persona.is_dir() and not settings.packages_preload:
        settings.packages_preload = ["yuki_persona"]
    return settings
