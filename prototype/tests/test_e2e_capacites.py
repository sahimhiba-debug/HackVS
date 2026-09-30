"""LE REGISTRE DES CAPACITÉS dans un VRAI navigateur : l'Établi (écran commun) et deux téléphones.
Vendredi 09.10 (scène du registre ; l'action collective, elle, se joue le jeudi 08.10) : l'Établi montre « Accueillir une
délégation… » à une pièce près (le minibus, en pointillés, avec sa demande) → Pauline répond Oui sur SON téléphone →
l'Établi passe à « le Club peut le faire » → le reçu est sur son téléphone → elle retire son consentement en un geste →
l'Établi dit « ce composant n'est plus disponible », sans jamais la nommer → la demande part vers Markus, pas vers elle.
Chaque écran affiche sa date. Sur échec, les pages sont capturées (tests/capture_e2e.py). Données FICTIVES."""
import pytest

from tests.test_e2e_pulse import _api, _sans_debordement, _telephone
from tests.test_e2e_scene import _chromium, serveur, url  # noqa: F401  (serveur démo isolé partagé)

CARTE = "article[data-finalite='delegation_acheteurs']"


def test_etabli_telephones_reponse_recu_retrait_anonyme(url):  # noqa: F811
    pw = pytest.importorskip("playwright.sync_api")
    _api(url, "/api/pulse/demo/reinitialiser", {})
    codes = {p["id"]: p["code"] for p in _api(url, "/api/pulse/console/personas")}
    erreurs: list[str] = []
    with pw.sync_playwright() as p:
        b = _chromium(p)
        etabli = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        etabli.on("pageerror", lambda e: erreurs.append(str(e)))
        etabli.goto(url + "/etabli")
        carte = etabli.locator(CARTE)
        carte.locator("[data-role=statut]:has-text('il manque une pièce')").wait_for()
        assert "vendredi 09.10" in carte.inner_text()                                  # la carte dit son jour
        assert "date du Club (simulée) : mardi 06.10" in etabli.inner_text("header")   # l'écran dit sa date
        etabli.locator("[data-role=ia]:has-text('IA : aucun modèle configuré — forme déterministe')").wait_for()   # dit, jamais « propulsé par »
        vide = carte.locator(".piece.vide")
        assert "Un minibus de 12 places ou plus" in vide.inner_text() and "Débloquerait 1 capacité" in vide.inner_text()

        _, pauline = _telephone(b, url, codes["s01"], (390, 844), erreurs)
        pauline.click("nav.onglets >> text=Demandes")
        pauline.wait_for_selector("[data-ask]")
        assert "mardi 06.10" in pauline.inner_text("main")                             # le téléphone dit sa date
        pauline.fill("#ask-mots", "Mon minibus a 14 places, libre vendredi après-midi.")
        pauline.click("#ask-proposer")                                                 # aucun modèle ici : la forme déterministe, dite
        pauline.locator("#ask-ia:has-text('forme déterministe, sans IA — aucun modèle configuré')").wait_for()
        assert "Remplissez le formulaire vous-même" in pauline.inner_text("#ask-ia")
        pauline.fill("#att-places", "14")
        pauline.click("#ask-oui")
        pauline.wait_for_selector("[data-recu='delegation_acheteurs']")
        assert "valable" in pauline.inner_text("[data-recu='delegation_acheteurs']")
        carte.locator("[data-role=statut]:has-text('le Club peut le faire')").wait_for()
        assert carte.locator(".piece.vide").count() == 0

        carte.click()                                                                  # le passeport
        etabli.wait_for_selector("section[aria-label='Passeport de capacité']")
        passeport = etabli.inner_text("section[aria-label='Passeport de capacité']")
        assert "fournie par une personne du Club, consentement donné" in passeport and "Pièces critiques" in passeport
        etabli.click("#rediger-recit")                                                 # NARRATE : ici, le gabarit des faits, dit
        etabli.locator("[data-role=recit-ia]:has-text('forme déterministe, sans IA')").wait_for()
        assert "[F1]" in etabli.inner_text("#recit") and "État : le Club peut le faire." in etabli.inner_text("#recit")
        etabli.click("#ia-bascule")                                                    # l'interrupteur, visible
        etabli.locator("[data-role=ia]:has-text('IA : éteinte')").wait_for()
        etabli.click("#ia-bascule")

        assert carte.locator("[data-role=statut]").inner_text() == "le Club peut le faire"   # l'état AVANT le retrait
        with etabli.expect_response(lambda r: "/console/capacites" in r.url and "DEGRADED" in r.text()) as lu:
            pauline.click("#retirer-delegation_acheteurs")                             # retrait, en un geste
        assert lu.value.ok                                                             # une lecture de l'Établi APRÈS le retrait…
        carte.locator("[data-role=statut]:has-text('un consentement ne vaut plus')").wait_for()   # …et l'écran l'affiche
        texte = etabli.inner_text("body")
        assert "transport : ce composant n'est plus disponible" in texte
        for x in ("Pauline", "Darbellay", "retiré", "s'est retir", "Minibus de 14"):      # ni qui, ni l'événement
            assert x not in texte, x

        _, markus = _telephone(b, url, codes["s14"], (412, 915), erreurs)
        markus.click("nav.onglets >> text=Demandes")
        markus.wait_for_selector("[data-ask]")                                         # la demande repart… vers un autre
        pauline.click("nav.onglets >> text=Demandes")
        pauline.wait_for_selector("text=Aucune demande pour vous en ce moment.")       # …pas vers elle (7 jours de silence après une réponse)
        for pg in (pauline, markus):
            assert _sans_debordement(pg)
        pauline.click("text=Mes données : ce que le Club sait de moi")
        pauline.wait_for_selector("h1:has-text('Mes données')")
        assert "consentement retiré" in pauline.inner_text("main")
    assert not [e for e in erreurs if "favicon" not in e], erreurs


