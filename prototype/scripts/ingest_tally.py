"""PIPELINE TALLY (Foire 2026 · H) : CSV du formulaire Tally (QR de la Foire) → data/eval/phrases_foire.jsonl.

    python scripts/ingest_tally.py [--csv ../docs/data/tally_phrases.csv] [--sortie data/eval/phrases_foire.jsonl]

- Colonnes détectées par leur TITRE : la page choisie (« langue / Sprache / language »), les trois colonnes de message
  (« coup de main / Hilfe / hand »), la date (« submitted / soumis / date »). Les trois messages sont fusionnés.
- Langue : DÉTECTÉE sur le texte (une réponse anglaise peut passer par la page française) ; la page reste en
  `langue_page`, pour diagnostic.
- Doublons retirés (texte normalisé) ; toute phrase contenant un e-mail ou un téléphone est ÉCARTÉE, et la sortie est
  vérifiée (assert) sans aucun de ces motifs.
- Sans CSV : le dit et sort proprement (le pipeline tourne avec ou sans le fichier).
- La sortie est HORS DÉPÔT (`data/eval/` est ignoré par git) : les phrases sont des données de répondants. La console
  n'affiche que des AGRÉGATS — jamais une phrase."""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

PROTO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROTO))

from eval import classification_metiers as cm  # noqa: E402

CSV_DEFAUT = PROTO.parent / "docs" / "data" / "tally_phrases.csv"
SORTIE_DEFAUT = PROTO / "data" / "eval" / "phrases_foire.jsonl"


def colonnes(entetes: list[str]) -> tuple[list[str], str | None, str | None]:
    bas = {h: h.lower() for h in entetes}
    messages = [h for h, b in bas.items() if any(m in b for m in ("coup de main", "hilfe", "hand"))]
    page = next((h for h, b in bas.items() if any(m in b for m in ("langue", "sprache", "language")) and h not in messages), None)
    quand = next((h for h, b in bas.items() if any(m in b for m in ("submitted", "soumis", "date"))), None)
    return messages, page, quand


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--csv", default=str(CSV_DEFAUT))
    a.add_argument("--sortie", default=str(SORTIE_DEFAUT))
    x = a.parse_args()
    source = Path(x.csv)
    if not source.is_file():
        print(f"CSV Tally absent ({source}) : rien à ingérer — l'évaluation tournera sur les 26 cas existants.")
        return 0
    with source.open(encoding="utf-8-sig", newline="") as f:
        lecteur = csv.DictReader(f)
        messages, page, quand = colonnes(lecteur.fieldnames or [])
        if not messages:
            print("aucune colonne de message reconnue (« coup de main / Hilfe / hand ») : rien à ingérer", file=sys.stderr)
            return 2
        vues, phrases, compte = set(), [], Counter()
        for ligne in lecteur:
            texte = " ".join(v.strip() for v in (ligne.get(m) or "" for m in messages) if v and v.strip())
            if not texte:
                compte["vides"] += 1
                continue
            if cm.contient_contact(texte):
                compte["écartées (contact)"] += 1
                continue
            cle = cm.normaliser(texte)
            if cle in vues:
                compte["doublons"] += 1
                continue
            vues.add(cle)
            phrases.append({"texte": texte, "langue": cm.detecter_langue(texte), "langue_page": (ligne.get(page) or "").strip() if page else None,
                            "date": (ligne.get(quand) or "")[:10] if quand else None, "source": cm.SOURCE_FOIRE})
    assert not any(cm.contient_contact(p["texte"]) for p in phrases), "un motif d'e-mail ou de téléphone a passé le filtre"
    sortie = Path(x.sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in phrases), encoding="utf-8")
    langues = Counter(p["langue"] for p in phrases)
    print(f"{len(phrases)} phrase(s) gardée(s) → {sortie} (hors dépôt)")
    print("langues détectées : " + ", ".join(f"{k} {v}" for k, v in sorted(langues.items())))
    print("retirées : " + ", ".join(f"{k} {compte[k]}" for k in ("vides", "doublons", "écartées (contact)")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
