"""Sécurité et concurrence de l'API Club Pulse. Monde FICTIF ; chaque test part d'un monde réinitialisé."""
import json
import threading

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import TAX, app
from app.pulse_api import Limiteur, creer_routeur
from intelligence import monde_demo as md
from intelligence.acces import Sessions
from intelligence.club_pulse import ClubPulse
from intelligence.demo import CLAUDIA, Demo
from intelligence.erreurs import Limite, NonAuthentifie
from intelligence.politique import Spectateur
from intelligence.reglages import Reglages

client = TestClient(app)
CONSOLE = {"X-Pulse-Console": "1"}
S, A, L, M, P = md.SOPHIE, md.ANNA, md.LEA, md.MARKUS, md.PAULINE
ANIMATRICE_ = Spectateur("animatrice")


def _aller(n):
    assert client.post(f"/api/pulse/demo/aller/{n}", headers=CONSOLE).status_code == 200


def _h(pid):
    ses = {p["id"]: p["session"] for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    return {"X-Pulse-Session": ses[pid]}


def _essai():
    return next(t["ecran"]["cible"] for t in client.get("/api/pulse/etat", headers=CONSOLE).json()["traces"] if t["acte"] == "Invitation")


def _version(eid, pid=S):
    return client.get(f"/api/pulse/moi/essais/{eid}", headers=_h(pid)).json()["version"]


# ------------------------------------------------------------------ authentification ≠ autorisation
def test_authentifie_mais_pas_autorise():
    _aller(8)
    eid = _essai()
    obs = {"texte": "faux résultat", "qualification": "positif", "limites": "aucune"}
    assert client.post(f"/api/pulse/moi/essais/{eid}/observation", headers=_h(M), json=obs).status_code == 403   # pas le porteur
    assert client.get(f"/api/pulse/moi/essais/{eid}", headers=_h(P)).status_code == 404       # Pauline : invisible, pas « interdit »
    assert client.post(f"/api/pulse/moi/essais/{eid}/lancer", headers=_h(M), json={"version": 0}).status_code == 403
    assert client.get("/api/pulse/moi/essais/inconnu", headers=_h(S)).status_code == 404
    assert client.get("/api/pulse/moi/decouvertes/inconnue", headers=_h(S)).status_code == 404


def test_decouverte_d_un_autre_membre_interdite_et_console_gardee():
    _aller(3)
    oid = next(t for t in client.get("/api/pulse/console/intelligence", headers=CONSOLE).json()["premieres"] if "Sophie" in t["titre"])["id"]
    assert client.get(f"/api/pulse/moi/decouvertes/{oid}", headers=_h(A)).status_code == 403
    assert client.get(f"/api/pulse/moi/decouvertes/{oid}/en-clair", headers=_h(A)).status_code == 403   # contrôle AVANT l'IA
    assert client.post(f"/api/pulse/moi/decouvertes/{oid}/essai", headers=_h(M)).status_code == 403
    assert client.get(f"/api/pulse/console/decouvertes/{oid}").status_code == 403                # console : son en-tête
    assert client.get(f"/api/pulse/console/decouvertes/{oid}", headers=CONSOLE).status_code == 200


def test_sessions_falsifiees_expirees_ou_d_un_autre_monde_refusees():
    t = [1000.0]
    s = Sessions(b"x" * 32, duree_s=60, horloge=lambda: t[0])
    jeton = s.emettre("s10")
    assert s.verifier(jeton) == "s10"
    pid, exp, sig = jeton.split(".")
    for faux in (f"n01.{exp}.{sig}", f"{pid}.{int(exp) + 999}.{sig}", "s10", "", "a.b.c"):
        with pytest.raises(NonAuthentifie):
            s.verifier(faux)
    t[0] = 2000.0
    with pytest.raises(NonAuthentifie, match="expirée"):
        s.verifier(jeton)
    ancien = _h(S)                                                         # jeton du monde précédent
    _aller(0)
    assert client.get("/api/pulse/moi/decouvertes", headers=ancien).status_code == 401   # nouveau monde, nouveau secret


def test_aucun_secret_par_defaut():
    a, b = Reglages.depuis_env({}), Reglages.depuis_env({})
    assert a.secret != b.secret and not a.secret_fourni                   # tiré au hasard à chaque démarrage
    with pytest.raises(ValueError):
        Reglages.depuis_env({"HACKVS_SECRET": "trop-court"})
    c1, c2 = ClubPulse(TAX, reglages=a), ClubPulse(TAX, reglages=b)
    assert c1.coffre.code_invitation(S) != c2.coffre.code_invitation(S)   # codes d'invitation imprévisibles


# ------------------------------------------------------------------ console, fréquence, taille
def test_console_exige_son_en_tete_et_son_jeton():
    assert client.post("/api/pulse/demo/reinitialiser").status_code == 403       # requête intersite : bloquée
    assert client.get("/api/pulse/console/personas").status_code == 403
    appli = FastAPI()
    appli.include_router(creer_routeur(TAX, console_jeton="jeton-console-de-test"))
    c = TestClient(appli)
    assert c.get("/api/pulse/console/intelligence", headers={"X-Pulse-Console": "1"}).status_code == 403
    assert c.get("/api/pulse/console/intelligence", headers={"X-Pulse-Console": "jeton-console-de-test"}).status_code == 200
    assert client.get("/api/pulse/etat").status_code == 403                  # le récit de la démo nomme des personnes


def test_console_sans_jeton_ne_repond_qu_a_cette_machine():
    """Sans HACKVS_CONSOLE_JETON, la console (qui peut incarner chaque membre) refuse un client distant ; avec un jeton,
    elle l'accepte. Défaut réel : déployée telle quelle, n'importe qui sur le réseau obtenait la session de chacun."""
    distant = TestClient(app, client=("203.0.113.9", 50000))
    for chemin in ("/api/pulse/console/personas", "/api/pulse/etat", "/api/pulse/console/intelligence"):
        r = distant.get(chemin, headers=CONSOLE)
        assert r.status_code == 403 and "HACKVS_CONSOLE_JETON" in r.json()["detail"], chemin
    assert client.get("/api/pulse/console/personas", headers=CONSOLE).status_code == 200    # même machine : démo locale
    appli = FastAPI()
    appli.include_router(creer_routeur(TAX, console_jeton="jeton-console-de-test"))
    loin = TestClient(appli, client=("203.0.113.9", 50000))
    assert loin.get("/api/pulse/console/intelligence", headers={"X-Pulse-Console": "jeton-console-de-test"}).status_code == 200


def test_deviner_un_code_d_invitation_est_limite():
    appli = FastAPI()
    appli.include_router(creer_routeur(TAX))
    c = TestClient(appli)
    statuts = [c.post("/api/pulse/acces", json={"code": f"ZZZZ{i:02d}"}).status_code for i in range(12)]
    assert statuts[:10] == [401] * 10 and statuts[10:] == [429, 429]
    t = [0.0]
    lim = Limiteur(2, 60.0, horloge=lambda: t[0])
    lim.verifier("k")
    lim.verifier("k")
    with pytest.raises(Limite):
        lim.verifier("k")
    t[0] = 61.0
    lim.verifier("k")                                                      # la fenêtre glisse


def test_entrees_hors_limites_refusees():
    _aller(1)
    h = _h(S)
    assert client.post("/api/pulse/moi/notes", headers=h, json={"texte": "x" * 2001}).status_code == 422
    assert client.post("/api/pulse/moi/demandes", headers=h, json={"texte": "x" * 601}).status_code == 422
    assert client.patch("/api/pulse/moi/profil", headers=h, json={"visibilite": {"notes": "PUBLIC"}}).status_code == 422
    assert client.patch("/api/pulse/moi/profil", headers=h, json={"visibilite": {"nom": "RELATIONS"}}).status_code == 422
    assert client.post("/api/pulse/console/temps", headers=CONSOLE, json={"jours": 999}).status_code == 422


# ------------------------------------------------------------------ idempotence et concurrence
def test_double_proposition_simultanee_un_seul_essai():
    _aller(3)
    oid = client.get("/api/pulse/etat", headers=CONSOLE).json()["traces"][1]["ecran"]["cible"]
    h = _h(S)
    r1, r2 = _en_parallele(lambda: client.post(f"/api/pulse/moi/decouvertes/{oid}/essai", headers=h),
                           lambda: client.post(f"/api/pulse/moi/decouvertes/{oid}/essai", headers=h))
    assert sorted([r1.status_code, r2.status_code]) == [200, 409]           # un double clic ne crée pas deux essais
    lecture = client.get(f"/api/pulse/moi/decouvertes/{oid}", headers=h)    # RELIRE n'est pas un conflit
    assert lecture.status_code == 200 and lecture.json()["essai"] and not lecture.json()["peut_proposer"]


def _en_parallele(*appels):
    res: list = [None] * len(appels)
    fils = [threading.Thread(target=lambda i=i, f=f: res.__setitem__(i, f())) for i, f in enumerate(appels)]
    for f in fils:
        f.start()
    for f in fils:
        f.join()
    return res


def test_deux_acceptations_simultanees_une_seule_compte():
    _aller(4)
    eid = _essai()
    h, v = _h(M), _version(eid, M)
    corps = {"version": v, "accepte": True}
    r1, r2 = _en_parallele(lambda: client.post(f"/api/pulse/moi/essais/{eid}/decision", headers=h, json=corps),
                           lambda: client.post(f"/api/pulse/moi/essais/{eid}/decision", headers=h, json=corps))
    assert (r1.status_code, r2.status_code) == (200, 200)                  # le second est rejoué sans effet (idempotent)
    offres = client.get("/api/pulse/moi/souvenirs", headers=h).json()["offres"]
    assert sum(1 for o in offres if "Développement commercial" in o["quoi"] or "Échange" in o["quoi"]) == 1   # une disponibilité, pas deux


def test_acceptation_et_annulation_simultanees_etat_coherent():
    _aller(4)
    eid = _essai()
    h, v = _h(M), _version(eid, M)
    r1, r2 = _en_parallele(lambda: client.post(f"/api/pulse/moi/essais/{eid}/decision", headers=h, json={"version": v, "accepte": True}),
                           lambda: client.post(f"/api/pulse/console/essais/{eid}/annuler", headers=CONSOLE, json={"raison": "le jury arrête"}))
    assert {r1.status_code, r2.status_code} <= {200, 409} and 500 not in (r1.status_code, r2.status_code)
    assert client.get(f"/api/pulse/console/essais/{eid}", headers=CONSOLE).json()["etat"] == "ANNULE"   # l'annulation gagne
    assert client.post(f"/api/pulse/moi/essais/{eid}/decision", headers=h, json={"version": v, "accepte": True}).status_code == 409


def test_rien_ne_continue_apres_annulation():
    d = Demo(TAX)
    d.rejouer(5)
    c, eid = d.club, d.ctx["essai"]
    c.banc.annuler("", eid, "annulé par le Club", console=True)
    avant = len(c.banc._evs(eid))
    c.avancer(30)                                                          # échéances : rien sur un essai annulé
    assert len(c.banc._evs(eid)) == avant and c.banc.etat(eid) == "ANNULE"


# ------------------------------------------------------------------ organisations et coffre
def test_collegues_d_une_meme_organisation_ne_partagent_rien_de_prive():
    d = Demo(TAX)
    c = d.club
    adh = next(a for a in c.coffre.adhesions.values() if a.formule == "entreprise")
    x, y = [p.id for p in c.coffre._personnes.values() if p.adhesion_id == adh.id][:2]
    c.coffre.actives.update({x, y})
    c.capturer(x, "Rencontré Markus : il cherche des producteurs de boissons. Note confidentielle.")
    assert c.vues.notes_de(y) == []
    for vue in (c.vues.decouvertes_de(y), c.vues_essai.actions(y), c.vues_essai.souvenirs(y)):
        assert "confidentielle" not in json.dumps(vue, ensure_ascii=False)


def test_le_moteur_ne_voit_aucune_identite():
    c = Demo(TAX).club
    brut = json.dumps([p.model_dump() for p in c.r.profils], ensure_ascii=False)
    for per in c.coffre._personnes.values():
        assert per.nom not in brut and per.courriel not in brut
    assert "@" not in brut


def test_qui_a_decline_n_est_nomme_qu_a_la_personne_qui_l_a_invite():
    """Markus décline l'invitation ; Sophie choisit de demander à Claudia, qui accepte. Seule Sophie (qui l'avait
    invité) sait que c'était Markus : ni Claudia, ni la console, ni un autre membre."""
    d = Demo(TAX)
    d.rejouer(4)
    c, eid = d.club, d.ctx["essai"]
    c.banc.decider(M, eid, c.banc.version(eid), False)
    alt = next(a for a in c.banc.alternatives(eid) if a["type"] == "remplacer")
    c.banc.choisir_alternative(S, eid, c.banc.version(eid), alt["id"])
    c.banc.decider(CLAUDIA, eid, c.banc.version(eid), True)
    assert c.banc.etat(eid) == "AUTORISE"
    nom = c.coffre.identite(M).nom
    vues = {"Claudia": c.vues_essai.essai(eid, CLAUDIA), "console": c.vues_essai.essai(eid, None, console=True),
            "console (essais)": c.vues_essai.console()["essais"], "Nicolas": c.vues.decouvertes_de(md.NICOLAS)}
    for qui, vue in vues.items():
        assert nom not in json.dumps(vue, ensure_ascii=False), qui
    assert "Claudia Imboden" in json.dumps(c.vues_essai.essai(eid, S), ensure_ascii=False)   # nommée après SON accord


def test_l_audit_des_ecrans_attrape_une_fuite_reintroduite(monkeypatch):
    """Le banc de confidentialité (eval/benchmark_pulse.py) a trouvé deux fuites réelles, corrigées : l'identifiant
    interne de la personne mentionnée dans une note, et le raisonnement pseudonymisé copié dans le « pourquoi » d'un
    essai. Réintroduire la première doit le faire échouer (le filet a des mailles)."""
    from eval.benchmark_pulse import confidentialite_ecrans
    from intelligence.vues_intelligence import VuesIntelligence
    assert confidentialite_ecrans()["fuites"] == []
    monkeypatch.setattr(VuesIntelligence, "vue_note", lambda self, pid, note: note)
    assert ("identifiant interne de membre", S) in confidentialite_ecrans()["fuites"]
