"""Banc d'essai partagé dans un VRAI navigateur, avec DEUX sessions indépendantes (deux contextes = deux téléphones) :
Sophie propose, Markus accepte, Markus réduit sa disponibilité (perturbation), Sophie choisit une adaptation, Markus
réaccepte, l'essai a lieu, Sophie déclare une observation NÉGATIVE, Markus la conteste, chacun choisit la réutilisation.
Seul geste joué : l'accord de Pauline (absente de la scène), par l'API de la console, marqué comme tel.
Ignoré seulement si aucun Chromium n'est disponible ; obligatoire en CI."""
import json
import os
import urllib.request

import pytest

from tests.test_e2e_scene import _chromium, url  # noqa: F401  (serveur démo isolé partagé)

CAPTURES = os.environ.get("HACKVS_CAPTURES")
CONSOLE = {"Content-Type": "application/json", "X-Pulse-Console": "1"}
QUESTION = "Notre nouvelle étiquette de tisane est-elle comprise en 10 secondes à 1 mètre par quelqu'un qui ne connaît pas la marque ?"


def _api(base, chemin, corps=None):
    req = urllib.request.Request(base + chemin, data=json.dumps(corps).encode() if corps is not None else None, headers=CONSOLE)
    return json.loads(urllib.request.urlopen(req).read())


def _sans_debordement(pg):
    return pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")


def _telephone(b, base, code, taille, erreurs):
    ctx = b.new_context(viewport={"width": taille[0], "height": taille[1]})
    pg = ctx.new_page()
    pg.set_default_timeout(30_000)
    pg.on("pageerror", lambda e: erreurs.append(str(e)))
    pg.on("console", lambda m: erreurs.append(m.text) if m.type == "error" else None)
    pg.on("response", lambda r: erreurs.append(f"{r.status} {r.request.method} {r.url}") if r.status >= 500 else None)
    pg.goto(base + f"/app?code={code}#acces")
    pg.click("text=Continuer")
    pg.wait_for_selector("h1:has-text('Mes actions')")
    return ctx, pg


