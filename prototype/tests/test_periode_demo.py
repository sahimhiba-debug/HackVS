"""La démonstration se passe PENDANT la Foire du Valais 2026 (2–11 octobre) — pas seulement à l'affichage : l'horloge,
les données préparées, la compréhension de « jeudi », le créneau calculé, les événements du journal et l'écran commun
utilisent la même période. Défaut trouvé à l'audit (2026-09-30) : le monde vivait au 03.11 et « la Foire » au 05.11.
Données FICTIVES."""
import json
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.demo import BESOIN_SOPHIE, Demo, jour_foire

TAX = charger_taxonomie()
DEBUT, FIN = date(2026, 10, 2), date(2026, 10, 11)


def test_horloge_donnees_et_scenario_dans_la_foire():
    d = Demo(TAX)
    c = d.club
    assert (md.FOIRE_DEBUT, md.FOIRE_FIN) == (DEBUT, FIN)
    assert DEBUT <= c.jour <= FIN and DEBUT <= jour_foire(c) <= FIN and jour_foire(c).weekday() == 3     # un jeudi
    # données préparées : chaque horaire déclaré tombe pendant la Foire
    plages = [pl for o in c.banc.offres() for pl in o.plages]
    assert plages and all(DEBUT <= pl.jour <= FIN for pl in plages)
    # le texte du membre (« jeudi après-midi ») est compris comme le jeudi de la Foire, par l'horloge du monde
    prop = c.preparer_action(md.SOPHIE, BESOIN_SOPHIE)
    assert prop["fenetre"]["jour"] == jour_foire(c).isoformat()
    # le scénario complet : le créneau, l'échéance et chaque fait du journal restent dans la Foire (sauf l'étape
    # « +30 jours », annoncée comme SIMULÉE, qui est la seule à en sortir)
    d.rejouer(len(Demo.ETAPES) - 1)
    eid = d.ctx["essai"]
    p = c.banc.protocole(eid) if d.club is c else d.club.banc.protocole(eid)
    assert DEBUT <= p.creneau.jour <= FIN and DEBUT <= p.echeance <= FIN
    assert all(DEBUT <= e.le <= FIN for e in d.club.banc.m.evenements())


def test_le_passe_du_monde_est_anterieur_a_son_present():
    """Aucune rencontre, aucune mise à jour de profil n'est datée APRÈS le jour courant du monde."""
    brut = json.loads((Path(md.__file__).resolve().parent.parent / "data" / "stage_reseau.json").read_text(encoding="utf-8"))
    r = md.construire()
    assert date.fromisoformat(brut["debut"]) == r.aujourd_hui
    assert all(date.fromisoformat(x["le"]) <= r.aujourd_hui for x in brut["rencontres_passees"])
    assert all(date.fromisoformat(p.maj) <= r.aujourd_hui for p in r.profils if p.maj)
    assert all(e.le <= r.aujourd_hui for e in r.memoire.evenements("RENCONTRE"))
    foire = [e for e in r.evenements if "Foire" in e.nom]
    assert foire and all(DEBUT <= e.le <= FIN for e in foire)                   # un événement « Foire » est DANS la Foire


def test_l_ecran_commun_montre_le_jeudi_de_la_foire():
    client = TestClient(app)
    assert client.post("/api/pulse/demo/reinitialiser", headers={"X-Pulse-Console": "1"}).status_code == 200
    p = client.get("/api/pulse/console/projection", headers={"X-Pulse-Console": "1"}).json()
    assert p["jour"] == "08.10" and p["jour_libelle"] == "Jeudi 08.10"
