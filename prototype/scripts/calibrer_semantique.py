"""Calibre la couche sémantique sur des données qui RESSEMBLENT à son usage réel.

La couche ne s'active que quand les règles ne reconnaissent aucune compétence : on la calibre donc sur
- positifs : paraphrases sans vocabulaire du Club (data/calibration_paraphrases.json) que les règles NE comprennent PAS ;
- négatifs : besoins hors catalogue (data/calibration_negatifs.json) que les règles ne comprennent pas non plus.

Deux méthodes comparées :
- « prototypes » : besoin ↔ vecteur moyen de chaque compétence (libellé + expressions) ; score et marge bruts ;
- « offres »     : besoin ↔ offres déclarées des membres ; score normalisé par requête (z) et marge en z.
Pour chacune, grille de seuils ; contrainte : fausses acceptations des négatifs ≤ FA_MAX et précision ≥ 95 %
sur les positifs acceptés ; objectif : couverture maximale. La méthode retenue est celle de meilleure couverture.
Coût asymétrique assumé : un mauvais contact coûte plus qu'une abstention.

Usage : python scripts/calibrer_semantique.py   → data/calibration_semantique.json
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import semantique  # noqa: E402
from app.models import Profil  # noqa: E402
from app.parser_rules import analyser  # noqa: E402
from app.taxonomy import DATA_DIR, charger_taxonomie  # noqa: E402

FA_MAX = 0.02
PRECISION_MIN = 0.95


def regles_echouent(texte: str, tax) -> bool:
    b = analyser(texte, tax)
    return not any(c.type == "expertise" for c in b.criteres) and not b.ambiguites


def grille(pos: np.ndarray, correct: np.ndarray, neg: np.ndarray, seuils_a, seuils_b, noms) -> dict | None:
    meilleur = None
    for a in seuils_a:
        for b in seuils_b:
            acc_p = (pos[:, 0] >= a) & (pos[:, 1] >= b)
            acc_n = (neg[:, 0] >= a) & (neg[:, 1] >= b)
            if not acc_p.any():
                continue
            fa, precision, couverture = acc_n.mean(), correct[acc_p].mean(), (acc_p & correct).mean()
            if fa <= FA_MAX and precision >= PRECISION_MIN and (meilleur is None or couverture > meilleur["couverture_positifs"]):
                meilleur = {noms[0]: float(a), noms[1]: float(b), "couverture_positifs": round(float(couverture), 3),
                            "precision_positifs_acceptes": round(float(precision), 3),
                            "fausses_acceptations_negatifs": round(float(fa), 3),
                            "acceptes_positifs": int(acc_p.sum()), "acceptes_negatifs": int(acc_n.sum())}
    return meilleur


def main() -> None:
    tax = charger_taxonomie()
    enc, protos = semantique.encodeur(), semantique.prototypes()
    para = json.loads((DATA_DIR / "calibration_paraphrases.json").read_text(encoding="utf-8"))["paraphrases"]
    negs = json.loads((DATA_DIR / "calibration_negatifs.json").read_text(encoding="utf-8"))["negatifs"]
    pos_txt = [(t, c) for c, ts in para.items() for t in ts]
    pos_utiles = [(t, c) for t, c in pos_txt if regles_echouent(t, tax)]
    neg_utiles = [t for t in negs if regles_echouent(t, tax)]
    vp = enc.encoder([f"query: {t}" for t, _ in pos_utiles])
    vn = enc.encoder([f"query: {t}" for t in neg_utiles])

    # méthode 1 : prototypes
    def proto_feat(v):
        cl = protos.scores(v)
        return cl[0][1], cl[0][1] - cl[1][1], cl[0][0]
    p1 = [proto_feat(v) for v in vp]
    n1 = np.array([proto_feat(v)[:2] for v in vn])
    ok1 = np.array([tax.meme_famille(c1, c) for (_, _, c1), (_, c) in zip(p1, pos_utiles)])
    m1 = grille(np.array([x[:2] for x in p1]), ok1, n1, np.round(np.arange(0.80, 0.90, 0.0025), 4), np.round(np.arange(0, 0.041, 0.0025), 4), ("tau", "delta"))

    # méthode 2 : offres des membres
    profils = [Profil(**p) for p in json.loads((DATA_DIR / "profils_demo.json").read_text(encoding="utf-8"))["profils"]]
    idx = semantique.index_offres(profils)

    def offre_feat(v):
        cl = idx.classer(v)
        z1, _, _, c1, _ = cl[0]
        autre = next((c for c in cl[1:] if not (c[3] and c1 and tax.meme_famille(c[3], c1))), None)
        return z1, z1 - (autre[0] if autre else 0.0), c1
    p2 = [offre_feat(v) for v in vp]
    n2 = np.array([offre_feat(v)[:2] for v in vn])
    ok2 = np.array([bool(c1) and tax.meme_famille(c1, c) for (_, _, c1), (_, c) in zip(p2, pos_utiles)])
    m2 = grille(np.array([x[:2] for x in p2]), ok2, n2, np.round(np.arange(1.5, 6.01, 0.05), 3), np.round(np.arange(0, 2.01, 0.05), 3), ("z", "marge_z"))

    # méthode 3 : options HYBRIDES montrées au membre (suggérer, jamais décider).
    # Constat : sur ces données, aucun score dense ne sépare un besoin hors catalogue d'un vrai besoin
    # (quantiles confondus) ; on ne calibre donc PAS une abstention, mais le NOMBRE d'options : le plus petit
    # écart Δ (en z-score) tel que la bonne compétence est montrée dans ≥ 90 % des positifs.
    RAPPEL_CIBLE = 0.90
    hp = [(semantique.suggerer(t, tax, methode="hybride")["classement"][:3], c) for t, c in pos_utiles]
    hn = [semantique.suggerer(t, tax, methode="hybride")["classement"][:3] for t in neg_utiles]

    def montre(top, d):
        return [x["concept"] for x in top if x["score"] >= top[0]["score"] - d]
    m3 = None
    for d in np.round(np.arange(0.0, 3.01, 0.05), 2):
        opts = [(montre(top, d), c) for top, c in hp]
        rappel = float(np.mean([any(tax.meme_famille(o, c) for o in os_) for os_, c in opts]))
        if rappel >= RAPPEL_CIBLE:
            hs = sum(sum(not tax.meme_famille(o, c) for o in os_) for os_, c in opts)
            m3 = {"delta_z": float(d), "rappel_cible": RAPPEL_CIBLE, "rappel_obtenu": round(rappel, 3),
                  "options_moyennes_positifs": round(float(np.mean([len(o) for o, _ in opts])), 2),
                  "options_hors_sujet_positifs": f"{hs}/{sum(len(o) for o, _ in opts)}",
                  "options_moyennes_negatifs": round(float(np.mean([len(montre(t, d)) for t in hn])), 2)}
            break
    m3 = m3 or {"delta_z": 3.0}

    cov = lambda m: m["couverture_positifs"] if m else -1
    methode = "prototypes" if cov(m1) >= cov(m2) else "offres"
    sortie = {
        "_description": "Seuils de la couche sémantique (scripts/calibrer_semantique.py). Calibration sur paraphrases que les règles ne comprennent pas.",
        "date": date.today().isoformat(), "modele": "multilingual-e5-large (ONNX, via fastembed)",
        "budget_fausses_acceptations": FA_MAX, "precision_minimale": PRECISION_MIN,
        "positifs": {"total": len(pos_txt), "utilises_regles_echouent": len(pos_utiles)},
        "negatifs": {"total": len(negs), "utilises_regles_echouent": len(neg_utiles)},
        "top1_correct_sans_seuil": {"prototypes": round(float(ok1.mean()), 3), "offres": round(float(ok2.mean()), 3)},
        "methode": methode,
        "seuils": (m1 or {"tau": 1.0, "delta": 1.0}) | {"hybride": m3},
        "seuils_offres": m2 or {"z": 99.0, "marge_z": 99.0},
    }
    (DATA_DIR / "calibration_semantique.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(sortie, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
