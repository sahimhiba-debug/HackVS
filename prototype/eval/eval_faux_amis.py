"""Faux amis composés : la compétence trompeuse ne doit pas être extraite (analyse par règles).

Usage (depuis prototype/) : python -m eval.eval_faux_amis
"""
from __future__ import annotations

import json
from pathlib import Path

from app.parser_rules import analyser
from app.taxonomy import charger_taxonomie

ICI = Path(__file__).resolve().parent


def evaluer() -> dict:
    tax = charger_taxonomie()
    cas = json.loads((ICI / "cas_faux_amis_composes.json").read_text(encoding="utf-8"))["cas"]
    res = {"liste": [0, 0], "hors_liste": [0, 0], "echecs": []}
    for c in cas:
        b = analyser(c["texte"], tax)
        piege = any(x.type == "expertise" and tax.meme_famille(x.valeur, c["interdit"]) for x in b.criteres)
        k = "hors_liste" if c["hors_liste"] else "liste"
        res[k][0] += not piege
        res[k][1] += 1
        if piege:
            res["echecs"].append(c["texte"])
    return {"evites_liste": f"{res['liste'][0]}/{res['liste'][1]}", "evites_hors_liste": f"{res['hors_liste'][0]}/{res['hors_liste'][1]}",
            "echecs": res["echecs"]}


if __name__ == "__main__":
    print(json.dumps(evaluer(), ensure_ascii=False, indent=1))
