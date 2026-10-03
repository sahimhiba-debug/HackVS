"""BILAN DE PÉRIODE (Foire 2026 · G) : écrit docs/bilans/bilan-<période>.md depuis le journal.

    make bilan PERIODE=trimestre                      # ou demo, 7j ; BILAN_SCENE=1 rejoue la scène de démonstration
    cd prototype && python scripts/bilan.py trimestre [--scene] [--ia] [--sortie chemin.md]

Journal : celui de HACKVS_ESSAIS_DB s'il est défini (la machine de démonstration après la séance) ; sinon un monde de
démonstration neuf — avec --scene, la scène Foire 2026 y est jouée (Pauline dit oui puis le Club clôture « contact
établi », Markus « pas cette fois », un invité d'Annecy propose son aide et note son intention). --ia : récit proposé
par le modèle configuré (HACKVS_BILAN_IA=1 équivaut), vérifié par le code. Données FICTIVES."""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.taxonomy import charger_taxonomie  # noqa: E402
from intelligence import bilan, monde_demo as md, partenariats  # noqa: E402
from intelligence.demo import Demo  # noqa: E402

RACINE = Path(__file__).resolve().parents[2]


def scene(c) -> None:
    ask = lambda pid: next(a for _, a in c.asks_pour(pid))  # noqa: E731
    c.repondre_ask(md.MARKUS, ask(md.MARKUS), False, choix="pas cette fois")
    p = c.decouverte.emettre("stand")
    inv = c.decouverte.activer(p["jeton"])["invite"]
    c.decouverte.declarer(inv, "Exposant invité d'Annecy", "transport", "Haute-Savoie")
    c.decouverte.repondre(inv, ask(md.PAULINE), True)
    c.decouverte.rejoindre(inv)
    c.repondre_ask(md.PAULINE, ask(md.PAULINE), True, {"places": 14})
    ref = c.capacites.recus(md.PAULINE)[0]["reference"]
    partenariats.cloturer(c, ref, "contact établi", "Premier contact pris pour la délégation.")


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("periode", nargs="?", default="trimestre", choices=["demo", "7j", "trimestre"])
    a.add_argument("--scene", action="store_true")
    a.add_argument("--ia", action="store_true")
    a.add_argument("--sortie")
    a.add_argument("--csv", action="store_true", help="écrit aussi le CSV (mêmes chiffres) à côté du Markdown")
    x = a.parse_args()
    reprendre = bool(os.environ.get("HACKVS_ESSAIS_DB"))
    c = Demo(charger_taxonomie(), reprendre=reprendre).club
    origine = "journal " + os.environ["HACKVS_ESSAIS_DB"] if reprendre else "monde de démonstration neuf"
    if x.scene:
        scene(c)
        origine += ", scène Foire 2026 jouée par le script"
    texte = bilan.rediger(c, x.periode, ia=x.ia or os.environ.get("HACKVS_BILAN_IA") == "1", origine=origine)
    sortie = Path(x.sortie) if x.sortie else RACINE / "docs" / "bilans" / f"bilan-{x.periode}.md"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(texte, encoding="utf-8")
    print(sortie)
    if x.csv:
        csv_ = sortie.with_suffix(".csv")
        csv_.write_text(bilan.csv_texte(c, x.periode), encoding="utf-8")
        print(csv_)


if __name__ == "__main__":
    main()
