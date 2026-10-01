"""Revue publique R-02 — un limiteur ne doit pas devenir la panne qu'il prévient.

Avant : chaque clé jamais vue (un préfixe de passe juré inventé, un code d'invitation tenté) créait une file conservée pour
toujours, et `POST /api/pulse/jure` n'avait AUCUN plafond global — un client non authentifié faisait croître la mémoire
du serveur sans borne, à la vitesse de ses requêtes. Données FICTIVES."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.pulse_api import Limiteur, creer_routeur
from app.taxonomy import charger_taxonomie
from intelligence.erreurs import Limite

TAX = charger_taxonomie()


class Horloge:
    def __init__(self):
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def test_les_cles_dont_la_fenetre_est_passee_sont_oubliees():
    h = Horloge()
    lim = Limiteur(5, 60.0, horloge=h)
    for i in range(10_000):                       # 10 000 clés distinctes inventées par un client
        lim.verifier(f"jure-code|{i}")
    h.t = 61.0                                    # la fenêtre est passée pour toutes
    lim.verifier("jure-code|neuve")
    assert len(lim._traces) <= 1, len(lim._traces)


def test_oublier_ne_rouvre_pas_une_cle_encore_freinee():
    """Contre-épreuve : la purge ne touche qu'aux clés dont toutes les traces sont sorties de la fenêtre."""
    h = Horloge()
    lim = Limiteur(2, 60.0, horloge=h)
    lim.verifier("a"); lim.verifier("a")                                    # noqa: E702
    for i in range(5_000):
        h.t = 30.0
        lim.verifier(f"autre|{i}")
    with pytest.raises(Limite):                                            # « a » reste freinée dans sa fenêtre
        lim.verifier("a")


def test_le_passe_jure_a_un_plafond_global_comme_l_acces():
    app = FastAPI()
    app.include_router(creer_routeur(TAX))
    c = TestClient(app)
    statuts = [c.post("/api/pulse/jure", json={"jeton": f"N{i:09d}.1.x.y"}).status_code for i in range(310)]
    assert statuts[:300].count(401) == 300 and statuts[300:] == [429] * 10, statuts[295:]
