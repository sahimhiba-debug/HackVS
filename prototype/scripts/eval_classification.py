"""HARNAIS DE CLASSIFICATION (Foire 2026 · H) : chaque phrase → un métier de la taxonomie, ou l'abstention.

    python scripts/eval_classification.py --fournisseur apertus|openai|claude|factice [--phrases data/eval/phrases_foire.jsonl]

- Phrases : celles du QR de la Foire (`ingest_tally.py`) si le fichier existe ; sinon les 26 cas existants
  (`eval/cas_comprendre_action.json`, source « cas-26 »).
- Fournisseurs du banc multi-fournisseurs (`intelligence/ia.py`) ; `factice` = sans réseau, pour vérifier la chaîne.
  CONSENTEMENT : les phrases de la Foire ne passent QUE par Apertus (ou le factice) — refus explicite sinon.
- Sortie contrainte (JSON, schéma), VALIDÉE par le code, abstention permise ; rapport d'AGRÉGATS (langues,
  distribution, abstention, rejets) dans `eval/resultats_classification/<source>-<fournisseur>.md` ; feuille
  d'annotation CSV HORS DÉPÔT (`var/annotation/`) avec `metier_humain` et `domaine` (club | hors_club) à remplir.
- Aucune exactitude revendiquée : elle se mesurera APRÈS l'annotation humaine."""
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROTO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROTO))

from eval import classification_metiers as cm  # noqa: E402

PHRASES_DEFAUT = PROTO / "data" / "eval" / "phrases_foire.jsonl"
CAS = PROTO / "eval" / "cas_comprendre_action.json"


class Factice:
    """Sans réseau : propose un métier par mots-clés, s'abstient sinon (vérifie la chaîne, ne mesure aucun modèle)."""
    modele = "factice (mots-clés, aucun réseau)"
    CLES = {"transport": ("minibus", "transport", "chauffeur"), "interprete": ("allemand", "dolmetsch", "traduction", "interprète"),
            "salle": ("salle", "lieu", "raum"), "traiteur": ("traiteur", "repas", "apéro", "catering"), "informatique": ("cyber", "site", "informat")}

    def completer(self, systeme, message, schema):
        m = message.lower()
        mid = next((k for k, mots in self.CLES.items() if any(x in m for x in mots)), None)
        return json.dumps({"metier": mid, "abstention": mid is None})


def charger(chemin: Path) -> tuple[list[dict], str]:
    if chemin.is_file():
        phrases = [json.loads(x) for x in chemin.read_text(encoding="utf-8").splitlines() if x.strip()]
        sources = {p.get("source") for p in phrases}
        return phrases, cm.SOURCE_FOIRE if cm.SOURCE_FOIRE in sources else "phrases"
    cas = json.loads(CAS.read_text(encoding="utf-8"))["cas"]
    return [{"texte": c["texte"], "langue": cm.detecter_langue(c["texte"]), "source": "cas-26", "id": c["id"]} for c in cas], "cas-26"


def fournisseur(nom: str):
    if nom == "factice":
        return Factice()
    from intelligence.ia import FOURNISSEURS
    return FOURNISSEURS[nom]()


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--fournisseur", required=True, choices=["apertus", "openai", "claude", "factice"])
    a.add_argument("--phrases", default=str(PHRASES_DEFAUT))
    a.add_argument("--rapport")
    a.add_argument("--feuille")
    x = a.parse_args()
    phrases, source = charger(Path(x.phrases))
    for p in phrases:                                               # AVANT tout appel : le consentement d'abord
        cm.verifier_fournisseur(p.get("source", source), x.fournisseur)
    f = fournisseur(x.fournisseur)
    resultats = [cm.classer(f, x.fournisseur, p.get("source", source), p["texte"]) for p in phrases]
    quand = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rapport = Path(x.rapport) if x.rapport else PROTO / "eval" / "resultats_classification" / f"{source}-{x.fournisseur}.md"
    rapport.parent.mkdir(parents=True, exist_ok=True)
    rapport.write_text(cm.rapport(phrases, resultats, source, x.fournisseur, getattr(f, "modele", "?"), quand), encoding="utf-8")
    feuille = Path(x.feuille) if x.feuille else PROTO / "var" / "annotation" / f"{source}-{x.fournisseur}.csv"
    feuille.parent.mkdir(parents=True, exist_ok=True)
    with feuille.open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h)
        w.writerow(["n", "texte", "langue_detectee", "metier_propose", "abstention", "rejet", "metier_humain", "domaine"])
        for i, (p, r) in enumerate(zip(phrases, resultats, strict=True), 1):
            s = r["sortie"] or {}
            w.writerow([i, p["texte"], p["langue"], s.get("metier") or "", s.get("abstention", ""), r["rejet"] or "", "", ""])
    print(f"rapport (agrégats) : {rapport}")
    print(f"feuille d'annotation (hors dépôt) : {feuille} — remplir metier_humain et domaine (club | hors_club)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PermissionError as e:
        print(f"REFUS — {e}", file=sys.stderr)
        sys.exit(3)
