"""Diagnostic d'organisation : boucle complète, aucune écriture, ne rien faire quand rien n'est prouvé."""
import json
from datetime import date

from adaptateurs.club import diagnostic as dg
from app.models import Profil
from app.taxonomy import DATA_DIR, charger_taxonomie
from plateforme.memoire import Memoire

TAX = charger_taxonomie()
P = [Profil(**p) for p in json.loads((DATA_DIR / "profils_demo.json").read_text(encoding="utf-8"))["profils"]]


def test_route_boucle_complete_sans_ecriture_et_bornee():
    from fastapi.testclient import TestClient

    from app import main
    c = TestClient(main.app)
    c.post("/api/demo/reinitialiser")
    c.get("/api/reseau/diagnostic")                       # 1er appel : projection du magasin
    avant = main.MEMOIRE.empreinte()
    r = c.get("/api/reseau/diagnostic?k=3&horizon=30")
    assert r.status_code == 200 and main.MEMOIRE.empreinte() == avant
    d = r.json()
    assert set(d) >= {"comprendre", "diagnostiquer", "voir_venir", "agir", "observer", "se_souvenir", "decision"}
    assert d["donnees_fictives"] and "@" not in r.text
    for q in ("k=0", "k=500", "horizon=1", "horizon=365"):
        assert c.get(f"/api/reseau/diagnostic?{q}").status_code == 422, q


def test_ne_rien_faire_quand_rien_n_est_prouve_ni_menace():
    fermes = [p.model_copy(update={"accepte_introductions": False}) for p in P]
    d = dg.diagnostic(Memoire(), fermes, [], TAX, date(2026, 10, 1))
    assert d["decision"] == "NE_RIEN_FAIRE" and d["agir"]["decision"] == "NE_RIEN_FAIRE"
    assert d["diagnostiquer"]["phenomenes"] == [] and "abstention" in d["diagnostiquer"]


def test_phenomenes_tries_par_priorite():
    from eval import reseaux_pathologiques as rp
    from adaptateurs.club import sante
    r = rp.pathologique("VIEILLISSEMENT", 0)
    ph = sante.phenomenes(r["g_hist"], r["g_act"], r["membres"], r["secteurs"], r["sollicitations"])["phenomenes"]
    ordre = sorted((p["phenomene"] for p in ph), key=dg.PRIORITE.index)
    assert ordre[0] == "ISOLEMENT" and ordre[-1] == "VIEILLISSEMENT"


def test_aucun_ravivement_ne_sollicite_un_membre_qui_refuse_les_introductions():
    """Défaut trouvé en red team : le diagnostic proposait de raviver la relation d'un membre fermé aux introductions."""
    from adaptateurs.club import cycle as cy
    from eval.perf_echelle import generer
    p, m, t = generer(150, 1)
    d = dg.diagnostic(m, p, cy.besoins_publies(m, t), TAX, t)
    fermes = {x.id for x in p if not x.accepte_introductions or not x.disponible}
    rav = [r["paire"] for r in d["voir_venir"]["INCLUSION"]["ravivements"]] + d["voir_venir"]["COHESION_ravivements"]
    assert fermes and not [r for r in rav if set(r) & fermes]
    for plan in d["agir"]["front"]:
        assert not [x for x in plan["paires"] if set(x) & fermes]


def test_chaque_changement_recoit_une_action_prouvee_ou_le_silence():
    from adaptateurs.club import cycle as cy
    from eval.perf_echelle import generer
    p, m, t = generer(150, 2)
    d = dg.diagnostic(m, p, cy.besoins_publies(m, t), TAX, t)
    evs = d["observer"]["evenements"]
    assert evs
    fermes = {x.id for x in p if not x.accepte_introductions or not x.disponible}
    for ev in evs:
        assert ("actions_prouvees" in ev) and (bool(ev["actions_prouvees"]) != bool(ev["si_aucune"]))
        for a in ev["actions_prouvees"]:
            concernes = set(a.get("paire", [])) | ({a["membre"]} if "membre" in a else set())
            assert not concernes & fermes                                  # consentement, même ici


def test_chaque_action_proposee_a_une_preuve_verifiable_mot_pour_mot():
    """Explicabilité vérifiable : l'extrait cité pour chaque action existe tel quel dans le profil de l'aidant."""
    from adaptateurs.club import cycle as cy
    from app.matching import preuve_valide
    from app.models import Preuve
    from eval.perf_echelle import generer
    p, m, t = generer(150, 3)
    par_id = {x.id: x for x in p}
    d = dg.diagnostic(m, p, cy.besoins_publies(m, t), TAX, t)
    verifiees = 0
    for plan in d["agir"]["front"]:
        assert [x["paire"] for x in plan["pourquoi"]] == plan["paires"]
        for action in plan["pourquoi"]:
            assert action["preuves"]
            for pr in action["preuves"]:
                assert set((pr["aide"], pr["aide_a"])) == set(action["paire"])
                assert preuve_valide(par_id[pr["aide"]], Preuve(critere="aide", extrait=pr["preuve"], champ=pr["champ"],
                                                               nature=pr["nature"])), pr
                verifiees += 1
    assert verifiees > 0


def test_diagnostic_deterministe_et_double_soumission_d_une_decision_sans_doublon():
    import json as js

    from adaptateurs.club import boucle
    from adaptateurs.club import cycle as cy
    from eval.perf_echelle import generer
    p, m, t = generer(100, 5)
    b = cy.besoins_publies(m, t)
    d1, d2 = dg.diagnostic(m, p, b, TAX, t), dg.diagnostic(m, p, b, TAX, t)
    assert js.dumps(d1, sort_keys=True, default=str) == js.dumps(d2, sort_keys=True, default=str)
    plan = d1["agir"]["front"][0]
    membres = sorted(x.id for x in p if x.type == "membre_club")
    e1 = boucle.enregistrer(m, t, plan, "org", membres)
    e2 = boucle.enregistrer(m, t, plan, "org", membres)            # double clic : même fait, idempotent
    assert e1.id == e2.id and len(m.evenements("DECISION_ORGANISATION")) == 1
