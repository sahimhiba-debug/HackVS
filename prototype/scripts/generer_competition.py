"""Génère les documents dérivés du dossier de compétition à partir de leurs SOURCES (jamais édités à la main) :

- competition/video/{VIDEO_SCRIPT,VIDEO_SHOTLIST,VIDEO_TIMELINE,VOICEOVER,CAPTIONS}.md ← captions.json + timeline_mesuree.json
- competition/rehearsal/TIMING.md ← PITCH_*.md (durée estimée, mots, jargon, temps avant la démo)

    python scripts/generer_competition.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

COMP = Path(__file__).resolve().parents[2] / "competition"
MOTS_PAR_MINUTE = 140           # débit calme en français (hypothèse de répétition, à mesurer au chronomètre)
JARGON = ["solveur", "optimiseur", "pareto", "graphe", "benchmark", "mcp", "api", "llm", "embedding", "milp", "heuristique",
          "idempotent", "déterministe", "réciprocité", "abstention", "simulation", "synthétique", "architecture", "algorithme"]


def srt_temps(s: float) -> str:
    h, m, sec = int(s // 3600), int(s % 3600 // 60), s % 60
    return f"{h:02d}:{m:02d}:{int(sec):02d},{int(round((sec % 1) * 1000)):03d}"


def video() -> None:
    cfg = json.loads((COMP / "video" / "captions.json").read_text(encoding="utf-8"))
    mesure = COMP / "video" / "timeline_mesuree.json"
    reel = json.loads(mesure.read_text(encoding="utf-8")) if mesure.exists() else None
    plans, t, lignes_tl, srt = cfg["plans"], 0.0, [], []
    for i, p in enumerate(plans):
        debut = t
        t += p["duree"]
        lignes_tl.append(f"| {i + 1} | {srt_temps(debut)[:8]} → {srt_temps(t)[:8]} | {p['duree']} s | étape {p['etape']} | {p['texte']} |")
        srt += [str(i + 1), f"{srt_temps(debut)} --> {srt_temps(t)}", p["texte"], ""]
    (COMP / "video" / "captions.srt").write_text("\n".join(srt), encoding="utf-8")
    entete = "> Généré par `prototype/scripts/generer_competition.py` depuis `captions.json` (source unique). Ne pas éditer.\n"
    (COMP / "video" / "VIDEO_TIMELINE.md").write_text(
        "# Chronologie de la vidéo\n\n" + entete + f"\nDurée prévue : {t:.0f} s."
        + (f" Durée mesurée à l'enregistrement : {sum(r['duree_s'] for r in reel):.0f} s." if reel else "")
        + "\n\n| Plan | Temps | Durée | Écran | Texte |\n|---|---|---|---|---|\n" + "\n".join(lignes_tl) + "\n", encoding="utf-8")
    (COMP / "video" / "VOICEOVER.md").write_text(
        "# Voix off (lue d'une voix calme ; mêmes mots que les sous-titres)\n\n" + entete + "\n"
        + "\n\n".join(p["texte"] for p in plans) + "\n", encoding="utf-8")
    (COMP / "video" / "CAPTIONS.md").write_text(
        "# Sous-titres\n\n" + entete + "\nFichier SRT : `captions.srt` (généré). Sous-titres aussi incrustés dans la vidéo "
        "par un calque HTML pendant l'enregistrement (aucune image retouchée).\n", encoding="utf-8")
    (COMP / "video" / "VIDEO_SHOTLIST.md").write_text(
        "# Liste des plans\n\n" + entete + "\nTous les plans sont des captures de la VRAIE scène `/demo/stage` (1440×810), "
        "enregistrées par Playwright. Aucun plan de diapositive.\n\n| Plan | Écran | Mouvement |\n|---|---|---|\n"
        + "\n".join(f"| {i + 1} | étape {p['etape']} de la scène | {'défilement lent de la carte' if p.get('defiler') else 'fixe'}"
                    f"{' · plan de fin' if p.get('fin') else ''} |" for i, p in enumerate(plans)) + "\n", encoding="utf-8")
    (COMP / "video" / "VIDEO_SCRIPT.md").write_text(
        "# Script vidéo\n\n" + entete + "\n**Structure.** Problème (0–16 s) → produit et personne (16–46 s) → décision "
        "difficile : preuves, abstention (46–73 s) → consentement et relation (73–98 s) → suivi prouvé et silence "
        "(98–112 s) → réseau (112–137 s) → phrase de fin.\n\n**Reproduire.** `cd prototype && python scripts/enregistrer_video.py` "
        "(lance le serveur localement, enregistre `competition/video/demo.webm`, capture `competition/evidence/scene_*.png`).\n\n"
        "**Règles.** Aucune fonctionnalité fictive : chaque écran est la scène réelle ; données de scène FICTIVES, étiquetées ; "
        "aucune musique ni effet ajouté ; si la voix off est enregistrée, lire VOICEOVER.md mot pour mot.\n", encoding="utf-8")


def repetition() -> None:
    lignes = ["# Minutage des pitchs (mesuré sur le texte)", "",
              f"> Généré par `prototype/scripts/generer_competition.py`. Débit supposé : {MOTS_PAR_MINUTE} mots/min "
              "(à recaler au chronomètre pendant la répétition).", "",
              "| Version | Mots | Durée estimée | Cible | Jargon (occurrences) | Densité de jargon | Temps avant la démo |", "|---|---|---|---|---|---|---|"]
    for nom, cible in (("PITCH_90SEC.md", 90), ("PITCH_3MIN.md", 180), ("PITCH_5MIN.md", 300)):
        f = COMP / nom
        if not f.exists():
            continue
        brut = re.sub(r"<!--.*?-->", "", f.read_text(encoding="utf-8"), flags=re.S)
        texte = "\n".join(l for l in brut.splitlines() if not l.startswith("#"))
        texte_sans_regie = re.sub(r"\*\*\[.*?\]\*\*|\[.*?\]", "", texte)
        mots = re.findall(r"[\wÀ-ÿ'’-]+", texte_sans_regie)
        jargon = sum(1 for m in mots if m.lower() in JARGON)
        m_demo = re.search(r"\[[^\]]*démo", texte)                # premier repère de régie qui lance la démo
        avant_demo = re.sub(r"\*\*\[.*?\]\*\*|\[.*?\]", "", texte[:m_demo.start()]) if m_demo else texte_sans_regie
        s_demo = len(re.findall(r"[\wÀ-ÿ'’-]+", avant_demo)) / MOTS_PAR_MINUTE * 60
        duree = len(mots) / MOTS_PAR_MINUTE * 60
        lignes.append(f"| {nom} | {len(mots)} | {duree:.0f} s | {cible} s | {jargon} | {100 * jargon / max(1, len(mots)):.1f} % | {s_demo:.0f} s |")
    lignes += ["", "Lecture : une durée estimée au-delà de la cible = couper ; densité de jargon > 3 % = reformuler.", ""]
    (COMP / "rehearsal" / "TIMING.md").write_text("\n".join(lignes), encoding="utf-8")


if __name__ == "__main__":
    video()
    repetition()
    print((COMP / "rehearsal" / "TIMING.md").read_text(encoding="utf-8"))
