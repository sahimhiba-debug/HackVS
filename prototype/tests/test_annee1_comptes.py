"""ANNÉE 1 · LOT 2 — Authentification et rôles (domaine).

Invitation personnelle envoyée par le Club (lien à usage unique, expiration) ; sessions signées, déconnexion, liste de
ses appareils ; rôles membre / invité / secrétariat / administration ; comptes nominatifs pour le secrétariat ; double
authentification par code (TOTP, RFC 6238) pour la console ; journal des actions d'administration.
Rien de secret dans le journal : jetons et secrets TOTP n'y sont JAMAIS en clair. Données FICTIVES."""
import hashlib
import hmac
import struct


import pytest

from intelligence import comptes as cp
from intelligence.erreurs import Interdit, NonAuthentifie
from plateforme.memoire import Memoire

SECRET = b"s" * 48


def totp(secret_b32: str, t: float, pas: int = 30) -> str:
    """Implémentation de RÉFÉRENCE (RFC 6238 / RFC 4226), indépendante du module testé."""
    import base64
    cle = base64.b32decode(secret_b32 + "=" * (-len(secret_b32) % 8))
    h = hmac.new(cle, struct.pack(">Q", int(t // pas)), hashlib.sha1).digest()
    o = h[-1] & 0x0F
    return f"{(struct.unpack('>I', h[o:o + 4])[0] & 0x7FFFFFFF) % 1_000_000:06d}"


@pytest.fixture
def ctx():
    t = [1_800_000_000.0]
    m = Memoire()
    c = cp.Comptes(m, SECRET, horloge=lambda: t[0])
    admin = c.amorcer_administration("Administration du Club")   # le tout premier compte, une seule fois
    elever(c, t, admin)                                           # audit I1 : administrer exige le second facteur
    return c, m, t, admin


def elever(c, t, session):
    """Second facteur activé puis session élevée par un code (exigé pour toute action d'administration)."""
    prep = c.preparer_totp(session)
    c.confirmer_totp(session, totp(prep["secret"], t[0]))
    t[0] += 30
    c.elever(session, totp(prep["secret"], t[0]))
    return prep["secret"]


def test_le_vecteur_de_la_rfc_6238_est_respecte():
    # RFC 6238, annexe B : secret ASCII « 12345678901234567890 », T = 59 s → 94287082 (8 chiffres) ; 6 chiffres : 287082
    import base64
    s = base64.b32encode(b"12345678901234567890").decode().rstrip("=")
    assert cp.code_totp(s, 59) == "287082" == totp(s, 59)


def test_invitation_a_usage_unique_et_qui_expire(ctx):
    c, m, t, admin = ctx
    lien = c.inviter(admin, role=cp.MEMBRE, etiquette="membre fictif 1", duree_s=3600)
    session = c.accepter(lien["jeton"], appareil="iPhone de test")
    assert c.verifier(session)["role"] == cp.MEMBRE
    with pytest.raises(NonAuthentifie):
        c.accepter(lien["jeton"], appareil="autre")                      # usage unique
    lien2 = c.inviter(admin, role=cp.MEMBRE, etiquette="membre fictif 2", duree_s=60)
    t[0] += 61
    with pytest.raises(NonAuthentifie):
        c.accepter(lien2["jeton"], appareil="x")                         # expirée
    with pytest.raises(NonAuthentifie):
        c.accepter(lien["jeton"][:-2] + "zz", appareil="x")              # falsifiée


def test_aucun_secret_en_clair_dans_le_journal(ctx):
    c, m, t, admin = ctx
    lien = c.inviter(admin, role=cp.SECRETARIAT, etiquette="Secrétariat 1", duree_s=3600)
    s = c.accepter(lien["jeton"], appareil="Mac")
    prep = c.preparer_totp(s)
    brut = "".join(e.model_dump_json() for e in m.evenements())
    assert lien["jeton"] not in brut and prep["secret"] not in brut and s not in brut
    assert lien["jeton"].split(".")[-1] not in brut


def test_sessions_appareils_et_deconnexion(ctx):
    c, m, t, admin = ctx
    lien = c.inviter(admin, role=cp.MEMBRE, etiquette="membre fictif", duree_s=3600)
    s1 = c.accepter(lien["jeton"], appareil="Téléphone")
    s2 = c.nouvelle_session(s1, appareil="Ordinateur")                  # un second appareil, depuis le premier
    apps = c.mes_appareils(s1)
    assert {a["appareil"] for a in apps} == {"Téléphone", "Ordinateur"} and sum(a["celui_ci"] for a in apps) == 1
    autre = next(a for a in apps if not a["celui_ci"])
    c.deconnecter_appareil(s1, autre["id"])
    with pytest.raises(NonAuthentifie):
        c.verifier(s2)                                                   # l'autre appareil est déconnecté
    c.deconnecter(s1)
    with pytest.raises(NonAuthentifie):
        c.verifier(s1)
    t[0] += cp.DUREE_SESSION_S + 1
    with pytest.raises(NonAuthentifie):
        c.verifier(c.nouvelle_session(admin, appareil="x"))              # admin : session expirée aussi (jamais éternelle)


def test_on_ne_deconnecte_pas_l_appareil_d_un_autre(ctx):
    c, m, t, admin = ctx
    a = c.accepter(c.inviter(admin, role=cp.MEMBRE, etiquette="a", duree_s=60)["jeton"], appareil="A")
    b = c.accepter(c.inviter(admin, role=cp.MEMBRE, etiquette="b", duree_s=60)["jeton"], appareil="B")
    id_b = c.mes_appareils(b)[0]["id"]
    with pytest.raises(Interdit):
        c.deconnecter_appareil(a, id_b)
    assert c.verifier(b)


def test_roles_et_permissions(ctx):
    c, m, t, admin = ctx
    sec = c.accepter(c.inviter(admin, role=cp.SECRETARIAT, etiquette="Secrétariat 1", duree_s=60)["jeton"], appareil="Mac")
    mem = c.accepter(c.inviter(admin, role=cp.MEMBRE, etiquette="m", duree_s=60)["jeton"], appareil="Tél")
    with pytest.raises(Interdit):
        c.inviter(mem, role=cp.MEMBRE, etiquette="x", duree_s=60)          # un membre n'invite pas (en lot 2)
    with pytest.raises(Interdit):
        c.inviter(sec, role=cp.ADMIN, etiquette="x", duree_s=60)           # le secrétariat ne crée pas d'administrateur
    with pytest.raises(Interdit):
        c.attribuer_role(sec, c.verifier(mem)["compte"], cp.SECRETARIAT)   # ni ne change un rôle
    c.attribuer_role(admin, c.verifier(mem)["compte"], cp.SECRETARIAT)
    assert c.verifier(mem)["role"] == cp.SECRETARIAT
    elever(c, t, sec)                                                    # inviter : second facteur exigé (audit I1)
    invite = c.accepter(c.inviter(sec, role=cp.INVITE, etiquette="exposant invité", duree_s=60)["jeton"], appareil="Tél")
    assert c.verifier(invite)["role"] == cp.INVITE


def test_revoquer_un_compte_coupe_toutes_ses_sessions(ctx):
    c, m, t, admin = ctx
    s = c.accepter(c.inviter(admin, role=cp.MEMBRE, etiquette="m", duree_s=60)["jeton"], appareil="A")
    s2 = c.nouvelle_session(s, appareil="B")
    c.revoquer(admin, c.verifier(s)["compte"])
    for x in (s, s2):
        with pytest.raises(NonAuthentifie):
            c.verifier(x)


def test_la_console_exige_un_compte_nominatif_et_le_code_totp(ctx):
    c, m, t, admin = ctx
    sec = c.accepter(c.inviter(admin, role=cp.SECRETARIAT, etiquette="Secrétariat 1", duree_s=60)["jeton"], appareil="Mac")
    with pytest.raises(Interdit, match="double authentification"):
        c.exiger_console(sec)                                             # pas encore de TOTP : refus
    prep = c.preparer_totp(sec)
    assert prep["uri"].startswith("otpauth://totp/") and "secret=" in prep["uri"]
    with pytest.raises(NonAuthentifie):
        c.confirmer_totp(sec, "000000" if totp(prep["secret"], t[0]) != "000000" else "111111")
    c.confirmer_totp(sec, totp(prep["secret"], t[0]))
    with pytest.raises(Interdit, match="code"):
        c.exiger_console(sec)                                             # TOTP actif, session pas encore élevée
    t[0] += 30
    c.elever(sec, totp(prep["secret"], t[0]))
    assert c.exiger_console(sec)["role"] == cp.SECRETARIAT
    with pytest.raises(NonAuthentifie):
        c.elever(sec, totp(prep["secret"], t[0]))                        # un code ne sert qu'une fois (rejeu)
    mem = c.accepter(c.inviter(admin, role=cp.MEMBRE, etiquette="m", duree_s=60)["jeton"], appareil="Tél")
    with pytest.raises(Interdit):
        c.exiger_console(mem)                                             # un membre n'a jamais la console


def test_le_code_totp_tolere_un_pas_de_decalage_pas_plus(ctx):
    c, m, t, admin = ctx
    sec = c.accepter(c.inviter(admin, role=cp.SECRETARIAT, etiquette="S", duree_s=60)["jeton"], appareil="Mac")
    prep = c.preparer_totp(sec)
    c.confirmer_totp(sec, totp(prep["secret"], t[0]))
    t[0] += 300
    c.elever(sec, totp(prep["secret"], t[0] - 30))                       # horloge du téléphone en retard de 30 s
    with pytest.raises(NonAuthentifie):
        c.elever(c.nouvelle_session(sec, appareil="2"), totp(prep["secret"], t[0] - 120))


def test_journal_des_actions_d_administration(ctx):
    c, m, t, admin = ctx
    mem = c.accepter(c.inviter(admin, role=cp.MEMBRE, etiquette="m", duree_s=60)["jeton"], appareil="Tél")
    c.attribuer_role(admin, c.verifier(mem)["compte"], cp.SECRETARIAT)
    c.revoquer(admin, c.verifier(mem)["compte"])
    actions = [x["action"] for x in c.journal_admin(admin)]
    assert actions[-3:] == ["inviter", "attribuer_role", "revoquer"]
    sec = c.accepter(c.inviter(admin, role=cp.SECRETARIAT, etiquette="S", duree_s=60)["jeton"], appareil="Mac")
    with pytest.raises(Interdit):
        c.journal_admin(sec)                                              # réservé à l'administration


def test_tout_survit_a_un_redemarrage(tmp_path):
    """L'état des comptes est un repli du journal : même résultat après relecture (sessions, révocations, TOTP)."""
    t = [1_800_000_000.0]
    f = str(tmp_path / "j.db")
    c = cp.Comptes(Memoire(f), SECRET, horloge=lambda: t[0])
    admin = c.amorcer_administration("Administration")
    elever(c, t, admin)
    s = c.accepter(c.inviter(admin, role=cp.MEMBRE, etiquette="m", duree_s=60)["jeton"], appareil="A")
    s2 = c.nouvelle_session(s, appareil="B")
    c.deconnecter(s2)
    c2 = cp.Comptes(Memoire(f), SECRET, horloge=lambda: t[0])
    assert c2.verifier(s)["role"] == cp.MEMBRE
    with pytest.raises(NonAuthentifie):
        c2.verifier(s2)
    with pytest.raises(Interdit):
        c2.amorcer_administration("deuxième")                             # l'amorçage n'a lieu qu'une fois


def test_limite_par_session(ctx):
    c, m, t, admin = ctx
    s = c.accepter(c.inviter(admin, role=cp.MEMBRE, etiquette="m", duree_s=60)["jeton"], appareil="A")
    for _ in range(cp.LIMITE_ECRITURES_MINUTE):
        c.compter_ecriture(s)
    with pytest.raises(cp.TropDeRequetes):
        c.compter_ecriture(s)
    t[0] += 61
    c.compter_ecriture(s)
