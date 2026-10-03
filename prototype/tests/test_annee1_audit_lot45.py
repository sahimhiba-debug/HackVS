"""ANNÉE 1 — correctifs de l'audit des lots 4 (secrétariat) et 5 (notifications). Chaque cas reproduit un constat de
l'audit (docs/annee-1/AUDIT_LOT45.md) ; il était ROUGE avant le correctif. Données FICTIVES."""
import json
import socket
import threading
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.taxonomy import charger_taxonomie
from intelligence import espace_membre as em
from intelligence import monde_demo as md
from intelligence import notifications as nt
from intelligence import secretariat as sec
from intelligence.comptes import code_totp
from intelligence.demo import Demo
from intelligence.erreurs import Invalide
from tests.test_annee1_notifications import ServeurSmtp, _texte

TAX = charger_taxonomie()


@pytest.fixture
def demo(monkeypatch, tmp_path):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    return Demo(TAX)


def _notif(c, port):
    return nt.Notifications(c, email=nt.SmtpGenerique("127.0.0.1", port, expediteur="club@exemple.invalid", starttls=False,
                                                         delai_s=3), sms=nt.FauxSms(), base="https://club.exemple", secret=b"n" * 32)


# ------------------------------------------------------------------ B1 : jamais d'envoi sous le verrou du monde
@pytest.fixture
def api(monkeypatch, tmp_path):
    for k, v in {"HACKVS_ESSAIS_DB": str(tmp_path / "j.db"), "HACKVS_SECRET": "p" * 40, "HACKVS_FOIRE": "1", "HACKVS_COMPTES": "1",
                 "HACKVS_SECRETARIAT": "1", "HACKVS_NOTIFICATIONS": "1", "HACKVS_ESPACE_MEMBRE": "1"}.items():
        monkeypatch.setenv(k, v)
    from app.pulse_api import creer_routeur
    routeur = creer_routeur(TAX)
    app = FastAPI()
    app.include_router(routeur)
    cl = TestClient(app)
    cp = routeur.comptes()
    admin = cp.amorcer_administration("Administration (fictive)")
    p = cp.preparer_totp(admin)
    cp.confirmer_totp(admin, code_totp(p["secret"], time.time()))
    cp.elever(admin, code_totp(p["secret"], time.time() + 30))
    for x in cl.get("/api/pulse/console/personas", headers={"X-Pulse-Console": "1"}).json():
        if x.get("session"):
            cl.post("/api/pulse/moi/preferences", headers={"X-Pulse-Session": x["session"]},
                    json={"langue": "fr", "region": "", "canaux": ["app", "email"]})
    persona = next(x for x in cl.get("/api/pulse/console/personas", headers={"X-Pulse-Console": "1"}).json() if x.get("session"))
    return cl, {"X-Pulse-Compte": admin}, {"X-Pulse-Session": persona["session"]}, monkeypatch


def test_b1_un_serveur_smtp_muet_ne_gele_pas_le_club(api):
    cl, adm, membre, mp = api
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen(50)
    pris = []
    threading.Thread(target=lambda: [pris.append(s.accept()) for _ in iter(int, 1)], daemon=True).start()
    mp.setenv("SMTP_HOST", "127.0.0.1")
    mp.setenv("SMTP_PORT", str(s.getsockname()[1]))
    mp.setenv("SMTP_STARTTLS", "0")
    mp.setenv("SMTP_DELAI_S", "2")
    res = {}
    th = threading.Thread(target=lambda: res.update(r=cl.post("/api/pulse/secretariat/notifications/relance", headers=adm)))
    th.start()
    time.sleep(1.0)
    t0 = time.monotonic()
    assert cl.get("/api/pulse/moi/espace", headers=membre).status_code == 200
    attente = time.monotonic() - t0
    th.join(120)
    s.close()
    assert attente < 1.5, f"une lecture a attendu {attente:.1f} s pendant la relance"
    assert res["r"].status_code == 200 and res["r"].json()["echec"] >= 1


# ------------------------------------------------------------------ I1 : une adresse piégée ne casse pas la relance
def test_i1_adresse_avec_retour_ligne_ou_virgule_suivie_comme_echec(demo):
    c = demo.club
    smtp = ServeurSmtp()
    try:
        for pid, piege in ((md.PAULINE, "x@exemple.invalid\r\nBcc: pirate@exemple.invalid"), (md.MARKUS, "a@exemple.invalid, b@exemple.invalid")):
            em.regler_preferences(c, pid, langue="fr", region="", canaux=["email"])
            c.coffre._personnes[pid] = c.coffre.identite(pid).model_copy(update={"courriel": piege})
        em.regler_preferences(c, md.SOPHIE, langue="fr", region="", canaux=["email"])
        n = _notif(c, smtp.port)
        r = [n.envoyer(pid, "demandes_en_attente", {"nombre": 1}) for pid in (md.PAULINE, md.MARKUS, md.SOPHIE)]
    finally:
        smtp.fermer()
    assert [x[0]["statut"] for x in r] == ["echec", "echec", "envoye"]
    assert all(len(m["a"]) == 1 and "pirate" not in m["data"] for m in smtp.recus)


# ------------------------------------------------------------------ I2 : pas de doublon le même jour
def test_i2_deux_relances_le_meme_jour_un_seul_message(demo):
    c = demo.club
    smtp = ServeurSmtp()
    try:
        em.regler_preferences(c, md.PAULINE, langue="fr", region="", canaux=["email"])
        n = _notif(c, smtp.port)
        a = n.envoyer(md.PAULINE, "demandes_en_attente", {"nombre": 1})
        b = n.envoyer(md.PAULINE, "demandes_en_attente", {"nombre": 1})
    finally:
        smtp.fermer()
    assert a[0]["statut"] == "envoye" and (b[0]["statut"], b[0]["raison"]) == ("ignore", "déjà envoyé aujourd'hui")
    assert len(smtp.recus) == 1


