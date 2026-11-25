"""Load, validate and cache interview packs (built-in YAML files + packs uploaded by admins)."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models import Pack as PackRow
from .schema import Pack

BUILTIN_DIR = Path(__file__).parent / "builtin"
MAX_PACK_BYTES = 200_000


class PackError(ValueError):
    pass


def parse_pack(text: str) -> Pack:
    if len(text.encode()) > MAX_PACK_BYTES:
        raise PackError("pack file is larger than 200 KB")
    try:
        data = yaml.safe_load(text)  # safe_load: no arbitrary Python objects
    except yaml.YAMLError as e:
        raise PackError(f"invalid YAML: {e}") from e
    if not isinstance(data, dict):
        raise PackError("pack must be a YAML mapping")
    try:
        return Pack.model_validate(data)
    except ValidationError as e:
        msgs = [f"{'.'.join(str(p) for p in err['loc']) or 'pack'}: {err['msg']}" for err in e.errors()]
        raise PackError("; ".join(msgs)) from e


def builtin_files() -> list[Path]:
    files = sorted(BUILTIN_DIR.glob("*.yaml"))
    extra = get_settings().packs_dir
    if extra and Path(extra).is_dir():
        files += sorted(Path(extra).glob("*.yaml"))
    return files


async def sync_builtin_packs(db: AsyncSession) -> int:
    """Insert or update built-in packs at startup. Returns how many changed."""
    changed = 0
    for path in builtin_files():
        text = path.read_text(encoding="utf-8")
        pack = parse_pack(text)
        row = await db.scalar(select(PackRow).where(PackRow.slug == pack.id))
        if row is None:
            db.add(PackRow(slug=pack.id, name=pack.name, version=pack.version, source_yaml=text, builtin=True))
            changed += 1
        elif row.builtin and row.source_yaml != text:
            row.name, row.version, row.source_yaml = pack.name, pack.version, text
            changed += 1
    await db.commit()
    _cache.clear()
    return changed


_cache: dict[tuple[str, int], Pack] = {}


async def get_pack(db: AsyncSession, slug: str) -> Pack | None:
    row = await db.scalar(select(PackRow).where(PackRow.slug == slug, PackRow.active.is_(True)))
    if row is None:
        return None
    key = (row.slug, row.version)
    if key not in _cache:
        _cache[key] = parse_pack(row.source_yaml)
    return _cache[key]