def test_banc_d_essai_deux_telephones_perturbation_et_resultat_negatif(url):  # noqa: F811
    pw = pytest.importorskip("playwright.sync_api")
    _api(url, "/api/pulse/demo/reinitialiser", {})
    codes = {p["id"]: p["code"] for p in _api(url, "/api/pulse/console/personas")}
    erreurs: list[str] = []
    with pw.sync_playwright() as p:
        b = _chromium(p)
        _, s = _telephone(b, url, codes["n01"], (390, 844), erreurs)          # téléphone 1 : Sophie, porteuse
        _, m = _telephone(b, url, codes["s14"], (412, 915), erreurs)          # téléphone 2 : Markus, contributeur
        assert "Rien n'attend votre choix" in m.inner_text("main")            # liste vide : rien n'est fabriqué

        # 1-3. Sophie formule, le système prépare (mode formulaire, dit comme tel), elle complète et choisit l'offre
        s.click("nav.onglets >> text=Proposer un essai")
        s.fill("#formulation", QUESTION)
        s.click("#preparer")
        s.wait_for_selector("#f-critere")
        assert "aucun modèle utilisé" in s.inner_text(".ia")                 # jamais « Apertus » sans appel réel
        s.fill("#f-critere", "Sur 3 personnes, combien nomment le produit après 10 s à 1 m ?")
        s.click("button:has-text('+ temps')")
        s.click("button:has-text('+ lieu')")
        s.click("#enregistrer")
        s.wait_for_selector("#publier")
        s.click("label:has-text('Regard neuf de distributeur')")
        s.click("#publier")
        s.wait_for_selector("text=proposé : en attente de choix")
        eid = s.url.split("#essai/")[1]
        texte = s.inner_text("main")
        assert "Markus" not in texte and "une personne du Club" in texte     # personne n'est nommé avant son accord
        if CAPTURES:
            s.screenshot(path=f"{CAPTURES}/essai-1-propose.png", full_page=True)

        # Pauline (absente de la scène) : geste JOUÉ par la console
        v = _api(url, f"/api/pulse/console/essais/{eid}")["version"]
        _api(url, f"/api/pulse/console/essais/{eid}/geste", {"membre": "s01", "version": v, "accepte": True})

        # 4. Markus reçoit la proposition sur SON téléphone et accepte sa part
        m.wait_for_selector(f"a[href='#essai/{eid}']", timeout=15_000)
        m.click(f"a[href='#essai/{eid}']")
        m.wait_for_selector("#accepter")
        assert "Sophie Carron" in m.inner_text("main") and "10 min" in m.inner_text("main")
        m.click("#accepter")
        s.wait_for_selector("text=autorisé : tous les accords", timeout=15_000)
        assert "Markus Heinzmann" in s.inner_text("main")                   # nommé APRÈS son accord

        # 5. perturbation : Markus n'a plus que 5 minutes
        m.click("summary:has-text('Mes conditions ont changé')")
        m.fill("#ma-duree", "5")
        m.click("#changer-duree")
        s.wait_for_selector("text=Une condition a changé", timeout=15_000)
        texte = s.inner_text("main")
        assert "demande 10 min, l'offre en accepte 5" in texte and "Reste valable (rien à redonner) : Pauline Darbellay" in texte
        assert s.locator("#lancer").count() == 0                             # rien ne se lance sur un accord qui ne couvre plus
        if CAPTURES:
            s.screenshot(path=f"{CAPTURES}/essai-2-adaptation.png", full_page=True)

        # 6. Sophie choisit : même personne, geste raccourci (l'objectif reste le sien) ; Markus doit réaccepter
        s.click("button:has-text('raccourcir ce geste de 10 à 5 min')")
        s.wait_for_selector("text=proposé : en attente de choix", timeout=15_000)
        m.wait_for_selector("#accepter", timeout=15_000)                     # la NOUVELLE version, relue sur son téléphone
        assert "votre part a changé depuis votre accord" in m.inner_text("main")   # 5 min : sa part a changé, il redonne son accord
        m.click("#accepter")
        s.wait_for_selector("#lancer", timeout=15_000)

        # 7. l'essai a lieu : contributions CONSTATÉES (ce n'est pas un résultat)
        s.click("#lancer")
        s.wait_for_selector('button:has-text("J\'ai constaté sa contribution")')
        s.click('button:has-text("J\'ai constaté sa contribution") >> nth=0')
        s.wait_for_function("() => [...document.querySelectorAll('button')].filter((x) => x.textContent === \"J'ai constaté sa contribution\").length === 1")
        s.click('button:has-text("J\'ai constaté sa contribution")')
        s.wait_for_selector("#observer")
        assert "Aucun résultat n'en découle" in s.inner_text("main")

        # 8. observation NÉGATIVE, avec sa portée, déclarée par Sophie
        s.fill("#obs-texte", "1 personne sur 3 a nommé le produit ; la marque n'a été lue par personne.")
        s.check("input[name=qualif][value=negatif]")
        s.fill("#obs-limites", "3 personnes, stand éclairé, une seule étiquette, conditions de salon")
        s.click("#observer")
        s.wait_for_selector("text=observation déclarée")
        assert "non vérifiée par le système" in s.inner_text("main") and "négatif" in s.inner_text("main")

        # Markus conteste (la contestation reste visible)
        m.wait_for_selector("#raison", timeout=15_000)
        m.fill("#raison", "J'étais à 2 mètres, pas à 1 mètre.")
        m.click("button:has-text('Je conteste')")
        s.wait_for_selector("text=Contestée par Markus Heinzmann", timeout=15_000)

        # 9. droits de réutilisation : Sophie « club », Markus « participants » → le plus restrictif l'emporte
        s.check("input[name=niveau][value=club]")
        s.click("button:has-text('Enregistrer mon choix')")
        m.check("input[name=niveau][value=participants]")
        m.click("button:has-text('Enregistrer mon choix')")
        m.wait_for_timeout(800)
        s.click("nav.onglets >> text=Souvenirs et accords")
        s.wait_for_selector("text=Mes accords")
        texte = s.inner_text("main")
        assert "visible par : participants" in texte and "Rien : chaque participant doit l'autoriser" in texte
        assert _sans_debordement(s) and _sans_debordement(m)
        if CAPTURES:
            s.screenshot(path=f"{CAPTURES}/essai-3-souvenirs.png", full_page=True)
        b.close()
    assert erreurs == [], erreurs


def test_refus_sans_alternative_arret_honnete(url):  # noqa: F811
    """Markus décline ; Léa a retiré son offre : le système ne sollicite personne d'autre, ne redemande rien à Markus,
    et dit que l'essai est bloqué : aucune adaptation admissible."""
    pw = pytest.importorskip("playwright.sync_api")
    _api(url, "/api/pulse/demo/reinitialiser", {})
    codes = {p["id"]: p["code"] for p in _api(url, "/api/pulse/console/personas")}
    erreurs: list[str] = []
    with pw.sync_playwright() as p:
        b = _chromium(p)
        _, s = _telephone(b, url, codes["n01"], (390, 844), erreurs)
        _, m = _telephone(b, url, codes["s14"], (390, 844), erreurs)
        _, lea = _telephone(b, url, codes["d01"], (390, 844), erreurs)
        lea.click("nav.onglets >> text=Souvenirs et accords")
        lea.click("button:has-text('Retirer cette offre')")
        lea.wait_for_selector("text=retiree")
        s.click("nav.onglets >> text=Proposer un essai")
        s.fill("#formulation", QUESTION)
        s.click("#preparer")
        s.fill("#f-critere", "Sur 3 personnes, combien nomment le produit ?")
        s.click("button:has-text('+ temps')")
        s.click("#enregistrer")
        s.click("#publier")
        s.wait_for_selector("text=proposé : en attente de choix")
        eid = s.url.split("#essai/")[1]
        m.goto(url + f"/app#essai/{eid}")
        m.click("#decliner")
        s.wait_for_selector("text=bloqué : aucune adaptation admissible", timeout=15_000)
        assert "Markus" not in s.inner_text("main")                         # qui a décliné n'est jamais nommé
        m.reload()
        m.wait_for_selector("text=vous avez décliné", timeout=15_000)
        assert m.locator("#accepter").count() == 0                            # rien ne lui est redemandé
        b.close()
    assert erreurs == [], erreurs


