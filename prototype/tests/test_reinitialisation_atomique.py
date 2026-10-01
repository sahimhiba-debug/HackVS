"""F28 — une réinitialisation (ou un « aller à l'étape n ») de la console est ATOMIQUE : elle attend que les requêtes en
vol se terminent, les nouvelles attendent qu'elle finisse, et plus rien de l'ancien monde n'est écrit dans le nouveau.
Avant (expérience E4) : avec un journal fichier, l'écriture tardive d'une requête de l'ancien monde atterrissait dans
le journal du monde neuf ; la session était vérifiée dans un monde et la commande exécutée dans un autre.
Entrelacement DÉTERMINISTE : la requête du membre est bloquée au milieu de sa commande. Données FICTIVES."""
import threading
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.pulse_api import creer_routeur
from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.club_pulse import ClubPulse

TAX = charger_taxonomie()
CONSOLE = {"X-Pulse-Console": "1"}


def test_la_reinitialisation_attend_la_requete_en_vol_et_le_monde_neuf_reste_vierge(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    monkeypatch.setenv("HACKVS_SECRET", "un-secret-de-test-assez-long-pour-32-octets!")
    app = FastAPI()
    app.include_router(creer_routeur(TAX))
    client = TestClient(app)
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    h = {"X-Pulse-Session": next(p["session"] for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()
                                 if p["id"] == md.LEA)}

    dans_la_commande, relacher = threading.Event(), threading.Event()
    original = ClubPulse.modifier_profil

    def bloquee(self, *a, **k):                       # la commande du membre s'arrête AU MILIEU (après sa lecture)
        dans_la_commande.set()
        assert relacher.wait(10)
        return original(self, *a, **k)
    monkeypatch.setattr(ClubPulse, "modifier_profil", bloquee)

    resultats: dict = {}
    membre = threading.Thread(target=lambda: resultats.__setitem__(
        "membre", client.patch("/api/pulse/moi/profil", headers=h, json={"disponible": False}).status_code))
    console = threading.Thread(target=lambda: resultats.__setitem__(
        "reinit", client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE).status_code))
    membre.start()
    assert dans_la_commande.wait(10)
    console.start()
    time.sleep(0.5)
    assert console.is_alive(), "la réinitialisation n'a pas attendu la requête en vol"
    relacher.set()
    membre.join(10)
    console.join(10)
    assert resultats == {"membre": 200, "reinit": 200}

    monkeypatch.setattr(ClubPulse, "modifier_profil", original)
    journal = client.get("/api/pulse/console/essais", headers=CONSOLE)       # le monde neuf répond
    assert journal.status_code == 200
    import sqlite3
    with sqlite3.connect(tmp_path / "journal.db") as db:
        types = [t for (t,) in db.execute("SELECT json_extract(donnees, '$.type') FROM evenements")]
    assert "PROFIL" not in types, "une écriture de l'ancien monde est dans le journal du nouveau"


def test_un_monde_remplace_refuse_toute_ecriture():
    """Défense en profondeur : le journal d'un monde remplacé est FERMÉ — une écriture égarée lève, elle n'atterrit
    nulle part (jamais dans le monde neuf)."""
    from plateforme.memoire import Memoire, MondeRemplace
    m = Memoire()
    m.fermer()
    from datetime import date

    from plateforme.affirmations import Statut
    from plateforme.memoire import Evt
    with pytest.raises(MondeRemplace):
        m.ajouter(Evt(type="X", le=date(2026, 10, 6), statut=Statut.OBSERVE))
