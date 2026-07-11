"""Catalog pack loading and keyword search.

User packs in ``.risqlet/catalogs/`` shadow packaged packs with the same id,
mirroring the scoring-policy resolution rules. Search is a keyword/tag
convenience only — semantic risk-to-technique mapping is the calling agent's
job (framework-provider pattern).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
from ruamel.yaml import YAML

from risqlet.catalog.models import CatalogEntry, CatalogPack
from risqlet.store import Store

PACKS_DIR = Path(__file__).resolve().parent / "packs"
USER_CATALOGS_DIR = "catalogs"


class CatalogError(Exception):
    pass


def packaged_pack_ids() -> list[str]:
    return sorted(p.stem for p in PACKS_DIR.glob("*.yaml"))


def _user_dir(store: Store | None) -> Path | None:
    if store is None:
        return None
    return store.root / USER_CATALOGS_DIR


def load_pack(pack_id: str, store: Store | None = None) -> CatalogPack:
    candidates = []
    user_dir = _user_dir(store)
    if user_dir is not None:
        candidates.append(user_dir / f"{pack_id}.yaml")
    candidates.append(PACKS_DIR / f"{pack_id}.yaml")
    yaml = YAML(typ="safe")
    for path in candidates:
        if path.is_file():
            with path.open() as f:
                data = yaml.load(f)
            try:
                pack = CatalogPack.model_validate(data)
            except ValidationError as exc:
                raise CatalogError(f"{path}: invalid pack: {exc}") from exc
            if pack.id != pack_id:
                raise CatalogError(f"{path}: pack id {pack.id!r} does not match {pack_id!r}")
            return pack
    searched = ", ".join(str(c) for c in candidates)
    raise CatalogError(f"no catalog pack named {pack_id!r} (searched {searched})")


def load_available(store: Store | None = None) -> dict[str, CatalogPack]:
    """Load every resolvable pack: packaged, user-dir, and config-referenced."""
    ids = set(packaged_pack_ids())
    user_dir = _user_dir(store)
    if user_dir is not None and user_dir.is_dir():
        ids.update(p.stem for p in user_dir.glob("*.yaml"))
    if store is not None:
        try:
            ids.update(store.load_config_raw().get("catalogs") or [])
        except Exception:
            pass  # config problems are validate's job
    packs = {}
    for pack_id in sorted(ids):
        packs[pack_id] = load_pack(pack_id, store)  # raises CatalogError on bad packs
    return packs


def resolve_entry(entry_id: str, packs: dict[str, CatalogPack]) -> CatalogEntry | None:
    if "." not in entry_id:
        return None
    pack_id, slug = entry_id.split(".", 1)
    pack = packs.get(pack_id)
    return pack.get(slug) if pack else None


def search(packs: dict[str, CatalogPack], terms: list[str]) -> list[tuple[str, CatalogEntry, int]]:
    """Case-insensitive keyword match over name/summary/tags/slug, ranked by hits."""
    needles = [t.lower() for t in terms if t.strip()]
    results = []
    for pack in packs.values():
        for entry in pack.entries:
            haystack = " ".join(
                [entry.slug, entry.name, entry.summary, " ".join(entry.tags)]
            ).lower()
            hits = sum(1 for needle in needles if needle in haystack)
            if hits:
                results.append((f"{pack.id}.{entry.slug}", entry, hits))
    results.sort(key=lambda r: (-r[2], r[0]))
    return results
