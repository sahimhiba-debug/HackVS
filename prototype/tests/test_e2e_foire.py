"""FOIRE 2026 dans un VRAI navigateur, interrupteur ALLUMÉ (serveur propre à ce fichier) : le scénario du juré.
La console (/suivi) affiche le QR du stand → le juré ouvre le lien sur « son » téléphone → déclare « Exposant invité
d'Annecy » (traiteur, Haute-Savoie) et reçoit son reçu → propose son aide sur une demande → « Rejoindre le Club » →
« prévu ensuite ». Le Suivi compte l'invité (« < 3 ») sans jamais afficher le nom déclaré. Données FICTIVES."""
import pytest

from tests.test_e2e_pulse import _sans_debordement
from tests.test_e2e_scene import _chromium, serveur


@pytest.fixture(scope="module")
def url_foire():
    with serveur(HACKVS_FOIRE="1") as base:
        yield base


def test_le_jure_devient_exposant_invite_d_annecy(url_foire):
    from playwright.sync_api import sync_playwright
    erreurs: list[str] = []
    with sync_playwright() as p:
        b = _chromium(p)
        console = b.new_context(viewport={"width": 1366, "height": 860}).new_page()
        console.set_default_timeout(30_000)
        console.on("pageerror", lambda e: erreurs.append(str(e)))
        console.goto(url_foire + "/suivi")
        console.locator("[data-role=monde]:has-text('monde de démonstration')").wait_for()
        console.locator("[data-tuile='Demandes envoyées']").wait_for()
        assert console.locator("[data-tuile='Nouveaux liens tissés']").count() == 1
        console.click("#qr-stand")
        console.locator("[data-role=qr-decouverte] img").wait_for()
        lien = console.locator("[data-role=qr-decouverte] a").get_attribute("href")
        assert lien and "/decouverte#passe=" in lien

        tel = b.new_context(viewport={"width": 390, "height": 844}).new_page()
        tel.set_default_timeout(30_000)
        tel.on("pageerror", lambda e: erreurs.append(str(e)))
        tel.goto(lien)
        tel.locator("#entreprise").wait_for()
        assert "passe=" not in tel.url                                  # le passe ne reste pas dans l'adresse
        assert "monde de démonstration" in tel.inner_text("header")
        tel.fill("#entreprise", "Exposant invité d'Annecy")
        tel.select_option("#metier", "traiteur")
        tel.select_option("#zone", "Haute-Savoie")
        tel.click("#declarer")
        tel.locator("[data-role=recu]:has-text('90 jours')").wait_for()
        tel.locator("[data-demande] >> text=Je peux aider").first.click()
        tel.locator("[data-role=message]:has-text('Proposition transmise')").wait_for()
        tel.click("#rejoindre")
        tel.locator("[data-role=prevu]:has-text('simulé en démonstration')").wait_for()
        tel.click("#langue")
        tel.locator("h1:has-text('Den Club kennenlernen')").wait_for()
        assert _sans_debordement(tel)

        tel2 = b.new_context().new_page()                               # le même lien, rescanné : rien
        tel2.goto(lien)
        tel2.locator("[data-role=invalide]").wait_for()

        console.locator("[data-passe] >> text=intention d'adhésion").wait_for()
        console.locator("[data-tuile='Invités ayant contribué'] .n:has-text('< 3')").wait_for()
        assert "Annecy" not in console.inner_text("body") and "Exposant" not in console.inner_text("body")
        assert "null" not in console.inner_text("#suivi") and "undefined" not in console.inner_text("body")
        console.click("#vues >> text=Le Club cherche")                   # E : les demandes sans réponse, par métier
        console.locator("[data-role=propose]").first.wait_for()          # le manque comblé par l'invité, à confirmer
        console.locator("[data-metier] [data-inviter]").first.click()
        console.locator("[data-role=invitation] textarea[data-langue=DE]").wait_for()
        assert "/decouverte#passe=" in console.input_value("[data-role=invitation] textarea[data-langue=FR]")
        assert "ohne Mitgliedschaft" in console.input_value("[data-role=invitation] textarea[data-langue=DE]")
        b.close()
    assert not erreurs, erreurs


