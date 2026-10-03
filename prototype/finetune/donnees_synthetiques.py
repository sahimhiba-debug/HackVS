"""PIPELINE D'AFFINAGE (P3 n°11) — prêt à entraîner, ENTRAÎNEMENT NON LANCÉ.

Tâche visée : la classification d'une demande dans la taxonomie des métiers (celle que `make eval-classification`
mesure). Données SYNTHÉTIQUES générées par Apertus 70B (CSCS), pondérées par la LISTE DU CLUB (distribution des métiers
de `docs/data/entreprises.csv`, « autre » exclu) et par les 9 capacités types (« Ce que votre Club pourrait
assembler ») ; aucune donnée réelle de membre, aucune phrase Tally.

    python -m finetune.donnees_synthetiques --n 200 --dry-run        # tirage + consignes, AUCUN appel
    python -m finetune.donnees_synthetiques --n 200                  # Apertus ; pause FINETUNE_PAUSE_S (4 s) entre appels
    → var/finetune/brut.jsonl, var/finetune/garde.jsonl (format « messages » pour l'affinage), var/finetune/rapport.md

FILTRE ALLER-RETOUR : un exemple n'est gardé que si (1) la demande générée est reclassée dans le MÊME métier par le
classeur du produit, (2) elle est « SMART » complète (coach : ni quand, ni combien, ni où ne manquent), (3) elle ne
contient ni courriel ni téléphone. Configuration LoRA : `finetune/lora_apertus_8b.yaml`."""
from __future__ import annotations

import json
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Callable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval import classification_metiers as cm  # noqa: E402
from intelligence import assembler, club_cherche, coach_smart, metiers  # noqa: E402

SORTIE = Path(__file__).resolve().parents[1] / "var" / "finetune"
SCHEMA_DEMANDE = {"type": "object", "additionalProperties": False, "required": ["texte"], "properties": {"texte": {"type": "string"}}}


def poids() -> dict[str, int]:
    """Métiers de la liste du Club et leur nombre d'entreprises (« autre » exclu : rien à apprendre d'un métier inconnu)."""
    liste = club_cherche.entreprises_par_metier()
    if liste is None:
        raise FileNotFoundError("liste du Club absente : docs/data/entreprises.csv")
    return {m: n for m, n in liste["par_metier"].items() if m != "autre" and n > 0}


def capacites_de(metier: str) -> list[str]:
    return [titre for _, titre, pieces in assembler.CAPACITES if any(metier in ms for _, ms in pieces)]


def tirage(n: int, graine: int = 2026) -> list[dict]:
    """n couples (métier, capacité), métier tiré au prorata de la liste ; capacité tirée parmi celles où il compte."""
    rnd = random.Random(graine)
    p = poids()
    ms = sorted(p)
    res = []
    for _ in range(n):
        m = rnd.choices(ms, weights=[p[x] for x in ms])[0]
        caps = capacites_de(m)
        res.append({"metier": m, "capacite": rnd.choice(caps) if caps else None, "langue": rnd.choices(["fr", "de"], weights=[4, 1])[0]})
    return res


def consigne(t: dict) -> str:
    lib = metiers.libelle(t["metier"])
    cadre = f" dans le cadre de « {t['capacite']} »" if t["capacite"] else ""
    langue = "en allemand" if t["langue"] == "de" else "en français"
    return (f"Écris, {langue}, UNE demande réaliste qu'un membre d'un club d'entrepreneurs valaisan adresserait au Club{cadre}, "
            f"et à laquelle une entreprise du métier « {lib} » pourrait répondre. Précise QUAND (un jour, une heure), "
            "COMBIEN (un nombre) et OÙ (une localité valaisanne). Aucun nom de personne ni d'entreprise, aucun contact. "
            "Une ou deux phrases. Réponds par {\"texte\": \"…\"}.")


def garder(texte: str, metier: str, classer: Callable[[str], Optional[str]]) -> tuple[bool, str]:
    """Le filtre aller-retour. (gardé, motif)."""
    if not 15 <= len(texte) <= 400:
        return False, "longueur"
    if cm.contient_contact(texte):
        return False, "contact"
    if coach_smart.questions(texte):
        return False, "pas SMART : " + ",".join(q["id"] for q in coach_smart.questions(texte))
    reclasse = classer(texte)
    if reclasse != metier:
        return False, f"reclassé « {reclasse} »"
    return True, "gardé"


def exemple_sft(texte: str, metier: str) -> dict:
    return {"messages": [{"role": "system", "content": cm.systeme()}, {"role": "user", "content": texte},
                         {"role": "assistant", "content": json.dumps({"metier": metier, "abstention": False}, ensure_ascii=False)}]}


def main(argv: Optional[list[str]] = None) -> int:
    import argparse
    a = argparse.ArgumentParser()
    a.add_argument("--n", type=int, default=50)
    a.add_argument("--graine", type=int, default=2026)
    a.add_argument("--dry-run", action="store_true")
    x = a.parse_args(argv)
    SORTIE.mkdir(parents=True, exist_ok=True)
    tirages = tirage(x.n, x.graine)
    dist = Counter(t["metier"] for t in tirages)
    if x.dry_run:
        (SORTIE / "consignes.jsonl").write_text("\n".join(json.dumps(t | {"consigne": consigne(t)}, ensure_ascii=False) for t in tirages) + "\n",
                                                encoding="utf-8")
        print(json.dumps({"n": x.n, "distribution": dict(dist.most_common()), "appels": 0}, ensure_ascii=False))
        return 0
    from intelligence.ia import Apertus
    f = Apertus()
    pause = float(os.environ.get("FINETUNE_PAUSE_S", "4"))
    brut, garde, motifs = [], [], Counter()

    def classer(texte: str) -> Optional[str]:
        time.sleep(pause)
        s = cm.classer(f, "apertus", "synthetique", texte)["sortie"]
        return s["metier"] if s else None
    for t in tirages:
        time.sleep(pause)                                           # limite de débit du CSCS : un appel à la fois, espacés
        try:
            texte = json.loads(f.completer("Tu écris des exemples synthétiques, fictifs.", consigne(t), SCHEMA_DEMANDE))["texte"]
        except Exception as e:                                      # une panne est comptée, jamais maquillée
            motifs[f"panne {type(e).__name__} {str(e)[:40]}"] += 1
            continue
        ok, motif = garder(texte, t["metier"], classer)
        motifs[motif.split(" :")[0].split(" «")[0]] += 1
        brut.append(t | {"texte": texte, "garde": ok, "motif": motif})
        if ok:
            garde.append(exemple_sft(texte, t["metier"]))
    (SORTIE / "brut.jsonl").write_text("".join(json.dumps(b, ensure_ascii=False) + "\n" for b in brut), encoding="utf-8")
    (SORTIE / "garde.jsonl").write_text("".join(json.dumps(g, ensure_ascii=False) + "\n" for g in garde), encoding="utf-8")
    r = {"demandes": x.n, "generees": len(brut), "gardees": len(garde), "motifs": dict(motifs), "distribution": dict(dist.most_common()),
         "modele": f.modele, "pause_s": pause}
    (SORTIE / "rapport.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
