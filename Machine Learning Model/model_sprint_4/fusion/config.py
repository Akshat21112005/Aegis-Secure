from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


_FILE_ENV = _parse_env_file(ENV_PATH)


def _get(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, _FILE_ENV.get(name, default))


@dataclass(frozen=True)
class FusionConfig:
    mode: str
    model_name: str
    semantic_url: str
    infrastructure_url: str
    runtime_url: str
    visual_url: str
    semantic_enabled: bool
    infrastructure_enabled: bool
    runtime_enabled: bool
    visual_enabled: bool
    specialist_timeout: int
    specialist_retries: int
    http_timeout: int
    model_dir: Path
    tokenizer_dir: Path
    adapter_dir: Path
    prompt_path: Path

    @classmethod
    def load(cls, *, env_path: Path | None = None) -> FusionConfig:
        env_file = env_path or ENV_PATH
        file_env = _parse_env_file(env_file)
        get = lambda key, default=None: os.getenv(key, file_env.get(key, _FILE_ENV.get(key, default)))

        base = BASE_DIR
        return cls(
            mode=str(get("FUSION_MODE", "local")).lower(),
            model_name=str(get("FUSION_MODEL_NAME", "Qwen/Qwen2.5-1.5B-Instruct")),
            semantic_url=str(get("SEMANTIC_URL", "") or ""),
            infrastructure_url=str(get("INFRASTRUCTURE_URL", "") or ""),
            runtime_url=str(get("RUNTIME_URL", "") or ""),
            visual_url=str(get("VISUAL_URL", "") or ""),
            semantic_enabled=_as_bool(get("SEMANTIC_ENABLED"), True),
            infrastructure_enabled=_as_bool(get("INFRASTRUCTURE_ENABLED"), True),
            runtime_enabled=_as_bool(get("RUNTIME_ENABLED"), True),
            visual_enabled=_as_bool(get("VISUAL_ENABLED"), False),
            specialist_timeout=_as_int(get("SPECIALIST_TIMEOUT"), 120),
            specialist_retries=_as_int(get("SPECIALIST_RETRIES"), 1),
            http_timeout=_as_int(get("HTTP_TIMEOUT"), 120),
            model_dir=base / str(get("FUSION_MODEL_DIR", "model/base")),
            tokenizer_dir=base / str(get("FUSION_TOKENIZER_DIR", "model/tokenizer")),
            adapter_dir=base / str(get("FUSION_ADAPTER_DIR", "model/adapter")),
            prompt_path=base / "prompt.md",
        )


def load_config() -> FusionConfig:
    """Read and validate Fusion deployment configuration."""

    return FusionConfig.load()
