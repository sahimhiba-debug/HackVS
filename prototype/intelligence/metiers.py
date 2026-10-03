"""Taxonomie des MÉTIERS (data/taxonomie_metiers.yaml) — lue sans dépendance (format volontairement simple : une liste
de « - id: … » suivis de « clé: valeur »). Et les ZONES (Foire 2026 · D, F) : d'où vient un membre ou un invité."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

CHEMIN = Path(__file__).resolve().parent.parent / "data" / "taxonomie_metiers.yaml"
# zones : la seule information de lieu — un canton ou un pays, jamais une adresse
ZONES = ("Valais romand", "Haut-Valais", "Vaud", "Genève", "Haute-Savoie", "Ain", "autre")
VALAIS = frozenset({"Valais romand", "Haut-Valais"})


def lire(texte: str) -> list[dict[str, str]]:
    res: list[dict[str, str]] = []
    for ligne in texte.splitlines():
        brut = ligne.split("#", 1)[0].rstrip() if not ligne.lstrip().startswith("#") else ""
        if not brut.strip():
            continue
        if brut.startswith("- "):
            res.append({})
            brut = brut[2:]
        cle, _, val = brut.strip().partition(":")
        if not res or not _:
            raise ValueError(f"taxonomie des métiers : ligne illisible « {ligne} »")
        res[-1][cle.strip()] = val.strip()
    for m in res:
        if not {"id", "fr", "de"} <= set(m):
            raise ValueError(f"taxonomie des métiers : id, fr et de sont requis ({m})")
    return res


@lru_cache(maxsize=1)
def metiers() -> tuple[dict[str, str], ...]:
    return tuple(lire(CHEMIN.read_text(encoding="utf-8")))


def ids() -> set[str]:
    return {m["id"] for m in metiers()}


def par_role(role: str) -> str:
    """Le métier d'un rôle de patron (transport → transport, voix → interprete) ; à défaut, le rôle lui-même."""
    return next((m["id"] for m in metiers() if m.get("role") == role), role)


def libelle(mid: str, langue: str = "fr") -> str:
    return next((m[langue] for m in metiers() if m["id"] == mid), mid)
