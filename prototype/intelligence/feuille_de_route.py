"""FEUILLE DE ROUTE VIVANTE (Foire 2026 · §7) — source unique : docs/roadmap/etat.yaml.

Trois statuts, VÉRIFIÉS par le code :
- « construit » : du code et des tests — chaque fichier de test cité doit exister ; `ecran` = lien dans le monde « visite » ;
- « validé sur le terrain » : seulement avec une PREUVE RÉELLE (`preuve_terrain`) ;
- « prévu » : ce qui exige des membres réels, des partenaires, un financement, un juriste ou du temps.
Le tableau de docs/roadmap/README.md est RÉGÉNÉRÉ depuis ce fichier (`make feuille-de-route`) ; un test vérifie qu'il
est à jour."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from .metiers import lire

RACINE = Path(__file__).resolve().parents[2]
ETAT = RACINE / "docs" / "roadmap" / "etat.yaml"
README = RACINE / "docs" / "roadmap" / "README.md"
TESTS = RACINE / "prototype" / "tests"
STATUTS = {"construit": ("✅", "Construit", "Gebaut", "Built"), "valide": ("🟢", "Validé sur le terrain", "Im Feld bestätigt",
           "Validated in the field"), "prevu": ("⬜", "Prévu", "Geplant", "Planned")}
DEBUT, FIN = "<!-- etat:debut (généré depuis etat.yaml — ne pas éditer à la main) -->", "<!-- etat:fin -->"


def charger(chemin: Path = ETAT) -> list[dict]:
    entrees = lire(chemin.read_text(encoding="utf-8"))
    for e in entrees:
        s = e.get("statut")
        if s not in STATUTS or not e.get("en"):
            raise ValueError(f"etat.yaml : statut ou titre anglais manquant ({e['id']})")
        if s == "construit":
            fichiers = [t.strip() for t in e.get("tests", "").split(",") if t.strip()]
            if not fichiers or not e.get("ecran"):
                raise ValueError(f"etat.yaml : « construit » exige des tests et un écran ({e['id']})")
            manquants = [f for f in fichiers if not (TESTS / f).exists()]
            if manquants:
                raise ValueError(f"etat.yaml : tests introuvables pour {e['id']} : {manquants}")
        if s == "valide" and not e.get("preuve_terrain"):
            raise ValueError(f"etat.yaml : « validé sur le terrain » exige une preuve réelle ({e['id']})")
    return entrees


def tableau(entrees: list[dict], jour: date) -> str:
    L = [DEBUT, f"*État au {jour.strftime('%d.%m.%Y')}, généré depuis [etat.yaml](etat.yaml).* ✅ construit (code + tests) · "
         "🟢 validé sur le terrain (preuve réelle) · ⬜ prévu", "", "| Chantier | Statut | Preuve |", "|---|---|---|"]
    for e in entrees:
        preuve = e.get("preuve_terrain") or e.get("tests") or e.get("note") or "—"
        L.append(f"| {e['fr']} | {STATUTS[e['statut']][0]} {STATUTS[e['statut']][1]} | {preuve} |")
    return "\n".join(L + [FIN])


def regenerer_readme(jour: date) -> bool:
    texte = README.read_text(encoding="utf-8")
    avant, _, reste = texte.partition(DEBUT)
    _, _, apres = reste.partition(FIN)
    nouveau = avant + tableau(charger(), jour) + apres
    change = nouveau != texte
    README.write_text(nouveau, encoding="utf-8")
    return change


def pour_la_page(base_visite: str | None) -> list[dict]:
    return [{"id": e["id"], "statut": e["statut"], "libelles": {lg: STATUTS[e["statut"]][i] for i, lg in enumerate(("fr", "de", "en"), 1)},
             "titre": {"fr": e["fr"], "de": e["de"], "en": e["en"]}, "note": e.get("note"), "preuve_terrain": e.get("preuve_terrain"),
             "lien": (base_visite.rstrip("/") + e["ecran"]) if base_visite and e["statut"] == "construit" and e.get("ecran") else None}
            for e in charger()]
