"""阶段缓存：用输入文件哈希 + 配置指纹判断输出是否可复用。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

CACHE_VERSION = 8


class BuildCache:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": CACHE_VERSION, "stages": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"version": CACHE_VERSION, "stages": {}}
        if data.get("version") != CACHE_VERSION:
            return {"version": CACHE_VERSION, "stages": {}}
        data.setdefault("stages", {})
        return data

    @staticmethod
    def _digest(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def make_key(self, files: Iterable[Path], config: dict[str, Any]) -> str:
        payload: dict[str, Any] = {"files": {}, "config": config}
        for file_path in files:
            file_path = Path(file_path)
            payload["files"][str(file_path.resolve())] = (
                self._digest(file_path) if file_path.exists() else None
            )
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def fresh(self, stage: str, key: str, outputs: Iterable[Path]) -> bool:
        entry = self.data["stages"].get(stage)
        if not entry or entry.get("key") != key:
            return False
        return all(Path(output).exists() for output in outputs)

    def update(self, stage: str, key: str, outputs: Iterable[Path]) -> None:
        self.data["stages"][stage] = {
            "key": key,
            "outputs": [str(Path(output).resolve()) for output in outputs],
        }

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + ".tmp")
        temporary.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
