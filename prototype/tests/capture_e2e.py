"""CAPTURE D'ARTEFACTS SUR ÉCHEC des tests de bout en bout : quand un test échoue DANS un bloc `sync_playwright()`, chaque
page encore ouverte de chaque navigateur lancé par `_chromium` est sauvegardée — capture d'écran pleine page + HTML —
dans `var/e2e_echecs/<test>/` (ou `$HACKVS_E2E_ECHECS`), AVANT la fermeture du navigateur. La CI les publie comme
artefacts. Branché une seule fois (conftest) pour tous les tests E2E, sans toucher à leur corps.

HERMÉTISME : chaque contexte de ces navigateurs est SURVEILLÉ ; toute requête vers un autre hôte que 127.0.0.1 /
localhost est notée (le navigateur ne la résout pas : voir `tests/test_e2e_scene._lancer`), et le test qui l'a émise
ÉCHOUE à la sortie de `sync_playwright()`, même si sa page s'est affichée."""
from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlsplit

OUVERTS: list = []
EXTERNES: list[str] = []
LOCAUX = {"127.0.0.1", "localhost"}
# Chromium ne résout que les hôtes locaux : un domaine externe échoue au lieu de charger
REGLES_RESOLUTION = "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1, EXCLUDE localhost"
DOSSIER = Path(os.environ.get("HACKVS_E2E_ECHECS") or Path(__file__).resolve().parents[1] / "var" / "e2e_echecs")


def enregistrer(navigateur):
    OUVERTS.append(navigateur)
    nouveau_contexte, nouvelle_page = navigateur.new_context, navigateur.new_page

    def new_context(*a, **k):
        return surveiller(nouveau_contexte(*a, **k))

    def new_page(*a, **k):
        page = nouvelle_page(*a, **k)
        surveiller(page.context)
        return page
    navigateur.new_context, navigateur.new_page = new_context, new_page
    return navigateur


def surveiller(contexte):
    def noter(requete):
        u = urlsplit(requete.url)
        if u.scheme in ("http", "https", "ws", "wss") and u.hostname not in LOCAUX:
            EXTERNES.append(requete.url)
    contexte.on("request", noter)
    return contexte


def externes_tentees() -> list[str]:
    return list(EXTERNES)


def verifier_hermetique() -> None:
    tentees, EXTERNES[:] = sorted(set(EXTERNES)), []
    if tentees:
        raise AssertionError(f"E2E non hermétique : requêtes vers l'extérieur tentées {tentees}")


def capturer(nom_test: str) -> list[Path]:
    dossier = DOSSIER / re.sub(r"[^\w.-]+", "_", nom_test)[:120]
    ecrits: list[Path] = []
    for b, navigateur in enumerate(OUVERTS):
        try:
            contextes = navigateur.contexts
        except Exception:                                        # navigateur déjà fermé : rien à capturer
            continue
        for c, ctx in enumerate(contextes):
            for n, page in enumerate(ctx.pages):
                base = dossier / f"n{b}-c{c}-p{n}"
                try:
                    dossier.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(base.with_suffix(".png")), full_page=True)
                    base.with_suffix(".html").write_text(page.content(), encoding="utf-8")
                    base.with_suffix(".url.txt").write_text(page.url, encoding="utf-8")
                    ecrits += [base.with_suffix(".png"), base.with_suffix(".html")]
                except Exception as e:                           # une page morte n'empêche pas de capturer les autres
                    (dossier / f"n{b}-c{c}-p{n}.erreur.txt").write_text(repr(e), encoding="utf-8")
    OUVERTS.clear()
    return ecrits


def installer() -> None:
    """Enveloppe la sortie de `sync_playwright()` : sur exception, capturer d'abord, fermer ensuite."""
    try:
        from playwright.sync_api._context_manager import PlaywrightContextManager
    except ImportError:                                          # Playwright absent : les E2E se signalent eux-mêmes
        return
    if getattr(PlaywrightContextManager.__exit__, "_capture_e2e", False):
        return
    sortie = PlaywrightContextManager.__exit__

    def __exit__(self, *exc):
        echec = bool(exc) and exc[0] is not None
        if echec:
            capturer((os.environ.get("PYTEST_CURRENT_TEST") or "hors-pytest").split(" ")[0])
        OUVERTS.clear()
        r = sortie(self, *exc)
        if echec:
            EXTERNES.clear()                                     # l'échec d'origine prime
        else:
            verifier_hermetique()
        return r
    __exit__._capture_e2e = True  # type: ignore[attr-defined]
    PlaywrightContextManager.__exit__ = __exit__  # type: ignore[method-assign]
