"""ANNÉE 1 · LOT 5 — Notifications réelles : adaptateur e-mail SMTP générique (testé contre un VRAI serveur SMTP local),
adaptateur SMS (interface + faux fournisseur), modèles FR/DE, suivi d'envoi, désinscription. En démonstration, tout est
SIMULÉ et étiqueté. Le journal ne garde jamais une adresse ni le contenu d'un message. Données FICTIVES."""
import socket
import threading
from datetime import timedelta

import pytest

from app.taxonomy import charger_taxonomie
from intelligence import espace_membre as em
from intelligence import monde_demo as md
from intelligence import notifications as nt
from intelligence.demo import Demo
from intelligence.erreurs import NonAuthentifie

TAX = charger_taxonomie()


class ServeurSmtp:
    """Un vrai serveur SMTP minimal (RFC 5321 : EHLO, MAIL, RCPT, DATA, QUIT) sur la boucle locale, pour les tests."""

    def __init__(self, refuser: bool = False):
        self.recus: list[dict] = []
        self.refuser = refuser
        self.s = socket.socket()
        self.s.bind(("127.0.0.1", 0))
        self.s.listen(5)
        self.port = self.s.getsockname()[1]
        threading.Thread(target=self._boucle, daemon=True).start()

    def _boucle(self):
        while True:
            try:
                conn, _ = self.s.accept()
            except OSError:
                return
            threading.Thread(target=self._client, args=(conn,), daemon=True).start()

    def _client(self, conn):
        f = conn.makefile("rwb")

        def dire(x):
            f.write((x + "\r\n").encode())
            f.flush()
        dire("220 test ESMTP")
        courant = {"de": None, "a": [], "data": ""}
        while True:
            ligne = f.readline().decode(errors="replace").rstrip("\r\n")
            if not ligne:
                break
            cmd = ligne.split(" ", 1)[0].upper()
            if cmd in ("EHLO", "HELO"):
                dire("250 test")
            elif cmd == "MAIL":
                courant["de"] = ligne
                dire("250 ok")
            elif cmd == "RCPT":
                if self.refuser:
                    dire("550 boîte inconnue")
                else:
                    courant["a"].append(ligne.split(":", 1)[1].strip("<> "))
                    dire("250 ok")
            elif cmd == "DATA":
                dire("354 suite")
                lignes = []
                while True:
                    x = f.readline().decode(errors="replace")
                    if x in (".\r\n", ".\n"):
                        break
                    lignes.append(x)
                courant["data"] = "".join(lignes)
                self.recus.append(dict(courant))
                dire("250 accepté")
            elif cmd == "QUIT":
                dire("221 au revoir")
                break
            else:
                dire("250 ok")
        conn.close()

    def fermer(self):
        self.s.close()


@pytest.fixture
def demo(monkeypatch, tmp_path):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    return Demo(TAX)


@pytest.fixture
def smtp():
    s = ServeurSmtp()
    yield s
    s.fermer()


def _texte(recu: dict) -> str:
    """Le message tel que le lit un client de messagerie (en-têtes + corps décodé)."""
    import email
    from email import policy
    m = email.message_from_string(recu["data"], policy=policy.default)
    return "".join(f"{k}: {v}\n" for k, v in m.items()) + m.get_content()


def _telephone(c, pid):
    """Les membres FICTIFS n'ont pas de numéro : on leur en donne un, fictif, pour tester le canal SMS."""
    ident = c.coffre.identite(pid)
    c.coffre._personnes[pid] = ident.model_copy(update={"telephone": "+41 00 000 00 00"})


def _notif(c, smtp=None, sms=None, simule=False):
    email = nt.Simule("email") if simule else nt.SmtpGenerique("127.0.0.1", smtp.port, expediteur="club@exemple.invalid",
                                                                starttls=False)
    return nt.Notifications(c, email=email, sms=sms or nt.FauxSms(), base="https://club.example", secret=b"n" * 32)


def test_un_email_part_vraiment_par_smtp_dans_la_langue_du_membre(demo, smtp):
    c = demo.club
    em.regler_preferences(c, md.PAULINE, langue="de", region="", canaux=["app", "email"])
    r = _notif(c, smtp).envoyer(md.PAULINE, "demandes_en_attente", {"nombre": 2})
    assert [x["statut"] for x in r] == ["envoye"]
    recu = smtp.recus[-1]
    assert recu["a"] == [c.coffre.identite(md.PAULINE).courriel]
    texte = _texte(recu)
    assert "Anfragen" in texte and "nicht mehr erhalten: https://club.example/desinscription#j=" in texte
    assert "List-Unsubscribe: <https://club.example/desinscription#j=" in texte


