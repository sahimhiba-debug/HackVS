"""La mesure de latence d'Apertus (`make latence-ia`) : statistiques justes, erreurs comptées à part (jamais lissées),
aucune nouvelle tentative, la clé jamais écrite, et sans configuration rien n'est appelé. Client HTTP FICTIF : aucun
réseau ; la vraie mesure se fait avec la clé, hors CI."""
import json

import pytest

from scripts import mesurer_latence_apertus as m

CLE = "cle-fictive-de-mesure-" + "q" * 20
ENV = {"APERTUS_API_KEY": CLE, "APERTUS_BASE_URL": "https://api.exemple.test/v1", "APERTUS_MODEL": "swiss-ai/Apertus-fictif"}
SORTIE_VALIDE = json.dumps({"objet": "Présenter des tisanes", "langue_public": "de", "manquant": [],
                            "fenetre": {"jour": "2026-10-08", "debut": "14:00", "fin": "16:00"},
                            "exigences": [{"role": "voix", "nature": "competence", "concept": None, "geste": "parler allemand au stand",
                                           "duree_min": 60, "livrable": None}]})


class Rep:
    def __init__(self, statut, corps):
        self.status_code, self._c = statut, corps
        self.text = json.dumps(corps)

    def json(self):
        return self._c


class Faux:
    """Répond 200 sauf aux appels dont l'indice est dans `pannes` (503) ; compte les requêtes et garde les en-têtes."""
    def __init__(self, pannes=()):
        self.n, self.pannes, self.entetes = 0, set(pannes), []

    def post(self, url, json=None, headers=None, timeout=None):
        self.n += 1
        self.entetes.append(headers or {})
        if self.n in self.pannes:
            return Rep(503, {"error": "indisponible"})
        contenu = SORTIE_VALIDE if json and json.get("max_tokens") == 900 else '{"canton": "VS"}'
        return Rep(200, {"choices": [{"message": {"content": contenu}}], "usage": {"completion_tokens": 42, "prompt_tokens": 900}})


def test_sans_configuration_rien_n_est_appele():
    f = Faux()
    with pytest.raises(SystemExit) as e:
        m.mesurer(3, env={"APERTUS_BASE_URL": "x", "APERTUS_MODEL": "y"}, http=f)
    assert e.value.code == 2 and f.n == 0


def test_statistiques_echauffement_exclu_et_erreurs_comptees_sans_nouvelle_tentative():
    f = Faux(pannes={3})                                      # 3e requête : la 2e mesure du profil tâche échoue
    r = m.mesurer(10, env=ENV, http=f)
    assert f.n == 22                                         # (10 + 1) par profil, une seule requête par appel
    t = r["tache"]
    assert t["appels"] == 10 and t["reussis"] == 9 and t["erreurs_http"] == 1 and t["causes"] == ["HTTP 503"]
    assert t["http_ms"]["n"] == 9 and t["acceptees"] == 9 and t["rejetees"] == 0
    assert t["jetons_sortie"]["mediane"] == 42
    assert r["court"]["reussis"] == 10
    assert r["contexte"]["nouvelles_tentatives"] == 0 and r["contexte"]["modele"] == "swiss-ai/Apertus-fictif"
    assert all(h.get("Authorization") == f"Bearer {CLE}" for h in f.entetes)          # la clé part bien à l'API…
    assert CLE not in json.dumps(r) and CLE not in m.rapport(r)                        # …et n'est écrite nulle part


def test_p95_au_rang_le_plus_proche():
    s = m.stats([float(x) for x in range(1, 21)])           # 20 valeurs : p95 = 19e
    assert (s["mediane"], s["p95"], s["min"], s["max"]) == (10.5, 19.0, 1.0, 20.0)
    assert m.stats([]) is None