def test_la_capture_sur_echec_sauvegarde_les_pages_ouvertes(url, tmp_path, monkeypatch):  # noqa: F811
    pw = pytest.importorskip("playwright.sync_api")
    from tests import capture_e2e
    monkeypatch.setattr(capture_e2e, "DOSSIER", tmp_path)
    with pytest.raises(AssertionError):
        with pw.sync_playwright() as p:
            b = _chromium(p)
            pg = b.new_page()
            pg.goto(url + "/etabli")
            raise AssertionError("échec volontaire")
    fichiers = sorted(x.suffix for x in tmp_path.rglob("*") if x.is_file())
    assert ".png" in fichiers and ".html" in fichiers


def test_budget_de_noeuds_atteint_l_etabli_le_montre():
    """Budget du compositeur forcé à 1 nœud (HACKVS_BUDGET_NOEUDS) : aucune recherche ne peut aboutir. L'Établi montre
    quand même la capacité, dit « état incertain : recherche bornée atteinte », et la met à l'attention de l'animation,
    avec ses deux actions : relancer (la carte retrouve un vrai statut) ou acquitter (la carte le dit, la file se vide)."""
    pw = pytest.importorskip("playwright.sync_api")
    with serveur(HACKVS_BUDGET_NOEUDS="1") as base, pw.sync_playwright() as p:
        pg = _chromium(p).new_page(viewport={"width": 1440, "height": 900})
        pg.goto(base + "/etabli")
        carte = pg.locator(CARTE)
        carte.locator("[data-role=statut]:has-text('état incertain : recherche bornée atteinte')").wait_for()
        assert "une composition a pu échapper au calcul (absence non garantie)" in carte.inner_text()
        assert "Accueillir une délégation d'acheteurs germanophones (recherche bornée : à vérifier)" in pg.inner_text("#attention")
        # la FILE a des actions : relancer (budget élevé) une capacité, acquitter l'autre
        pg.click("[data-file='delegation_acheteurs'] >> [data-action=relancer]")
        carte.locator("[data-role=statut]:has-text('il manque une pièce')").wait_for()
        assert pg.locator("[data-file='delegation_acheteurs']").count() == 0
        autre = pg.locator("article[data-finalite='presentation_germanophone']")
        pg.click("[data-file='presentation_germanophone'] >> [data-action=acquitter]")
        autre.locator("[data-role=statut]:has-text('acquitté par l')").wait_for()
        assert pg.locator("[data-file]").count() == 0 and "Rien." in pg.inner_text("#attention")


def test_qr_jure_etabli_telephone_usage_unique(url):  # noqa: F811
    """L'Établi montre un QR juré (local, data:) ; le téléphone qui l'ouvre joue Markus (fictif) avec un bandeau et le passe
    quitte l'adresse ; le même passe, rescanné sur un autre téléphone, ne donne rien."""
    pw = pytest.importorskip("playwright.sync_api")
    import json
    import urllib.request
    with pw.sync_playwright() as p:
        b = _chromium(p)
        etabli = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        etabli.goto(url + "/etabli")
        etabli.click("#qr-jure")
        etabli.wait_for_selector("section[aria-label='QR juré'] img[src^='data:image/svg+xml']")
        assert "Valable une seule fois" in etabli.inner_text("[data-role=jure-regle]")
        requete = urllib.request.Request(url + "/api/pulse/console/jure", data=json.dumps({"persona": "s14", "minutes": 15}).encode(),
                                         headers={"X-Pulse-Console": "1", "Content-Type": "application/json"})
        chemin = json.load(urllib.request.urlopen(requete))["url"].split("://", 1)[1].split("/", 1)[1]
        juge = b.new_context(viewport={"width": 390, "height": 844}).new_page()
        juge.goto(f"{url}/{chemin}")
        juge.wait_for_selector("#bandeau-jure:not([hidden])")
        assert "Jury : vous jouez Markus" in juge.inner_text("#bandeau-jure") and "FICTIF" in juge.inner_text("#bandeau-jure")
        assert "jure=" not in juge.url and juge.url.endswith("#demandes")          # le passe a quitté l'adresse
        juge.wait_for_selector("h1:has-text('Demandes du Club')")
        second = b.new_context(viewport={"width": 390, "height": 844}).new_page()
        second.goto(f"{url}/{chemin}")
        second.wait_for_selector(".toast:has-text('déjà été utilisé')")
        assert second.locator("#bandeau-jure").is_hidden()
