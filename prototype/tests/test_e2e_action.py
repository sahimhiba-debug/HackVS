"""L'ACTION COLLECTIVE dans un VRAI navigateur : deux téléphones (Sophie, porteuse ; Léa, voix allemande) et l'écran
commun. Pauline, Markus et Nicolas sont JOUÉS par la console (marqué). Le parcours : Sophie écrit son besoin → confirme
les exigences → le serveur trouve le créneau → elle publie → Léa accepte sur SON téléphone → Léa change SA disponibilité
(17 h) → l'écran commun montre ce qui tombe et les adaptations → Sophie choisit → Léa reconfirme → Sophie engage →
Léa transmet la fiche → elle apparaît chez Sophie, qui confirme la réception (de la fiche : la présentation
reste à tenir) → +30 jours simulés : rien n'est reconduit, le résultat reste inconnu sans déclaration. On mesure aussi le délai entre un geste sur
un téléphone et sa visibilité sur l'écran commun. Captures dans HACKVS_CAPTURES si défini.
Ignoré seulement si aucun Chromium n'est disponible ; obligatoire en CI."""
import json
import os
import time
import urllib.request

import pytest

from intelligence.demo import BESOIN_SOPHIE, FICHE_DE
from tests.test_e2e_pulse import _sans_debordement, _telephone
from tests.test_e2e_scene import _chromium, url  # noqa: F401  (serveur démo isolé partagé)

CAPTURES = os.environ.get("HACKVS_CAPTURES")
CONSOLE = {"Content-Type": "application/json", "X-Pulse-Console": "1"}
NOMS = ("Sophie", "Carron", "Léa", "Imhof", "Pauline", "Markus", "Nicolas")


def _api(base, chemin, corps=None):
    req = urllib.request.Request(base + chemin, data=json.dumps(corps).encode() if corps is not None else None, headers=CONSOLE)
    return json.loads(urllib.request.urlopen(req).read())


def _jouer(base, eid, qui):
    v = _api(base, f"/api/pulse/console/essais/{eid}")["version"]
    return _api(base, f"/api/pulse/console/essais/{eid}/geste", {"membre": qui, "version": v, "accepte": True})


def _capture(pg, nom):
    if CAPTURES:
        pg.screenshot(path=os.path.join(CAPTURES, f"{nom}.png"), full_page=True)


def _delai_projection(proj, attendu: str, t0: float) -> float:
    proj.wait_for_function("(t) => document.querySelector('main').innerText.includes(t)", arg=attendu, timeout=10_000)
    return (time.perf_counter() - t0) * 1000