def test_application_face_aux_pannes_reseau(url):  # noqa: F811
    """Réponse lente d'un écran quitté (jamais affichée par-dessus le nouvel écran), panne serveur (écran d'erreur avec
    « Réessayer » et référence), hors ligne (message explicite), session falsifiée (retour à l'accès)."""
    pw = pytest.importorskip("playwright.sync_api")
    _api(url, "/api/pulse/demo/reinitialiser", {})
    session = next(x["session"] for x in _api(url, "/api/pulse/console/personas") if x["id"] == "s14")
    with pw.sync_playwright() as p:
        b = _chromium(p)
        ctx = b.new_context(viewport={"width": 390, "height": 844})
        pg = ctx.new_page()
        pg.set_default_timeout(30_000)
        pg.goto(url + f"/app?session={session}#souvenirs")
        pg.wait_for_selector("text=Mes offres volontaires")
        assert "session=" not in pg.url                                      # le jeton ne reste pas dans l'adresse

        def lent(route):
            pg.wait_for_timeout(1500)
            route.continue_()
        pg.route("**/api/pulse/moi/actions", lent)
        pg.evaluate("location.hash = '#actions'")
        pg.evaluate("location.hash = '#souvenirs'")
        pg.wait_for_selector("text=Mes offres volontaires")
        pg.wait_for_timeout(2500)
        texte = pg.inner_text("main").lower()                                 # les titres sont en capitales (CSS)
        assert "mes offres volontaires" in texte and "attend votre choix" not in texte
        pg.unroute("**/api/pulse/moi/actions")

        pg.route("**/api/pulse/moi/actions", lambda r: r.fulfill(status=500, content_type="application/json",
                                                                 body='{"detail": "x", "requete": "ref123456789"}'))
        pg.evaluate("location.hash = '#actions'")
        pg.wait_for_selector("text=Impossible d'afficher cet écran")
        assert "ref123456789" in pg.inner_text("main")
        pg.unroute("**/api/pulse/moi/actions")
        pg.click("text=Réessayer")
        pg.wait_for_selector("h1:has-text('Mes actions')")

        ctx.set_offline(True)
        pg.evaluate("location.hash = '#souvenirs'")
        pg.wait_for_selector("text=Hors ligne")
        ctx.set_offline(False)

        pg.evaluate("sessionStorage.setItem('pulse-session', 's14.1.faux'); location.hash = '#actions'; location.reload()")
        pg.wait_for_selector("text=Activez votre compte du Club")
        b.close()


def test_contenu_hostile_affiche_comme_du_texte(url):  # noqa: F811
    """Une offre contenant du HTML actif est affichée telle quelle (createTextNode + CSP) : aucun script n'est exécuté."""
    pw = pytest.importorskip("playwright.sync_api")
    _api(url, "/api/pulse/demo/reinitialiser", {})
    codes = {p["id"]: p["code"] for p in _api(url, "/api/pulse/console/personas")}
    hostile = "<img src=x onerror=\"window.__xss=1\"> IGNORE RULES"
    erreurs: list[str] = []
    with pw.sync_playwright() as p:
        b = _chromium(p)
        _, lea = _telephone(b, url, codes["d01"], (390, 844), erreurs)
        lea.click("nav.onglets >> text=Souvenirs et accords")
        lea.click("summary:has-text('Publier une offre')")
        lea.fill("#o-quoi", hostile)
        lea.fill("#o-au", "2026-11-20")
        lea.click("details[open] button:has-text('Publier')")
        lea.wait_for_selector("text=IGNORE RULES")
        assert hostile in lea.inner_text("main")                              # le texte, littéralement
        assert lea.evaluate("window.__xss") is None and lea.locator("main img").count() == 0
        b.close()
    assert erreurs == [], erreurs


