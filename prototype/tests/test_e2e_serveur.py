"""Le serveur des tests de bout en bout (`tests/test_e2e_scene.serveur`) : déclaré prêt dès qu'il répond, et un serveur
qui NE DÉMARRE PAS est une erreur immédiate et claire — jamais 20 s d'attente aveugle suivies d'échecs trompeurs.
(F03 : la sonde interrogeait `/api/stage`, hors du périmètre servi depuis la Phase 1 : 404, pris pour « pas prêt ».)"""
import time

import pytest

from tests.test_e2e_scene import serveur


def test_un_serveur_sain_est_pret_en_quelques_secondes():
    t = time.perf_counter()
    with serveur():
        pret = time.perf_counter() - t
    assert pret < 10, f"prêt après {pret:.1f} s"


def test_un_serveur_qui_ne_demarre_pas_est_une_erreur_claire():
    t = time.perf_counter()
    with pytest.raises(RuntimeError, match="serveur de démonstration non démarré"):
        with serveur(HACKVS_SECRET="trop-court"):                     # Reglages refuse un secret < 32 caractères
            pass
    assert time.perf_counter() - t < 15


def test_le_serveur_e2e_tourne_dans_la_configuration_du_produit():
    """Les E2E testent le produit tel qu'il est servi : SANS l'ancien prototype (drapeau éteint), même si la suite en
    processus l'allume (conftest). Sinon un chemin bloqué par le périmètre en réalité passerait en E2E."""
    import urllib.error
    import urllib.request
    with serveur() as base:
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(base + "/api/etat", timeout=5)          # route de l'ancien prototype
        assert e.value.code == 404
        assert urllib.request.urlopen(base + "/etabli", timeout=5).status == 200