def test_action_collective_deux_telephones_et_ecran_commun(url):  # noqa: F811
    pw = pytest.importorskip("playwright.sync_api")
    _api(url, "/api/pulse/demo/reinitialiser", {})
    codes = {p["id"]: p["code"] for p in _api(url, "/api/pulse/console/personas")}
    erreurs: list[str] = []
    delais = {}
    with pw.sync_playwright() as p:
        b = _chromium(p)
        _, s = _telephone(b, url, codes["n01"], (390, 844), erreurs)          # téléphone 1 : Sophie, porteuse
        _, lea = _telephone(b, url, codes["d01"], (412, 915), erreurs)        # téléphone 2 : Léa, voix allemande
        proj = b.new_context(viewport={"width": 1920, "height": 1080}).new_page()
        proj.on("pageerror", lambda e: erreurs.append(str(e)))
        proj.goto(url + "/projection")
        proj.wait_for_selector("text=contributions proposées, dispersées")      # AVANT : des offres éparses, aucune demande
        _capture(proj, "p0_avant")

        # --- 1. le besoin, avec ses mots ; 2. les exigences confirmées ; 3. la proposition trouvée par le serveur
        s.click("nav.onglets >> text=Agir à plusieurs")
        s.fill("#besoin", BESOIN_SOPHIE)
        s.click("#comprendre")
        s.wait_for_selector("#exigences .exigence >> nth=2")
        assert "Règles simples" in s.inner_text("main") or "Apertus" in s.inner_text("main")   # l'origine est dite
        s.click("button:has-text('Reprendre la suggestion')")
        _capture(s, "a1_sophie_exigences")
        s.click("#chercher")
        s.wait_for_selector("text=Proposition complète")
        assert "08.10 16:00–16:45" in s.inner_text("main")
        _capture(s, "a2_sophie_proposition")
        assert _sans_debordement(s)
        assert "contributions proposées, dispersées" in proj.inner_text("main")    # rien n'est projeté sans son accord
        s.click("#projeter")                                                   # SON choix : montrer, en rôles
        proj.wait_for_selector("text=les 3 disponibilités se recouvrent de 16:00 à 17:30")
        _capture(proj, "p1_proposition")
        s.click("#publier-proposition")
        s.wait_for_selector("#creneau")
        eid = s.evaluate("() => location.hash.split('/')[1]")

        # --- 4. accords : Léa sur SON téléphone ; Pauline et Markus JOUÉS (marqué)
        lea.click("nav.onglets >> text=Mes actions")
        lea.click(f"a[href='#essai/{eid}']")
        lea.wait_for_selector("#accepter")
        assert "Fiche produit en allemand" in lea.inner_text("main")
        _capture(lea, "b1_lea_invitation")
        t0 = time.perf_counter()
        lea.click("#accepter")
        delais["accord → écran commun"] = _delai_projection(proj, "1 accord(s) sur 3", t0)
        for qui in ("s01", "s14"):
            _jouer(url, eid, qui)
        proj.wait_for_selector("text=Coopération prête")
        _capture(proj, "p2_cooperation_prete")

        # --- 5. perturbation : Léa n'est disponible qu'à 17 h (valeur choisie par le jury), sur SON téléphone
        lea.reload()
        lea.wait_for_selector("summary:has-text('Ma disponibilité a changé')")
        lea.click("summary:has-text('Ma disponibilité a changé')")
        lea.fill("#dispo-debut", "17:00")
        lea.fill("#dispo-fin", "19:00")
        t0 = time.perf_counter()
        lea.click("#changer-dispo")
        delais["perturbation → écran commun"] = _delai_projection(proj, "Ce qui vient de changer", t0)
        texte = proj.inner_text("main")
        assert "Ne couvre plus : Voix en allemand" in texte and "17:00–17:45" in texte
        _capture(proj, "p3_perturbation")
        s.reload()
        s.wait_for_selector("text=Une condition a changé")
        _capture(s, "a3_sophie_adaptation")
        assert s.locator("#lancer").count() == 0                              # aucun lancement possible : le bouton n'existe pas

        # --- 6. adaptation choisie par Sophie ; tout le monde reconfirme
        s.click("button:has-text('17:00–17:45')")
        s.wait_for_selector("text=Créneau : 08.10 17:00–17:45")
        lea.reload()
        lea.wait_for_selector("#accepter")
        lea.click("#accepter")
        for qui in ("s14", "s04"):
            _jouer(url, eid, qui)
        proj.wait_for_selector("text=Coopération prête")
        _capture(proj, "p4_readapte")

        # --- 7. engagé ; 8. la fiche : transmise par Léa, reçue par Sophie
        s.reload()
        s.click("#lancer")
        s.wait_for_selector("text=en cours")
        lea.reload()
        lea.wait_for_selector("#livraison")
        lea.fill("#livraison", FICHE_DE)
        lea.click("#transmettre")
        lea.wait_for_selector("text=réception à confirmer")
        s.reload()
        s.wait_for_selector("#fiche-e1")
        assert "Kräutertees" in s.inner_text("#fiche-e1")
        _capture(s, "a4_sophie_fiche_recue")
        s.click("#recu-e1")
        s.wait_for_selector("text=réception de la fiche confirmée")
        assert s.locator("#constater-e1").count() == 0                        # la présentation n'a pas eu lieu : rien à constater
        proj.wait_for_selector(".exig[data-palier='livrable reçu']")
        assert "pas encore réalisée" in proj.inner_text("main")
        _capture(proj, "p5_fiche_recue")

        # --- 9. continuité : horloge de démonstration +30 jours (SIMULÉE) — rien n'est reconduit, rien n'est supposé
        _api(url, "/api/pulse/console/temps", {"jours": 30})
        proj.wait_for_selector("text=aucun résultat n'a été déclaré")
        assert proj.locator(".exig[data-palier='livrable reçu']").count() == 1   # la fiche reçue le reste
        _capture(proj, "p6_trente_jours")

        brut = proj.inner_text("body")
        assert not [n for n in NOMS if n in brut], "l'écran commun ne nomme personne"
        assert "joué par l'équipe" in brut.lower() and "accepte sa part" in brut        # les gestes joués sont DITS
        b.close()
    assert not erreurs, erreurs
    for k, v in delais.items():
        assert v < 3000, (k, v)                                               # visible en moins de 3 s (lecture toutes les 0,7 s)
    if CAPTURES:
        with open(os.path.join(CAPTURES, "delais.json"), "w", encoding="utf-8") as f:
            json.dump({k: round(v) for k, v in delais.items()}, f, ensure_ascii=False, indent=1)
