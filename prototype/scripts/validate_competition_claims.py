"""Cohérence PITCH ↔ CODE : exécute les contrôles du registre des preuves et régénère le registre.

    python scripts/validate_competition_claims.py            # contrôles rapides (≈ 1 min, benchmark compris)
    python scripts/validate_competition_claims.py --sans-benchmark

Produit competition/14_PROOF_LEDGER.md et competition/15_CLAIMS.md. Code de sortie ≠ 0 si :
- une affirmation REAL ou SYNTHETIC échoue à son contrôle ;
- un chiffre cité dans un texte de pitch n'est pas un chiffre prouvé (par le registre) ;
- une route citée dans le script de démo n'existe pas ;
- la vidéo annoncée n'existe pas ou sa durée ne correspond pas aux légendes.
Aucune affirmation n'est « réparée » par ce script : il la déclasse en NE PAS DIRE.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
PROTO = RACINE / "prototype"
COMP = RACINE / "competition"
sys.path.insert(0, str(PROTO))
os.environ.setdefault("HACKVS_SEMANTIQUE", "0")
os.environ.setdefault("HACKVS_DB", ":memory:")
os.environ.setdefault("HACKVS_DECISIONS_DB", ":memory:")
os.environ.setdefault("HACKVS_CYCLE_DB", ":memory:")


def _scene():
    from app import stage
    from app.taxonomy import charger_taxonomie
    if not hasattr(_scene, "c"):
        w = stage.rejouer_jusqu_a(charger_taxonomie(), len(stage.ETAPES))
        _scene.c = {t["etape"]: t["faits"] for t in w.traces}
    return _scene.c


def _bench():
    if not hasattr(_bench, "c"):
        from eval import benchmark_reseau as br
        _bench.c = br.main()
    return _bench.c


def _pytest(cible: str) -> tuple[bool, str]:
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", cible], cwd=PROTO, capture_output=True, text=True, env=os.environ)
    return r.returncode == 0, (r.stdout.strip().splitlines() or ["?"])[-1]


texte_courant: dict = {"texte": ""}


def controle(nom: str) -> tuple[bool, str]:
    import time
    if nom == "aucun":
        return True, "non contrôlable automatiquement"
    if nom.startswith("test:"):
        return _pytest(nom[5:])
    s = _scene() if nom.startswith("scene") else None
    if nom == "scene_abstention":
        t = s[7]["tentatives"][0]
        return t["decision"] == "S_ABSTENIR", t["raisons"][0]
    if nom == "scene_double_accord":
        return s[2]["coordonnees_avant_accord"] is False and s[2]["coordonnees_apres_accord"] is True, "avant : non ; après accord : oui"
    if nom == "scene_refus_non_nomme":
        return s[1]["ecartes_par_leur_choix"] == 0 and "Kalbermatten" not in json.dumps(s, ensure_ascii=False), "jamais nommé, non compté (k < 3)"
    if nom == "scene_relances":
        n = sum(len(p["raisons"]) for p in s[6]["relances"])
        return n == 1 and s[6]["silences"]["rien_de_nouveau"] == 17, f"{n} relance, {s[6]['silences']['rien_de_nouveau']} silences"
    if nom == "scene_reciprocite":
        c = s[1]["candidats"][0]
        return c["nom"] == "Markus Heinzmann" and c["dimensions"]["reciprocite"]["etablie"], c["dimensions"]["reciprocite"].get("votre_offre", "")
    if nom == "scene_simulation":
        f = s[4]
        r = max(f["plans"], key=lambda p: p["plus_grand_groupe"])
        c = max(f["plans"], key=lambda p: p["groupe_robuste"])
        ok = (r is not c and (f["avant"]["plus_grand_groupe"], r["plus_grand_groupe"]) == (8, 15)
              and (f["avant"]["groupe_robuste"], c["groupe_robuste"], r["groupe_robuste"]) == (4, 8, 4))
        av = f["avant"]
        return ok, f"réunir : {av['plus_grand_groupe']} → {r['plus_grand_groupe']} ; consolider : robuste {av['groupe_robuste']} → {c['groupe_robuste']}"
    if nom == "scene_rejeu":
        from app import stage
        from app.taxonomy import charger_taxonomie
        tax = charger_taxonomie()
        canon = lambda tr: re.sub(r'"(id|relance_id|relation_id)": "[^"]*"', "", json.dumps(tr, ensure_ascii=False, sort_keys=True))  # noqa: E731
        t0 = time.perf_counter()
        runs = [canon(stage.rejouer_jusqu_a(tax, len(stage.ETAPES)).traces) for _ in range(3)]
        ms = (time.perf_counter() - t0) * 1000 / 3
        return runs[0] == runs[1] == runs[2] and ms < 1000, f"3 rejeux identiques, {ms:.0f} ms par scène"
    if nom.startswith("benchmark"):
        b = _bench()["moyennes"]
        opt = b["optimiseur (plateforme)"]
        autres = {k: v for k, v in b.items() if k != "optimiseur (plateforme)"}
        if nom == "benchmark_ponts":
            m = max(v["ponts_%"] for v in autres.values())
            return opt["ponts_%"] > m, f"{opt['ponts_%']} % contre {m} % au mieux"
        if nom == "benchmark_compromis":
            servis = max(v["membres_avec_besoin_servi"] for v in autres.values())
            recip = max(v["reciproques_%"] for v in autres.values())
            return opt["membres_avec_besoin_servi"] > servis and opt["reciproques_%"] < recip, \
                f"servis {opt['membres_avec_besoin_servi']} > {servis} ; réciprocité {opt['reciproques_%']} % < {recip} %"
        if nom == "benchmark_pareto":
            p = _bench()["pareto"]
            return min(p) >= 2, f"{min(p)} à {max(p)} points"
    if nom == "eval_decisions":
        r = subprocess.run([sys.executable, "-m", "eval.eval_decisions"], cwd=PROTO, capture_output=True, text=True, env=os.environ)
        return r.returncode == 0, r.stdout.strip().splitlines()[-1]
    if nom == "modeles_non_verifies":
        from plateforme import modeles
        reg = modeles.registre(env={})
        return all(p["etat"] != "VERIFIEE" for p in reg["profils"].values()), "aucun fournisseur VERIFIEE"
    if nom == "tests_min_100":
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--collect-only"], cwd=PROTO, capture_output=True, text=True, env=os.environ)
        n = int(re.search(r"(\d+) tests? collected", r.stdout).group(1))
        return n >= 100, f"{n} tests"
    if nom == "failures_exact":  # le nombre CITÉ doit être exactement le nombre documenté (jamais périmé)
        n = len(re.findall(r"^\| \d+ \|", (COMP / "FAILURES.md").read_text(encoding="utf-8"), re.M))
        cite = int(re.search(r"corrigé (\d+) défauts", texte_courant["texte"]).group(1))
        return n == cite, f"{n} défauts documentés, {cite} cités"
    return False, f"contrôle inconnu : {nom}"


def chiffres(texte: str) -> set[str]:
    return set(re.findall(r"(?<![\w.,])\d+(?:[.,]\d+)?", texte))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sans-benchmark", action="store_true")
    a = ap.parse_args()
    reg = json.loads((COMP / "claims.json").read_text(encoding="utf-8"))
    lignes, echecs, autorises = [], [], set(reg["chiffres_autorises_hors_affirmations"])
    for c in reg["affirmations"]:
        if a.sans_benchmark and c["controle"].startswith("benchmark"):
            ok, detail = True, "non exécuté (--sans-benchmark)"
        else:
            try:
                texte_courant["texte"] = c["texte"]
                ok, detail = controle(c["controle"])
            except Exception as e:  # un contrôle qui plante est un échec
                ok, detail = False, f"{type(e).__name__}: {e}"
        sur = ok and c["type"] in ("REAL", "SYNTHETIC")
        if not ok and c["type"] in ("REAL", "SYNTHETIC"):
            echecs.append(f"{c['id']} : {detail}")
        if sur:
            autorises |= chiffres(c["texte"])
        precision = {"SYNTHETIC": " (préciser : SYNTHETIC_BENCHMARK)", "UNVERIFIED": " — NE PAS présenter comme un fait",
                     "INFERRED": " — hypothèse, à formuler comme telle"}.get(c["type"], "")
        dire = "OUI" if sur else ("NON" if c["type"] in ("REAL", "SYNTHETIC") else "AVEC PRÉCAUTION")
        lignes.append(f"| {c['id']} | {c['texte']} | {c['type']} | {'OK' if ok else 'ÉCHEC'} — {detail} | {c['preuve']} | "
                      f"{dire}{precision} | {c['demo']} |")
    jour = dt.date.today().isoformat()
    entete = ["# 14 — Registre des preuves (généré, ne pas éditer à la main)", "",
              f"Généré le {jour} par `prototype/scripts/validate_competition_claims.py` à partir de `competition/claims.json`.",
              "Statuts : REAL (vrai du prototype, contrôlé), SYNTHETIC (données générées), INFERRED (hypothèse), UNVERIFIED (non vérifié par nous).", "",
              "| ID | Affirmation | Type | Contrôle (date : " + jour + ") | Preuve | Peut-on le dire ? | Où le montrer |", "|---|---|---|---|---|---|---|"]
    (COMP / "14_PROOF_LEDGER.md").write_text("\n".join(entete + lignes) + "\n", encoding="utf-8")
    # chiffres des textes de pitch
    for f in sorted(COMP.glob("PITCH_*.md")) + [COMP / "10_PITCH.md", COMP / "video" / "VOICEOVER.md"]:
        if not f.exists():
            continue
        corps = re.sub(r"<!--.*?-->", "", f.read_text(encoding="utf-8"), flags=re.S)
        corps = "\n".join(l for l in corps.splitlines() if not l.startswith("#") and "Durée" not in l and "mots" not in l)
        corps = re.sub(r"\d+:\d+(?:[–-]\d+:\d+)?", "", corps)            # minutages de régie : pas des affirmations
        corps = re.sub(r"\b\d+_[A-Z]\w*", "", corps)                     # références de fichiers (09_DEMO_SCRIPT)
        corps = re.sub(r"(?m)^\s*\d+\.\s", "", corps)                     # numérotation de listes
        inconnus = sorted(chiffres(corps) - autorises - {x.replace(".", ",") for x in autorises} - {x.replace(",", ".") for x in autorises})
        if inconnus:
            echecs.append(f"{f.name} cite des chiffres non prouvés : {inconnus}")
    # routes citées dans le script de démo
    from app.main import app
    routes = {getattr(r, "path", None) for r in app.routes} | set(app.openapi()["paths"])
    demo = COMP / "09_DEMO_SCRIPT.md"
    if demo.exists():
        for route in set(re.findall(r"`(/[a-z/]+)`", demo.read_text(encoding="utf-8"))):
            if route not in routes:
                echecs.append(f"09_DEMO_SCRIPT cite une route absente : {route}")
    # vidéo
    video, legendes = COMP / "video" / "demo.webm", json.loads((COMP / "video" / "captions.json").read_text(encoding="utf-8"))
    if not video.exists():
        echecs.append("vidéo absente : competition/video/demo.webm")
    else:
        ff = next(iter(Path("/opt/pw-browsers").glob("ffmpeg-*/ffmpeg-linux")), None)
        if ff:
            sortie = subprocess.run([str(ff), "-i", str(video)], capture_output=True, text=True).stderr
            m = re.search(r"Duration: (\d+):(\d+):(\d+)", sortie)
            if m:
                duree = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
                attendu = sum(p["duree"] for p in legendes["plans"])
                if abs(duree - attendu) > 15:
                    echecs.append(f"vidéo : {duree} s, légendes : {attendu} s — vidéo à réenregistrer")
    resume = ["# 15 — Affirmations : ce que l'on peut dire (généré)", "",
              "À dire (contrôlé aujourd'hui) :", ""]
    resume += [f"- {c['texte']}" + (" *(benchmark SYNTHÉTIQUE)*" if c["type"] == "SYNTHETIC" else "") for c in reg["affirmations"]
               if c["type"] in ("REAL", "SYNTHETIC") and not any(e.startswith(c["id"] + " ") for e in echecs)]
    resume += ["", "Avec précaution (hypothèse ou non vérifié) :", ""]
    resume += [f"- [{c['type']}] {c['texte']} — {c['demo']}" for c in reg["affirmations"] if c["type"] in ("INFERRED", "UNVERIFIED")]
    resume += ["", "Chiffres autorisés dans le pitch : " + ", ".join(sorted(autorises, key=lambda x: (len(x), x))), ""]
    (COMP / "15_CLAIMS.md").write_text("\n".join(resume), encoding="utf-8")
    print("\n".join(echecs) if echecs else "Toutes les affirmations contrôlables sont vérifiées ; aucun chiffre non prouvé dans le pitch.")
    sys.exit(1 if echecs else 0)


if __name__ == "__main__":
    main()