# ------------------------------------------------------------------ I3 : campagnes bornées
def test_i3_campagnes_plafonnees_par_jour(demo):
    from intelligence import club_cherche
    c = demo.club
    metier = club_cherche.calculer(c)["metiers"][0]["metier"]
    with pytest.raises(Invalide):
        sec.lancer_campagne(c, metier, 21, base="https://x")             # au plus 20 par campagne
    for _ in range(5):
        sec.lancer_campagne(c, metier, 20, base="https://x")
    with pytest.raises(Invalide, match="aujourd'hui"):
        sec.lancer_campagne(c, metier, 1, base="https://x")              # au plus 100 passes par jour


# ------------------------------------------------------------------ I4 : la désinscription publique ne se bloque pas
def test_i4_des_liens_faux_ne_bloquent_pas_un_vrai_lien(api):
    cl, adm, membre, mp = api
    for _ in range(320):
        cl.post("/api/pulse/notifications/desinscrire", json={"jeton": "s01.email.faux.0000000000000000"})
    from intelligence import notifications as n2
    vrai = None
    smtp = ServeurSmtp()
    try:
        mp.setenv("SMTP_HOST", "127.0.0.1")
        mp.setenv("SMTP_PORT", str(smtp.port))
        mp.setenv("SMTP_STARTTLS", "0")
        cl.post("/api/pulse/secretariat/notifications/relance", headers=adm)
        vrai = _texte(smtp.recus[0]).rsplit("desinscription#j=", 1)[1].split()[0]
    finally:
        smtp.fermer()
    assert n2 and cl.post("/api/pulse/notifications/desinscrire", json={"jeton": vrai}).status_code == 200


# ------------------------------------------------------------------ I5 : « < 3 » compté en entreprises, libellés rares
def test_i5_metiers_comptes_en_entreprises_et_libelles_rares_regroupes(demo, monkeypatch, tmp_path):
    f = tmp_path / "e.csv"
    f.write_text("nom;metier\nAcme SA;Acme SA - sous-traitance horlogère\nWolfCorp;Gravure laser Wolf\nWolfCorp;Gravure laser Wolf\n"
                 "WolfCorp;Gravure laser Wolf\nA1;Paysagiste\nB2;Paysagiste\nC3;paysagiste\n", encoding="utf-8")
    monkeypatch.setenv("HACKVS_ENTREPRISES_CSV", str(f))
    r = sec.metiers_a_verifier(demo.club)
    brut = json.dumps(r, ensure_ascii=False)
    assert "acme" not in brut.lower() and "wolf" not in brut.lower()           # libellés de moins de 3 entreprises : cachés
    assert [x["valeur"] for x in r["a_verifier"]] == ["paysagiste"] and r["a_verifier"][0]["entreprises"] == 3
    assert r["rares"] == 2                                                    # deux libellés, dits par leur seul nombre


# ------------------------------------------------------------------ I6 : seuils et mesures vérifiés
@pytest.mark.parametrize("seuil", [True, "30", None])
def test_i6_un_seuil_qui_n_est_pas_un_nombre_est_refuse(demo, tmp_path, seuil):
    f = tmp_path / "c.json"
    d = sec.criteres_par_defaut()
    d[0]["seuil"] = seuil
    f.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(Invalide):
        sec.tableau_pilote(demo.club, f)


def test_i6_une_mesure_inconnue_est_refusee(demo, tmp_path):
    f = tmp_path / "c.json"
    d = sec.criteres_par_defaut()
    d[0]["mesure"] = "reponses.inventee"
    f.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(Invalide):
        sec.tableau_pilote(demo.club, f)


# ------------------------------------------------------------------ M1, M2, M3
def test_m1_le_lien_stop_du_sms_n_est_jamais_coupe(demo):
    c = demo.club
    em.regler_preferences(c, md.PAULINE, langue="de", region="", canaux=["sms"])
    c.coffre._personnes[md.PAULINE] = c.coffre.identite(md.PAULINE).model_copy(update={"telephone": "+41 00 000 00 00"})
    sms = nt.FauxSms()
    n = nt.Notifications(c, email=nt.Simule("email"), sms=sms, base="https://" + "tres-longue-adresse-publique." * 4 + "ch",
                         secret=b"n" * 32)
    n.envoyer(md.PAULINE, "demandes_en_attente", {"nombre": 2})
    texte = sms.envoyes[0]["texte"]
    jeton = texte.rsplit("desinscription#j=", 1)[1]
    assert len(texte) <= 480 and n.desinscrire(jeton)["desinscrit"] is True


def test_m2_le_repli_vers_le_francais_est_trace(demo):
    c = demo.club
    em.regler_preferences(c, md.PAULINE, langue="en", region="", canaux=["email"])
    r = nt.Notifications(c, email=nt.Simule("email"), sms=nt.FauxSms(), base="https://x", secret=b"n" * 32).envoyer(
        md.PAULINE, "demandes_en_attente", {"nombre": 1})
    assert r[0]["langue"] == "fr" and r[0]["raison"] == "repli fr"


def test_m3_un_identifiant_avec_un_point(demo):
    n = nt.Notifications(demo.club, email=nt.Simule("email"), sms=nt.FauxSms(), base="https://x", secret=b"n" * 32)
    lien = n.lien_desinscription("membre.avec.points", "email")
    assert n.desinscrire(lien.split("#j=", 1)[1])["desinscrit"] is True