def test_membre_a_distance_repond_depuis_l_e_mail_simule(url_foire):
    """F : Markus déclare « Haut-Valais, Deutsch » sur son téléphone → la boîte de sortie (simulé en démonstration)
    montre l'e-mail en allemand avec trois liens → « Diesmal nicht » s'ouvre sur la page de réponse, confirme, et le
    même lien rouvert ne vaut plus."""
    from playwright.sync_api import sync_playwright
    from tests.test_e2e_pulse import _api, _telephone
    erreurs: list[str] = []
    _api(url_foire, "/api/pulse/demo/reinitialiser", {})
    codes = {x["id"]: x["code"] for x in _api(url_foire, "/api/pulse/console/personas")}
    with sync_playwright() as p:
        b = _chromium(p)
        _, tel = _telephone(b, url_foire, codes["s14"], (390, 844), erreurs)
        tel.goto(url_foire + "/app#donnees")
        tel.locator("#dist-zone").wait_for()
        tel.select_option("#dist-zone", "Haut-Valais")
        tel.select_option("#dist-langue", "de")
        tel.click("#dist-enregistrer")
        tel.locator(".toast:has-text('Enregistré')").wait_for()
        assert _api(url_foire, "/api/pulse/console/boite")["courriels"], "la déclaration n'a pas produit d'e-mail"
        console = b.new_context(viewport={"width": 1366, "height": 860}).new_page()
        console.set_default_timeout(30_000)
        console.on("pageerror", lambda e: erreurs.append(str(e)))
        console.goto(url_foire + "/suivi")
        console.click("#vues >> text=Boîte de sortie")
        console.locator("[data-role=simule]:has-text('simulé en démonstration')").wait_for()
        console.locator("[data-courriel=de] >> text=Der Club fragt Sie").wait_for()
        assert "[object" not in console.inner_text("#vue-boite")
        lien = console.locator("[data-courriel=de] [data-lien='Diesmal nicht']").get_attribute("href")
        rep = b.new_context(viewport={"width": 390, "height": 844}).new_page()
        rep.on("pageerror", lambda e: erreurs.append(str(e)))
        rep.goto(lien)
        rep.locator("h1:has-text('Diesmal nicht')").wait_for()
        assert "lien=" not in rep.url
        rep.click("#confirmer")
        rep.locator("[data-role=fait]").wait_for()
        rep2 = b.new_context().new_page()
        rep2.goto(lien)
        rep2.locator("[data-role=erreur]").wait_for()
        b.close()
    assert not erreurs, erreurs


def test_visible_par_le_club_double_accord_depuis_le_telephone(url_foire):
    """B : Pauline coche « Visible par le Club » sur SON reçu ; le Club l'a permis aussi → une ligne nominative apparaît
    dans Suivi ; elle décoche → la ligne disparaît."""
    import json
    import urllib.request
    from playwright.sync_api import sync_playwright
    from tests.test_e2e_pulse import _api, _telephone
    erreurs: list[str] = []
    _api(url_foire, "/api/pulse/demo/reinitialiser", {})
    codes = {x["id"]: x["code"] for x in _api(url_foire, "/api/pulse/console/personas")}
    with sync_playwright() as p:
        b = _chromium(p)
        _, tel = _telephone(b, url_foire, codes["s01"], (390, 844), erreurs)
        session = tel.evaluate("sessionStorage.getItem('pulse-session') || localStorage.getItem('pulse-session')")
        h = {"X-Pulse-Session": session, "Content-Type": "application/json"}
        ask = json.load(urllib.request.urlopen(urllib.request.Request(url_foire + "/api/pulse/moi/asks", headers=h)))[0]["id"]
        urllib.request.urlopen(urllib.request.Request(f"{url_foire}/api/pulse/moi/asks/{ask}/reponse", method="POST", headers=h,
                                                      data=json.dumps({"oui": True, "attributs": {"places": 14}}).encode()))
        ref = json.load(urllib.request.urlopen(urllib.request.Request(url_foire + "/api/pulse/moi/consentements", headers=h)))[0]["reference"]
        _api(url_foire, f"/api/pulse/console/recus/{ref}/visible", {"visible": True})
        assert _api(url_foire, "/api/pulse/console/suivi")["nominatif"] == []
        tel.goto(url_foire + "/app#donnees")
        tel.locator(f"[data-visible='{ref}']").check()
        tel.wait_for_timeout(500)
        assert len(_api(url_foire, "/api/pulse/console/suivi")["nominatif"]) == 1
        tel.locator(f"[data-visible='{ref}']").uncheck()
        tel.wait_for_timeout(500)
        assert _api(url_foire, "/api/pulse/console/suivi")["nominatif"] == []
        b.close()
    assert not erreurs, erreurs