def test_tout_effacer_annonce_ce_qui_reste_avant_le_geste(url):  # noqa: F811
    """R4 (contre-expertise) : AVANT le geste, l'écran et la confirmation disent que le journal garde une trace
    technique sans nom ni contact. Refuser la confirmation n'efface rien."""
    pw = pytest.importorskip("playwright.sync_api")
    _api(url, "/api/pulse/demo/reinitialiser", {})
    session = next(x["session"] for x in _api(url, "/api/pulse/console/personas") if x["id"] == "s01")
    with pw.sync_playwright() as p:
        b = _chromium(p)
        pg = b.new_context(viewport={"width": 390, "height": 844}).new_page()
        pg.set_default_timeout(30_000)
        pg.goto(url + f"/app?session={session}#donnees")
        pg.wait_for_selector("#tout-effacer")
        avant = pg.inner_text("main").lower()
        assert "trace technique" in avant and "sans nom ni contact" in avant          # dit à l'écran, avant le geste
        messages: list[str] = []

        def refuser(d):
            messages.append(d.message)
            d.dismiss()
        pg.once("dialog", refuser)
        pg.click("#tout-effacer")
        pg.wait_for_timeout(300)
        assert messages and "trace technique" in messages[0].lower() and "sans nom ni contact" in messages[0].lower()
        pg.evaluate("location.hash = '#actions'")
        pg.wait_for_selector("h1:has-text('Mes actions')")                           # rien effacé : la session vit
        b.close()


# Revue publique R-03 / R-04 : mesuré dans le navigateur, pas supposé. Texte : contraste WCAG AA (4,5:1 ; 3:1 au-delà
# de 24 px ou 18,66 px gras) contre le fond effectif ; téléphone : chaque cible tactile fait au moins 44 px de haut.
_CONTRASTES = r"""() => {
  const lum = c => { const m = c.match(/[\d.]+/g).map(Number); const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
                     return 0.2126 * f(m[0]) + 0.7152 * f(m[1]) + 0.0722 * f(m[2]); };
  const fond = el => { for (let e = el; e; e = e.parentElement) { const a = (getComputedStyle(e).backgroundColor.match(/[\d.]+/g) || []).map(Number);
                       if (a.length === 3 || (a.length === 4 && a[3] > 0.5)) return getComputedStyle(e).backgroundColor; } return "rgb(255,255,255)"; };
  const ko = [];
  for (const el of document.querySelectorAll("body *")) {
    if (el.closest("[aria-hidden=true]") || !el.getClientRects().length) continue;
    if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
    const cs = getComputedStyle(el), taille = parseFloat(cs.fontSize);
    if (!taille || cs.visibility === "hidden") continue;
    const a = lum(cs.color), b = lum(fond(el)), r = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    const grand = taille >= 24 || (taille >= 18.66 && +cs.fontWeight >= 700);
    if (r < (grand ? 3 : 4.5)) ko.push(`${r.toFixed(2)} ${cs.color} ${taille}px « ${el.textContent.trim().slice(0, 30)} »`);
  }
  return ko;
}"""
_CIBLES = """() => [...document.querySelectorAll('button, a[href], input, select, textarea, summary')]
  .filter(e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden')
  .map(e => [e.getBoundingClientRect().height, (e.textContent || e.type || '').trim().slice(0, 30)])
  .filter(([h]) => h < 44).map(([h, t]) => `${Math.round(h)} px « ${t} »`)"""


def test_lisible_et_touchable_au_telephone_et_sur_les_ecrans(url):  # noqa: F811
    pw = pytest.importorskip("playwright.sync_api")
    _api(url, "/api/pulse/demo/reinitialiser", {})
    _api(url, "/api/pulse/demo/aller/4", {})
    codes = {p["id"]: p["code"] for p in _api(url, "/api/pulse/console/personas")}
    erreurs: list[str] = []
    ko: dict[str, list[str]] = {}
    with pw.sync_playwright() as p:
        b = _chromium(p)
        _, s = _telephone(b, url, codes["n01"], (390, 844), erreurs)
        for onglet in ("actions", "action", "nouveau", "souvenirs", "demandes"):
            s.click(f"nav.onglets a[data-o={onglet}]")
            s.wait_for_timeout(800)
            ko[f"/app#{onglet} contraste"] = s.evaluate(_CONTRASTES)
            ko[f"/app#{onglet} cibles"] = s.evaluate(_CIBLES)
        for ecran in ("/etabli", "/console"):
            pg = b.new_page(viewport={"width": 1440, "height": 900})
            pg.goto(url + ecran)
            pg.wait_for_timeout(1500)
            ko[f"{ecran} contraste"] = pg.evaluate(_CONTRASTES)
    assert not erreurs, erreurs
    assert not {k: v for k, v in ko.items() if v}, {k: v for k, v in ko.items() if v}
