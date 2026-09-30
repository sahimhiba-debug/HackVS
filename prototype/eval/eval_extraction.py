"""Évaluation du rôle EXTRACT TEL QU'IL EXISTE (option 1) sur le corpus FR/DE/suisse allemand annoté.

    python -m eval.eval_extraction --dev                  # vérifier le protocole sur DEV (modèle réel requis)
    python -m eval.eval_extraction --geler                # figer corpus + prompt + schéma après DEV
    python -m eval.eval_extraction --test                 # UNE passe TEST ; refusée si déjà faite ou si rien n'est gelé
    python -m eval.eval_extraction --dev --hors-ligne --sortie X   # vérifier la mécanique SANS modèle (jamais dans docs/)

Protocole (fixé avant toute exécution, avec le corpus : `eval/corpus_extraction/README.md`) :
- le corpus est celui du commit 61de546 : son SHA-256 est vérifié, sinon refus ;
- le rôle, son prompt et son schéma NE SONT PAS modifiés ; le modèle vient de l'environnement (`APERTUS_*`) ;
- chaque énoncé est un appel `RolesIA.extraire(texte, {"places": 12})` — le contexte d'une demande de pièce à
  attribut « places » (celui des patrons) — sans rejeu (aucun enregistrement réutilisé) ;
- les sorties BRUTES du modèle sont enregistrées par une enveloppe du fournisseur, côté banc (le rôle n'en sait rien) ;
- un appel échoué compte comme FALLBACK, jamais comme exclu.

Correspondance sortie → prédiction (fixée ici, AVANT la passe DEV) :
- `attributs` non vide → EXTRACTION, quantités prédites = `attributs` ;
- `attributs` vide (sortie acceptée vide, ou forme déterministe) → « RIEN D'EXTRAIT » : le produit montre alors le
  formulaire vide. Le rôle ne distingue PAS RIEN de FALLBACK : cette distinction est « non couverte par le schéma
  actuel » ; l'issue est donc mesurée en deux classes (extraction / rien d'extrait) et la matrice 3×2 est publiée.
- type, pièce, créneau, offre/retrait, plusieurs pièces : NON PRODUITS par le schéma actuel — rappel 0 %, affiché tel
  quel ; jamais un succès implicite.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Optional

from app.taxonomy import charger_taxonomie
from intelligence.ia import Apertus, Intelligence, NonConfigure
from intelligence.roles_ia import RolesIA

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[1]
CORPUS = ICI / "corpus_extraction" / "corpus.json"
GEL = ICI / "corpus_extraction" / "gel.json"
PROMPT = ICI.parent / "prompts" / "extraire_piece_v1.md"
SHA_CORPUS = "5069a8d4aefc9f527728bc7d69313166fe1aadb7e690754c816d092ae926937b"      # commit 61de546
CONTEXTE = {"places": 12}
NON_COUVERTS = ["type", "piece", "creneau.jour", "creneau.debut", "creneau.fin", "validite", "plusieurs_pieces"]


def sha(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


class Enregistreur:
    """Enveloppe du fournisseur, CÔTÉ BANC : chaque sortie brute et le schéma envoyé sont consignés tels quels."""

    def __init__(self, f):
        self.f, self.nom, self.modele = f, f.nom, f.modele
        self.bruts: list[dict] = []

    def completer(self, systeme_txt: str, message: str, schema: Optional[dict]) -> str:
        t0 = time.perf_counter()
        try:
            brut = self.f.completer(systeme_txt, message, schema)
            self.bruts.append({"brut": brut, "ms": round((time.perf_counter() - t0) * 1000, 1), "schema": schema})
            return brut
        except Exception as e:
            self.bruts.append({"erreur": f"{type(e).__name__}: {e}"[:300], "ms": round((time.perf_counter() - t0) * 1000, 1), "schema": schema})
            raise


def quantites(pieces: list[dict]) -> Counter:
    return Counter((k, v) for p in pieces for k, v in p["quantite"].items())


def evaluer(split: str, hors_ligne: bool) -> dict:
    if sha(CORPUS) != SHA_CORPUS:
        raise SystemExit("corpus modifié depuis le commit 61de546 : refus (le corpus et l'or sont gelés)")
    tax = charger_taxonomie()
    fournisseur = None
    if not hors_ligne:
        try:
            fournisseur = Enregistreur(Apertus())
        except NonConfigure as manque:
            raise SystemExit(f"modèle non configuré ({manque}) : passe réelle impossible — rien n'est inventé") from None
    ia = Intelligence(tax, fournisseur)
    roles = RolesIA(ia, tax)
    enonces = [e for e in json.loads(CORPUS.read_text(encoding="utf-8"))["enonces"] if e["split"] == split]
    lignes = []
    for e in enonces:
        n0 = len(fournisseur.bruts) if fournisseur else 0
        rep = roles.extraire(e["texte"], CONTEXTE)
        a = rep.appel
        pred = {k: v for k, v in rep.sortie["attributs"].items()}
        lignes.append({"id": e["id"], "langue": e["langue"], "registre": e["registre"], "couverture": e["couverture"],
                       "texte": e["texte"], "or": e["or"], "sortie": rep.sortie, "issue_appel": a.issue, "statut": a.statut,
                       "erreur": a.erreur, "rejets": a.rejets, "tentatives": a.tentatives, "latence_ms": a.latence_ms,
                       "bruts": fournisseur.bruts[n0:] if fournisseur else [],
                       "prediction": "EXTRACTION" if pred else "RIEN D'EXTRAIT", "quantites_predites": pred})
    return {"split": split, "hors_ligne": hors_ligne, "date": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "corpus_sha256": sha(CORPUS), "prompt": PROMPT.name, "prompt_sha256": sha(PROMPT), "contexte": CONTEXTE,
            "modele": fournisseur.modele if fournisseur else None, "hote": getattr(fournisseur.f, "base", None) if fournisseur else None,
            "schema_envoye": next((b["schema"] for x in lignes for b in x["bruts"]), None), "lignes": lignes}


def occurrences(lignes: list[dict], champ: str) -> int:
    """Combien de valeurs l'OR attend pour ce champ (une valeur nulle n'est pas attendue)."""
    if champ == "plusieurs_pieces":
        return sum(len(x["or"]["pieces"]) > 1 for x in lignes)
    pieces = [p for x in lignes for p in x["or"]["pieces"]]
    if champ.startswith("creneau."):
        return sum(1 for p in pieces if p["creneau"] and p["creneau"][champ.split(".")[1]] is not None)
    return sum(1 for p in pieces if p[champ] is not None)


def _pct(a: int, b: int) -> str:
    return f"{a}/{b} ({100 * a / b:.0f} %)" if b else "—"


def mesurer(r: dict) -> dict:
    L = r["lignes"]

    def bloc(sel: list[dict]) -> dict:
        extrait_or = [x for x in sel if x["or"]["issue"] == "EXTRACTION"]
        vides_or = [x for x in sel if x["or"]["issue"] != "EXTRACTION"]
        juste2 = sum((x["prediction"] == "EXTRACTION") == (x["or"]["issue"] == "EXTRACTION") for x in sel)
        tp = sum(sum((Counter(x["quantites_predites"].items()) & quantites(x["or"]["pieces"])).values()) for x in sel)
        n_pred = sum(len(x["quantites_predites"]) for x in sel)
        n_or = sum(sum(quantites(x["or"]["pieces"]).values()) for x in sel)
        # extraction exacte : impossible pour un énoncé EXTRACTION (champs non produits) ; exacte pour RIEN/FALLBACK si rien d'extrait
        exactes = sum(x["prediction"] == "RIEN D'EXTRAIT" for x in vides_or)
        return {"n": len(sel), "issue_2_classes": _pct(juste2, len(sel)),
                "matrice": {g: Counter(x["prediction"] for x in sel if x["or"]["issue"] == g) for g in ("EXTRACTION", "FALLBACK", "RIEN")},
                "taux_extraction": _pct(sum(x["prediction"] == "EXTRACTION" for x in sel), len(sel)),
                "taux_fallback_form": _pct(sum(x["issue_appel"] == "FALLBACK_FORM" for x in sel), len(sel)),
                "echecs_appel": _pct(sum(bool(x["erreur"]) for x in sel), len(sel)),
                "sorties_rejetees": _pct(sum(len(x["rejets"]) for x in sel), sum(x["tentatives"] for x in sel)),
                "rejet_final": _pct(sum(x["issue_appel"] == "FALLBACK_FORM" and len(x["rejets"]) == 2 for x in sel), len(sel)),
                "quantites_precision": _pct(tp, n_pred), "quantites_rappel": _pct(tp, n_or),
                "exacte": _pct(exactes, len(sel)), "exacte_detail": f"{exactes} énoncés « rien à extraire » justes ; "
                f"{len(extrait_or)} énoncés EXTRACTION ne peuvent pas être exacts (champs non couverts)"}
    lat = [x["latence_ms"] for x in L if x["issue_appel"] != "FALLBACK_FORM" or x["tentatives"]]
    q = sorted(lat)
    return {"total": bloc(L), "par_langue": {g: bloc([x for x in L if x["langue"] == g]) for g in ("fr", "de", "gsw")},
            "latence": {"n": len(q), "mediane_ms": statistics.median(q) if q else None, "p90_ms": q[int(0.9 * (len(q) - 1))] if q else None,
                        "max_ms": max(q) if q else None, "essais_par_enonce": _pct(sum(x["tentatives"] for x in L), len(L))},
            "non_couverts": {c: {"or": occurrences(L, c), "produits": 0, "rappel": "0 % — non couvert par le schéma actuel"}
                             for c in NON_COUVERTS}}


def rapport(r: dict, m: dict) -> str:
    t = m["total"]
    o = [f"# Évaluation EXTRACT — split {r['split'].upper()}{' (HORS LIGNE, sans modèle)' if r['hors_ligne'] else ''}", "",
         f"- Date : {r['date']} · modèle : `{r['modele']}` · hôte : `{r['hote']}`",
         f"- Corpus : `eval/corpus_extraction/corpus.json` sha256 `{r['corpus_sha256']}` (commit 61de546)",
         f"- Prompt : `prompts/{r['prompt']}` sha256 `{r['prompt_sha256']}` · contexte `{json.dumps(r['contexte'])}` · "
         f"schéma envoyé : voir le fichier brut", "- Rôle, prompt, schéma et moteur : NON modifiés (option 1).", "",
         "## Résultats", "", "| Mesure | Total | FR | DE | GSW |", "|---|---|---|---|---|"]
    for k, lib in (("issue_2_classes", "issue juste (extraction / rien d'extrait)"), ("taux_extraction", "taux EXTRACTION prédit"),
                   ("taux_fallback_form", "taux FALLBACK_FORM (forme déterministe)"), ("echecs_appel", "appels échoués (→ FALLBACK)"),
                   ("sorties_rejetees", "sorties du modèle rejetées par le validateur / essais"), ("rejet_final", "rejetées deux fois (→ FALLBACK)"),
                   ("quantites_precision", "quantités : précision"), ("quantites_rappel", "quantités : rappel"), ("exacte", "extraction exacte")):
        o.append(f"| {lib} | {t[k]} | " + " | ".join(m["par_langue"][g][k] for g in ("fr", "de", "gsw")) + " |")
    o += ["", f"Extraction exacte : {t['exacte_detail']}.", "", "Matrice or × prédit (total) :", "",
          "| or \\ prédit | EXTRACTION | RIEN D'EXTRAIT |", "|---|---|---|"]
    for g, c in t["matrice"].items():
        rien = c.get("RIEN D'EXTRAIT", 0)
        o.append(f"| {g} | {c.get('EXTRACTION', 0)} | {rien} |")
    lat = m["latence"]
    sans_q = sum(1 for x in r["lignes"] if x["or"]["issue"] == "EXTRACTION" and not quantites(x["or"]["pieces"]))
    o += ["", "RIEN et FALLBACK ne sont PAS distingués par le rôle : « non couvert par le schéma actuel ».",
          f"{sans_q} énoncé(s) EXTRACTION de l'or ne portent AUCUNE quantité (compétence, retrait, lieu sans taille) : le rôle "
          "actuel, qui ne produit que des quantités, ne peut pas les extraire — limite du schéma, pas du modèle.", "",
          f"Latence par énoncé (appels au modèle) : médiane {lat['mediane_ms']} ms · p90 {lat['p90_ms']} ms · max {lat['max_ms']} ms "
          f"(n = {lat['n']}) ; essais au modèle : {lat['essais_par_enonce']}.", "",
          "## Champs NON couverts par le schéma actuel (rappel 0 %, jamais un succès implicite)", "",
          "| Champ | Occurrences dans l'or | Produits | Rappel |", "|---|---|---|---|"]
    for c, v in m["non_couverts"].items():
        o.append(f"| {c} | {v['or']} | {v['produits']} | {v['rappel']} |")
    o += ["", "## Échecs, verbatim", ""]
    for x in r["lignes"]:
        bon_issue = (x["prediction"] == "EXTRACTION") == (x["or"]["issue"] == "EXTRACTION")
        bon_q = Counter(x["quantites_predites"].items()) == quantites(x["or"]["pieces"])
        if not (bon_issue and bon_q):
            o += [f"- **{x['id']}** ({x['langue']}, {x['registre']}) « {x['texte']} »",
                  f"  - or : {x['or']['issue']} ; quantités {dict(quantites(x['or']['pieces']))}",
                  f"  - montré : {x['prediction']} ; quantités {x['quantites_predites']} ; statut {x['issue_appel']}"
                  + (f" ; erreur {x['erreur']}" if x["erreur"] else "") + (f" ; rejets {x['rejets']}" if x["rejets"] else "")]
    return "\n".join(o) + "\n"


def main(argv: list[str]) -> int:
    if "--geler" in argv:
        GEL.write_text(json.dumps({"corpus_sha256": sha(CORPUS), "prompt": PROMPT.name, "prompt_sha256": sha(PROMPT),
                                   "roles_ia_sha256": sha(ICI.parent / "intelligence" / "roles_ia.py"),
                                   "gele_le": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}, indent=1) + "\n")
        print(f"gelé : {GEL}")
        return 0
    split = "test" if "--test" in argv else "dev"
    hors_ligne = "--hors-ligne" in argv
    sortie = Path(argv[argv.index("--sortie") + 1]) if "--sortie" in argv else RACINE / "docs" / "audit"
    if hors_ligne and sortie.resolve() == (RACINE / "docs" / "audit").resolve():
        raise SystemExit("une passe hors ligne ne s'écrit jamais dans docs/audit (elle ne mesure pas le modèle)")
    if split == "test":
        if not GEL.exists():
            raise SystemExit("TEST refusé : rien n'est gelé (python -m eval.eval_extraction --geler après DEV)")
        gel = json.loads(GEL.read_text())
        if (gel["corpus_sha256"], gel["prompt_sha256"], gel["roles_ia_sha256"]) != (sha(CORPUS), sha(PROMPT), sha(ICI.parent / "intelligence" / "roles_ia.py")):
            raise SystemExit("TEST refusé : corpus, prompt ou rôle modifiés depuis le gel")
        if (sortie / "extraction_test.md").exists() and not hors_ligne:
            raise SystemExit("TEST refusé : la passe unique a déjà eu lieu (docs/audit/extraction_test.md)")
    r = evaluer(split, hors_ligne)
    m = mesurer(r)
    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / f"extraction_{split}_brut.json").write_text(json.dumps(r | {"mesures": m}, ensure_ascii=False, indent=1, default=dict) + "\n", encoding="utf-8")
    (sortie / f"extraction_{split}.md").write_text(rapport(r, m), encoding="utf-8")
    print(rapport(r, m)[:1500])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