def test_la_carte_devient_le_profil_formulaire_sans_ia(url_foire):
    """Parité : IA éteinte (serveur d'E2E sans modèle), le même écran propose le formulaire ; confirmer donne un reçu."""
    from playwright.sync_api import sync_playwright
    from tests.test_e2e_pulse import _api, _telephone
    erreurs: list[str] = []
    _api(url_foire, "/api/pulse/demo/reinitialiser", {})
    codes = {x["id"]: x["code"] for x in _api(url_foire, "/api/pulse/console/personas")}
    with sync_playwright() as p:
        b = _chromium(p)
        _, tel = _telephone(b, url_foire, codes["s01"], (390, 844), erreurs)
        tel.goto(url_foire + "/app#donnees")
        tel.locator("#carte-photo").set_input_files(files=[{"name": "carte.png", "mimeType": "image/png",
                                                             "buffer": __import__("base64").b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==")}])
        tel.locator("[data-role=carte-formulaire]").wait_for()                 # IA ou non : le même formulaire, à confirmer
        tel.fill("#carte-entreprise", "Tisanes Alpines Fictives")
        tel.select_option("#carte-metier", "agriculture")
        tel.click("#carte-confirmer")
        tel.locator("[data-role=carte-recu]:has-text('pas conservée')").wait_for()
        b.close()
    assert not erreurs, erreurs


def test_ce_que_votre_club_pourrait_assembler(url_foire):
    """Liste du Club : 8 sur 9, la délégation germanophone manque l'interprète ; aucun nom ; « < 3 » pour les rares."""
    from playwright.sync_api import sync_playwright
    erreurs: list[str] = []
    with sync_playwright() as p:
        b = _chromium(p)
        console = b.new_context(viewport={"width": 1366, "height": 860}).new_page()
        console.set_default_timeout(30_000)
        console.on("pageerror", lambda e: erreurs.append(str(e)))
        console.goto(url_foire + "/suivi")
        console.click("#vues [data-vue=assembler]")
        console.locator("[data-role=assemblables]:has-text('8 sur 9')").wait_for()
        assert console.locator("[data-capacite=delegation][data-assemblable=false]").inner_text().count("manque : interprète") == 1
        assert "classification à confirmer" in console.inner_text("#assembler-source")
        assert "< 3 entreprises" in console.inner_text("[data-role=cherche-liste]")
        assert "Club Pulse dit ce qu'il peut faire cette semaine" in console.inner_text("[data-role=phrase]")
        texte = console.inner_text("body")
        assert "null" not in texte and "undefined" not in texte
        b.close()
    assert erreurs == []


def test_interface_allemande_selon_la_langue_preferee(url_foire):
    """P3 n°5 : Pauline déclare « de » → l'interface passe en allemand (Ja / Nein / Diesmal nicht), bandeau « à relire »."""
    from playwright.sync_api import sync_playwright
    from tests.test_e2e_pulse import _api, _telephone
    erreurs: list[str] = []
    _api(url_foire, "/api/pulse/demo/reinitialiser", {})
    codes = {x["id"]: x["code"] for x in _api(url_foire, "/api/pulse/console/personas")}
    with sync_playwright() as p:
        b = _chromium(p)
        _, tel = _telephone(b, url_foire, codes["s01"], (390, 844), erreurs)
        tel.goto(url_foire + "/app#donnees")
        tel.locator("#dist-langue").select_option("de")
        tel.click("#dist-enregistrer")
        tel.locator("text=Gespeichert.").or_(tel.locator("text=Enregistré.")).first.wait_for()
        tel.goto(url_foire + "/app#demandes")
        tel.reload()                                                        # la langue se lit au chargement
        tel.locator("[data-role=traduction]").wait_for()
        assert "zu prüfen" in tel.inner_text("[data-role=traduction]") and "à relire" in tel.inner_text("[data-role=traduction]")
        tel.locator("button:has-text('Ja')").first.wait_for()
        texte = tel.inner_text("body")
        assert "Diesmal nicht" in texte and "Anfragen" in texte
        assert tel.evaluate("document.documentElement.lang") == "de"
        tel.goto(url_foire + "/app?lang=fr#demandes")                      # l'adresse peut forcer le français
        tel.locator("button:has-text('Oui')").first.wait_for()
        assert tel.locator("[data-role=traduction]").count() == 0
        b.close()
    assert erreurs == [], erreurs


def test_annonce_sous_chiffre_accord_mutuel_dans_deux_navigateurs(url_foire):
    """P3 n°9 : Pauline publie sous chiffre ; Markus dit son intérêt sans voir l'auteur ; Pauline accepte ; chacun voit l'autre."""
    from playwright.sync_api import sync_playwright
    from tests.test_e2e_pulse import _api, _telephone
    erreurs: list[str] = []
    _api(url_foire, "/api/pulse/demo/reinitialiser", {})
    per = {x["id"]: x for x in _api(url_foire, "/api/pulse/console/personas")}
    with sync_playwright() as p:
        b = _chromium(p)
        _, pauline = _telephone(b, url_foire, per["s01"]["code"], (390, 844), erreurs)
        _, markus = _telephone(b, url_foire, per["s14"]["code"], (390, 844), erreurs)
        pauline.goto(url_foire + "/app#donnees")
        pauline.fill("#annonce-texte", "Cherche un local de stockage à Martigny, 20 m², 3 mois.")
        pauline.click("#annonce-publier")
        pauline.locator("[data-mienne='A-001']").wait_for()
        markus.goto(url_foire + "/app#donnees")
        carte = markus.locator("[data-annonce='A-001']")
        carte.wait_for()
        assert per["s01"]["nom"] not in markus.inner_text("#annonces")
        carte.locator("button:has-text('intéressé')").click()
        markus.locator("text=Intérêt transmis").wait_for()
        pauline.reload()
        pauline.locator("[data-accepter='1']").click()
        pauline.locator(f"text={per['s14']['nom']}").wait_for()
        markus.reload()
        markus.locator(f"[data-annonce='A-001'] >> text={per['s01']['nom']}").wait_for()
        b.close()
    assert erreurs == [], erreurs