def test_le_journal_ne_garde_ni_adresse_ni_contenu(demo, smtp):
    c = demo.club
    em.regler_preferences(c, md.PAULINE, langue="fr", region="", canaux=["email", "sms"])
    _telephone(c, md.PAULINE)
    n = _notif(c, smtp)
    n.envoyer(md.PAULINE, "demandes_en_attente", {"nombre": 3})
    brut = "".join(e.model_dump_json() for e in c.journal.evenements("NOTIF_ENVOI"))
    ident = c.coffre.identite(md.PAULINE)
    assert brut and ident.courriel not in brut and ident.telephone not in brut and "attendent" not in brut
    assert {(x["canal"], x["statut"]) for x in n.suivi()["envois"]} >= {("email", "envoye"), ("sms", "envoye")}


def test_seuls_les_canaux_choisis_sont_utilises(demo, smtp):
    c = demo.club
    em.regler_preferences(c, md.PAULINE, langue="fr", region="", canaux=["app"])
    assert _notif(c, smtp).envoyer(md.PAULINE, "demandes_en_attente", {"nombre": 1}) == []
    assert smtp.recus == []


def test_en_pause_on_ne_recoit_rien(demo, smtp):
    c = demo.club
    em.regler_preferences(c, md.PAULINE, langue="fr", region="", canaux=["email"])
    em.mettre_en_pause(c, md.PAULINE, c.jour + timedelta(days=5))
    r = _notif(c, smtp).envoyer(md.PAULINE, "demandes_en_attente", {"nombre": 1})
    assert [(x["statut"], x["raison"]) for x in r] == [("ignore", "pause")] and smtp.recus == []


def test_desinscription_par_lien_signe(demo, smtp):
    c = demo.club
    em.regler_preferences(c, md.PAULINE, langue="fr", region="", canaux=["email"])
    n = _notif(c, smtp)
    n.envoyer(md.PAULINE, "demandes_en_attente", {"nombre": 1})
    jeton = _texte(smtp.recus[-1]).rsplit("desinscription#j=", 1)[1].split()[0]          # le lien du pied de message
    with pytest.raises(NonAuthentifie):
        n.desinscrire(jeton[:-3] + "xyz")                                     # falsifié
    assert n.desinscrire(jeton)["canal"] == "email"
    r = n.envoyer(md.PAULINE, "demandes_en_attente", {"nombre": 1})
    assert [(x["statut"], x["raison"]) for x in r] == [("ignore", "desinscrit")] and len(smtp.recus) == 1


def test_un_echec_smtp_est_suivi_jamais_cache(demo):
    c = demo.club
    em.regler_preferences(c, md.PAULINE, langue="fr", region="", canaux=["email"])
    refus = ServeurSmtp(refuser=True)
    try:
        r = _notif(c, refus).envoyer(md.PAULINE, "demandes_en_attente", {"nombre": 1})
    finally:
        refus.fermer()
    assert [x["statut"] for x in r] == ["echec"]
    assert n_echecs(c) == 1


def n_echecs(c):
    return sum(1 for e in c.journal.evenements("NOTIF_ENVOI") if e.donnees["resultat"] == "echec")


def test_le_faux_fournisseur_sms_et_le_mode_simule(demo):
    c = demo.club
    em.regler_preferences(c, md.PAULINE, langue="fr", region="", canaux=["email", "sms"])
    _telephone(c, md.PAULINE)
    sms = nt.FauxSms()
    r = _notif(c, sms=sms, simule=True).envoyer(md.PAULINE, "demandes_en_attente", {"nombre": 4})
    assert {(x["canal"], x["statut"]) for x in r} == {("email", "simule"), ("sms", "envoye")}
    assert len(sms.envoyes) == 1 and len(sms.envoyes[0]["texte"]) <= 320 and "4" in sms.envoyes[0]["texte"]


def test_chaque_modele_existe_en_francais_et_en_allemand():
    for nom, langues in nt.MODELES.items():
        assert {"fr", "de"} <= set(langues), nom
        for lg in ("fr", "de"):
            assert {"sujet", "corps", "sms"} <= set(langues[lg]), (nom, lg)


def test_sans_numero_le_sms_n_est_pas_tente(demo):
    c = demo.club
    em.regler_preferences(c, md.PAULINE, langue="fr", region="", canaux=["sms"])
    r = _notif(c, simule=True).envoyer(md.PAULINE, "demandes_en_attente", {"nombre": 1})
    assert [(x["statut"], x["raison"]) for x in r] == [("ignore", "sans numéro")]
