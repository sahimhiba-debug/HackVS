"""Banc « la carte devient le profil » : 6 cartes FICTIVES rendues en image (Chromium), envoyées par le CHEMIN DU PRODUIT
(`carte.proposer` : même prompt, même schéma, même validation) au fournisseur configuré. Mesure champ par champ, contre
des attentes fixées avant l'exécution. Ne démontre pas une qualité générale (6 cartes, une mise en page).

    python -m eval.banc_carte            # → eval/resultats_carte/apertus.md"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

PROTO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROTO))

from app.taxonomy import charger_taxonomie  # noqa: E402
from intelligence import carte  # noqa: E402
from intelligence.demo import Demo  # noqa: E402

CAS = PROTO / "eval" / "cas_carte.json"


def _norm(x: str | None) -> str:
    x = unicodedata.normalize("NFKD", x or "").encode("ascii", "ignore").decode().lower()
    return "".join(ch for ch in x if ch.isalnum())


def rendre(c: dict, page) -> str:
    html = (f"<div style='width:700px;height:400px;background:#fff;font-family:sans-serif;padding:40px;box-sizing:border-box'>"
            f"<div style='font-size:22px;color:#666;letter-spacing:2px'>{c['lieu']}</div>"
            f"<div style='font-size:50px;font-weight:800;margin-top:50px'>{c['nom']}</div>"
            f"<div style='font-size:28px;color:#333;margin-top:10px'>{c['entreprise']}</div>"
            f"<div style='font-size:24px;color:#444;margin-top:6px'>{c['ligne']}</div>"
            f"<div style='font-size:20px;color:#888;margin-top:26px'>{c['langues']}</div></div>")
    page.set_content(html)
    return "data:image/png;base64," + base64.b64encode(page.screenshot()).decode()


def main() -> int:
    from playwright.sync_api import sync_playwright
    os.environ.setdefault("HACKVS_ESSAIS_DB", ":memory:")
    club = Demo(charger_taxonomie()).club
    if club.ia.f is None:
        print("aucun fournisseur configuré : rien n'est mesuré")
        return 1
    cas = json.loads(CAS.read_text(encoding="utf-8"))["cas"]
    lignes, justes, total, durees = [], {k: 0 for k in ("entreprise", "metier", "zone", "langue")}, 0, []
    debut = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM", "/opt/pw-browsers/chromium"))
        page = b.new_page(viewport={"width": 700, "height": 400})
        for c in cas:
            t = time.perf_counter()
            r = carte.proposer(club, rendre(c, page))
            durees.append((time.perf_counter() - t) * 1000)
            prop = r["proposition"]
            ok = {k: (_norm(prop.get(k)) == _norm(v)) if k == "entreprise" else prop.get(k) == v for k, v in c["attendu"].items()}
            for k, v in ok.items():
                justes[k] += v
            total += 1
            lignes.append(f"| {c['id']} | {r['source']} | " + " | ".join("✓" if ok[k] else "✗" for k in justes) + " |")
        b.close()
    t = "\n".join([f"# Banc « la carte devient le profil » — {club.ia.f.nom}", "",
                   f"> {debut} UTC · modèle `{getattr(club.ia.f, 'modele', '?')}` · {total} cartes FICTIVES, attentes fixées avant "
                   "(`eval/cas_carte.json`) · chemin du produit (`carte.proposer`). Ne démontre pas une qualité générale.", "",
                   "| Carte | source | entreprise | métier | zone | langue |", "|---|---|---|---|---|---|", *lignes, "",
                   "| Champ | justes |", "|---|---|", *[f"| {k} | {v}/{total} |" for k, v in justes.items()], "",
                   f"Latence par carte : médiane {sorted(durees)[len(durees) // 2]:.0f} ms. Le membre confirme ou corrige TOUJOURS ; "
                   "l'image n'est pas conservée.", ""])
    sortie = PROTO / "eval" / "resultats_carte" / f"{club.ia.f.nom}.md"
    sortie.write_text(t, encoding="utf-8")
    print(t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
