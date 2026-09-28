"""Calibre la couche sémantique : choisit (τ, δ) sur un jeu de calibration indépendant des évaluations.

Positifs : chaque expression « de base » de la taxonomie, formulée comme un besoin (« Je cherche … »), comparée aux
prototypes de concepts dont on RETIRE cette expression (leave-one-out, sinon la tâche serait triviale).
Négatifs : data/calibration_negatifs.json (besoins hors catalogue, dont des pièges proches).
Règle : accepter le concept n°1 si score ≥ τ et marge (n°1 − n°2) ≥ δ.
Critère : maximiser les positifs acceptés ET corrects, sous contrainte :
  - fausses acceptations sur les négatifs ≤ 2 % (coût asymétrique : un mauvais contact coûte plus qu'une abstention) ;
  - précision sur les positifs acceptés ≥ 95 % (concept correct ou de la même famille).
Écrit data/calibration_semantique.json (seuils + statistiques). Usage : python scripts/calibrer_semantique.py
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import semantique  # noqa: E402
from app.taxonomy import DATA_DIR, charger_taxonomie  # noqa: E402

GABARITS = ["Je cherche {e}.", "Il nous faut {e}.", "Nous avons besoin de {e}."]
FA_MAX = 0.02  # budget de fausses acceptations sur les négatifs


def main() -> None:
    tax = charger_taxonomie()
    protos = semantique.prototypes()
    enc = semantique.encodeur()
    ids = protos.ids
    # --- positifs (leave-one-out)
    requetes, attendus, retirer = [], [], []
    for cid in ids:
        passages = protos.passages[cid]
        for j, p in enumerate(passages[1:], start=1):  # 0 = libellé, gardé
            e = p.removeprefix("passage: ")
            g = GABARITS[(j + len(cid)) % len(GABARITS)]
            requetes.append("query: " + g.format(e=e))
            attendus.append(cid)
            retirer.append(j)
    vq = enc.encoder(requetes)
    pos = []
    for v, cid, j in zip(vq, attendus, retirer):
        m = protos.matrice.copy()
        m[ids.index(cid)] = protos._proto(cid, sauf_indice=j)
        s = m @ v
        o = np.argsort(-s)
        c1 = ids[o[0]]
        pos.append((float(s[o[0]]), float(s[o[0]] - s[o[1]]), tax.meme_famille(c1, cid)))
    # --- négatifs
    negs_txt = json.loads((DATA_DIR / "calibration_negatifs.json").read_text(encoding="utf-8"))["negatifs"]
    vn = enc.encoder(["query: " + t for t in negs_txt])
    neg = []
    for v in vn:
        s = protos.matrice @ v
        o = np.argsort(-s)
        neg.append((float(s[o[0]]), float(s[o[0]] - s[o[1]])))
    pos_a, neg_a = np.array([(a, b) for a, b, _ in pos]), np.array(neg)
    correct = np.array([c for *_, c in pos])
    # --- grille
    meilleur = None
    for tau in np.round(np.arange(0.78, 0.90, 0.0025), 4):
        for delta in np.round(np.arange(0.0, 0.041, 0.0025), 4):
            acc_p = (pos_a[:, 0] >= tau) & (pos_a[:, 1] >= delta)
            acc_n = (neg_a[:, 0] >= tau) & (neg_a[:, 1] >= delta)
            if not acc_p.any():
                continue
            fa = acc_n.mean()
            precision = correct[acc_p].mean()
            couverture = (acc_p & correct).mean()
            if fa <= FA_MAX and precision >= 0.95 and (meilleur is None or couverture > meilleur["couverture_positifs"]):
                meilleur = {"tau": float(tau), "delta": float(delta), "couverture_positifs": round(float(couverture), 3),
                            "precision_positifs_acceptes": round(float(precision), 3), "fausses_acceptations_negatifs": round(float(fa), 3)}
    sortie = {
        "_description": "Seuils de la couche sémantique, choisis par scripts/calibrer_semantique.py (contrôle du taux de fausses acceptations).",
        "date": date.today().isoformat(), "modele": "multilingual-e5-large (ONNX, fastembed)",
        "n_positifs": len(pos), "n_negatifs": len(neg),
        "top1_correct_sans_seuil": round(float(correct.mean()), 3),
        "budget_fausses_acceptations": FA_MAX,
        "seuils": meilleur or {"tau": 1.0, "delta": 1.0},
    }
    (DATA_DIR / "calibration_semantique.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(sortie, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
