"""ANNÉE 1 · LOT 1 — Sauvegarde et restauration du journal, indépendantes du moteur (SQLite ↔ PostgreSQL).

Format : JSON Lines. Ligne 1 : l'en-tête (`format`, `version`, `nombre`, `empreinte`, `niveau_schema`). Puis un fait par
ligne, dans l'ordre du journal. L'empreinte est celle du journal (`Memoire.empreinte`, SHA-256 des identifiants de
contenu, eux-mêmes des empreintes du contenu) : un fait altéré, ajouté, retiré ou déplacé change l'empreinte.

Restaurer : seulement dans un journal VIDE ; tout le fichier est vérifié AVANT la moindre écriture ; puis tout est
écrit en une transaction, et l'empreinte est revérifiée. Tout ou rien."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .memoire import Evt, Memoire

FORMAT, VERSION = "clubpulse-journal", 1


class SauvegardeInvalide(ValueError):
    """Fichier altéré, incomplet, d'un autre format — ou cible non vide."""


def _empreinte(evts: list[Evt]) -> str:
    return hashlib.sha256("".join(e.id for e in evts).encode()).hexdigest()


def sauvegarder(m: Memoire, chemin: Path | str) -> dict:
    evts = m.evenements()
    entete = {"format": FORMAT, "version": VERSION, "nombre": len(evts), "empreinte": _empreinte(evts)}
    p = Path(chemin)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".part")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(entete, ensure_ascii=False) + "\n")
        for e in evts:
            f.write(e.model_dump_json(exclude={"seq"}) + "\n")
    tmp.replace(p)                                     # jamais une sauvegarde à moitié écrite sous le bon nom
    return entete


def lire(chemin: Path | str) -> tuple[dict, list[Evt]]:
    lignes = Path(chemin).read_text(encoding="utf-8").splitlines()
    if not lignes:
        raise SauvegardeInvalide("fichier vide")
    try:
        entete = json.loads(lignes[0])
        evts = [Evt.model_validate_json(x) for x in lignes[1:] if x.strip()]
    except ValueError as e:
        raise SauvegardeInvalide(f"fichier illisible : {e}") from None
    if entete.get("format") != FORMAT or entete.get("version") != VERSION:
        raise SauvegardeInvalide(f"format inconnu : {entete.get('format')} v{entete.get('version')}")
    if len(evts) != entete.get("nombre"):
        raise SauvegardeInvalide(f"incomplet : {len(evts)} faits lus, {entete.get('nombre')} annoncés")
    if _empreinte(evts) != entete.get("empreinte"):
        raise SauvegardeInvalide("empreinte différente : fichier altéré")
    return entete, evts


def restaurer(m: Memoire, chemin: Path | str) -> dict:
    entete, evts = lire(chemin)                        # tout vérifier AVANT d'écrire
    if m.evenements():
        raise SauvegardeInvalide("le journal cible n'est pas vide : restauration refusée (jamais de mélange)")
    with m.transaction():
        for e in evts:
            m.ajouter(e)
    if m.empreinte() != entete["empreinte"]:          # ne devrait jamais arriver : on le vérifie quand même
        raise SauvegardeInvalide("empreinte du journal restauré différente de la sauvegarde")
    return entete
