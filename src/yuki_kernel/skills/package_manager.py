"""外置工具包安装/卸载/列表与包来源抽象。"""

import json
import shutil
import tempfile
import zipfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from .external import MANIFEST_NAME, PackageError, load_package


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class PackageInfo:
    id: str
    version: str
    source: str
    installed_at: str


class PackageSource(ABC):
    @abstractmethod
    async def fetch(self, ref: str) -> tuple[Path, Callable[[], None]]:
        """返回包根目录和清理函数。"""


class LocalDirSource(PackageSource):
    async def fetch(self, ref: str) -> tuple[Path, Callable[[], None]]:
        path = Path(ref).expanduser().resolve()
        if not path.is_dir():
            raise PackageError(f"不是目录：{ref}")
        return path, lambda: None


class ZipSource(PackageSource):
    async def fetch(self, ref: str) -> tuple[Path, Callable[[], None]]:
        tmp = tempfile.TemporaryDirectory(prefix="yuki-pkg-")
        target = Path(tmp.name).resolve()
        with zipfile.ZipFile(ref) as archive:
            for member in archive.infolist():
                dest = (target / member.filename).resolve()
                if not dest.is_relative_to(target):
                    tmp.cleanup()
                    raise PackageError(f"zip 包含非法路径：{member.filename}")
                if member.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(archive.read(member))
        return target, tmp.cleanup


class MarketplaceSource(PackageSource):
    async def fetch(self, ref: str) -> tuple[Path, Callable[[], None]]:
        raise NotImplementedError("marketplace 尚未接入")


def _find_package_root(directory: Path) -> Path:
    if (directory / MANIFEST_NAME).is_file():
        return directory
    for child in directory.iterdir():
        if child.is_dir() and (child / MANIFEST_NAME).is_file():
            return child
    raise PackageError("包内找不到 manifest.json")


class PackageManager:
    def __init__(self, packages_dir: Path):
        self.packages_dir = packages_dir
        self.packages_dir.mkdir(parents=True, exist_ok=True)
        self.registry_path = packages_dir / ".registry.json"

    def _read_registry(self) -> dict[str, PackageInfo]:
        if not self.registry_path.exists():
            return {}
        data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        return {
            entry["id"]: PackageInfo(**entry)
            for entry in data.get("installed", [])
        }

    def _write_registry(self, entries: dict[str, PackageInfo]) -> None:
        payload = {
            "installed": [
                {
                    "id": info.id,
                    "version": info.version,
                    "source": info.source,
                    "installed_at": info.installed_at,
                }
                for info in sorted(entries.values(), key=lambda item: item.id)
            ]
        }
        tmp = self.registry_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.registry_path)

    async def install(self, source: PackageSource, ref: str) -> PackageInfo:
        src_dir, cleanup = await source.fetch(ref)
        try:
            root = _find_package_root(src_dir)
            package = load_package(root)
            package_id = package["id"]
            dest = self.packages_dir / package_id
            if dest.exists():
                raise PackageError(f"包已安装：{package_id}")
            shutil.copytree(root, dest)
        finally:
            cleanup()

        info = PackageInfo(
            id=package_id,
            version=package["version"],
            source=ref,
            installed_at=_now(),
        )
        entries = self._read_registry()
        entries[package_id] = info
        self._write_registry(entries)
        return info

    def remove(self, package_id: str) -> None:
        dest = self.packages_dir / package_id
        if not dest.exists():
            raise PackageError(f"包未安装：{package_id}")
        shutil.rmtree(dest)
        entries = self._read_registry()
        entries.pop(package_id, None)
        self._write_registry(entries)

    def list_installed(self) -> list[PackageInfo]:
        return sorted(self._read_registry().values(), key=lambda item: item.id)
