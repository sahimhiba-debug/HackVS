"""Parcours complet AVEC le composant IA, dans un vrai navigateur et contre un vrai serveur Club Pulse : le serveur est
configuré avec `APERTUS_*` et son client HTTP du produit appelle un FAUX Apertus (serveur HTTP local compatible
OpenAI) — aucun réseau, aucune clé : reproductible partout (et en mode salle).

1. un membre ouvre Club Pulse sur son téléphone ; 2. « Agir à plusieurs » → « Comprendre ma demande » ;
3. le serveur appelle RÉELLEMENT le fournisseur (requête reçue, sortie contrainte par schéma, aucun nom envoyé) ;
4. la sortie est validée ; 5. elle apparaît, dite « Compris par Apertus — à vérifier » ; 6. le membre continue
(« Chercher une proposition ») ; 7. fournisseur en panne ou sortie invalide → règles simples, dites, et le parcours
continue. Ce test ne mesure PAS la qualité d'Apertus (voir eval/eval_apertus.py)."""
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from intelligence.demo import BESOIN_SOPHIE
from tests.test_e2e_scene import _chromium, serveur

SORTIE = {"objet": "tisanes", "langue_public": "de", "manquant": [],
          "fenetre": {"jour": "2026-10-08", "debut": "14:00", "fin": "18:00"},
          "exigences": [{"role": "voix", "nature": "competence", "concept": None, "geste": "Présenter les tisanes en allemand",
                         "duree_min": 45, "livrable": None},
                        {"role": "lieu", "nature": "lieu", "concept": None, "geste": "Prêter un stand", "duree_min": 45, "livrable": None}]}


class FauxApertus:
    """Serveur HTTP local, compatible OpenAI ; `mode` : « ok », « invalide » (texte non JSON) ou « panne » (503)."""

    def __init__(self):
        self.mode, self.recues = "ok", []
        faux = self

        class Gestion(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                corps = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                faux.recues.append({"chemin": self.path, "corps": corps, "auth": self.headers.get("Authorization", "")})
                if faux.mode == "panne":
                    self.send_response(503)
                    self.end_headers()
                    return
                contenu = json.dumps(SORTIE) if faux.mode == "ok" else "Bien sûr ! Voici ce que je propose…"
                rep = json.dumps({"choices": [{"message": {"content": contenu}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(rep)))
                self.end_headers()
                self.wfile.write(rep)
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.srv = ThreadingHTTPServer(("127.0.0.1", self.port), Gestion)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()


@pytest.fixture(scope="module")
def avec_ia():
    faux = FauxApertus()
    env = {"APERTUS_BASE_URL": f"http://127.0.0.1:{faux.port}/v1", "APERTUS_API_KEY": "cle-e2e-fictive-" + "z" * 24,
           "APERTUS_MODEL": "swiss-ai/Apertus-faux-e2e", "APERTUS_BUDGET_S": "6"}
    with serveur(**env) as base:
        yield base, faux
    faux.srv.shutdown()


def _demander(pg, texte):
    pg.click("nav.onglets >> text=Agir à plusieurs")
    pg.fill("#besoin", texte)
    pg.click("#comprendre")
    pg.wait_for_selector("#exigences .exigence")
    return pg.inner_text("p.ia")


def test_parcours_avec_ia_puis_repli_quand_le_fournisseur_flanche(avec_ia):
    pw = pytest.importorskip("playwright.sync_api")
    import urllib.request
    base, faux = avec_ia
    entete = {"X-Pulse-Console": "1", "Content-Type": "application/json"}
    urllib.request.urlopen(urllib.request.Request(base + "/api/pulse/demo/reinitialiser", data=b"{}", headers=entete))
    codes = {p["id"]: p["code"] for p in json.load(urllib.request.urlopen(
        urllib.request.Request(base + "/api/pulse/console/personas", headers=entete)))}
    erreurs: list[str] = []
    with pw.sync_playwright() as p:
        b = _chromium(p)
        pg = b.new_context(viewport={"width": 390, "height": 844}).new_page()
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.on("response", lambda r: erreurs.append(f"{r.status} {r.url}") if r.status >= 500 else None)
        pg.goto(base + f"/app?code={codes['n01']}#acces")                  # 1. le membre ouvre Club Pulse
        pg.click("text=Continuer")
        pg.wait_for_selector("h1:has-text('Mes actions')")

        # 2-5. l'IA est réellement appelée, sa sortie validée puis montrée comme une PROPOSITION
        faux.mode, n = "ok", len(faux.recues)
        etiquette = _demander(pg, BESOIN_SOPHIE)
        assert len(faux.recues) == n + 1, "le fournisseur n'a pas été appelé"
        appel = faux.recues[-1]
        assert appel["chemin"] == "/v1/chat/completions" and appel["corps"]["model"] == "swiss-ai/Apertus-faux-e2e"
        assert appel["corps"]["response_format"]["json_schema"]["strict"] is True and appel["auth"].startswith("Bearer ")
        assert "Sophie" not in json.dumps(appel["corps"], ensure_ascii=False)          # aucun nom du coffre ne sort
        assert "Compris par Apertus" in etiquette and "à vérifier" in etiquette, etiquette
        roles = pg.eval_on_selector_all("#exigences .exigence", "els => els.map(e => e.dataset.role)")
        assert roles == ["voix", "lieu"]                                         # ce que le modèle a proposé, validé
        assert pg.input_value("#f-jour") == "2026-10-08"

        # 6. le membre décide et continue : rien n'a été écrit avant ce geste
        pg.click("#chercher")
        pg.wait_for_function("() => location.hash.startsWith('#essai/')")
        pg.wait_for_selector("text=Ce que le Club peut réunir")

        # 7. fournisseur qui répond n'importe quoi, puis en panne : règles simples, dites, et le parcours continue
        for mode in ("invalide", "panne"):
            faux.mode, n = mode, len(faux.recues)
            pg.goto(base + "/app#actions")
            pg.wait_for_selector("h1:has-text('Mes actions')")
            etiquette = _demander(pg, BESOIN_SOPHIE)
            assert len(faux.recues) > n, mode                                   # il a bien été appelé…
            assert "Règles simples, aucun modèle utilisé" in etiquette, (mode, etiquette)   # …et le repli est dit
            pg.click("#chercher")
            pg.wait_for_function("() => location.hash.startsWith('#essai/')")
            pg.wait_for_selector("text=Ce que le Club peut réunir")
        b.close()
    assert not erreurs, erreurs
