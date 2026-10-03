"""ANNÉE 1 — correctifs de l'audit des lots 2 (comptes) et 3 (espace membre). Chaque cas reproduit un constat de
l'audit (docs/annee-1/AUDIT_LOT23.md) ; il était ROUGE avant le correctif. Données FICTIVES."""
import json
from datetime import timedelta

import pytest

from app.taxonomy import charger_taxonomie
from intelligence import comptes as cp
from intelligence import espace_membre as em
from intelligence import monde_demo as md
from intelligence.demo import Demo
from intelligence.erreurs import Interdit
from plateforme.memoire import Evt, Memoire
from plateforme.affirmations import Statut

TAX = charger_taxonomie()


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    return tmp_path


def _lire_tout(c):
    """Toutes les lectures que l'audit a vues casser après une purge."""
    c.banc.offres()
    c.projection_capacites()
    c.empreinte_etat()
    c.vues_capacites.console()
    for p in c.r.profils[:20]:
        c.asks_pour(p.id)
    for e in c.journal.evenements("ESSAI_VERSION"):
        c.banc.protocole(e.donnees.get("essai") or e.acteurs[0])


# ------------------------------------------------------------------ B1 : la purge ne casse rien, même scène jouée
@pytest.mark.parametrize("qui", [md.PAULINE, md.LEA, md.SOPHIE])
def test_b1_apres_purge_tout_se_lit_encore_et_se_rejoue(env, qui):
    demo = Demo(TAX)
    demo.rejouer(9)                                     # la scène entière : offres, essais, protocoles, accords
    c = demo.club
    em.effacer_definitivement(c, qui)
    _lire_tout(c)
    _lire_tout(Demo(TAX, reprendre=True).club)


# ------------------------------------------------------------------ I3 : les copies de ses textes partent aussi
def test_i3_les_textes_recopies_chez_les_autres_sont_purges(env):
    demo = Demo(TAX)
    demo.rejouer(9)
    c = demo.club
    quoi = {e.donnees["offre"]["quoi"] for e in c.journal.evenements("OFFRE") if e.acteurs == [md.LEA]}
    assert quoi and any(t in json.dumps([e.model_dump(mode="json") for e in c.journal.evenements() if md.LEA not in e.acteurs],
                                        ensure_ascii=False) for t in quoi)      # copiées ailleurs : le cas existe
    em.effacer_definitivement(c, md.LEA)
    brut = json.dumps([e.model_dump(mode="json") for e in c.journal.evenements()], ensure_ascii=False)
    assert not any(t in brut for t in quoi)


# ------------------------------------------------------------------ B2 : deux purges le même jour
def test_b2_deux_effacements_le_meme_jour(env):
    c = Demo(TAX).club
    a = em.effacer_definitivement(c, md.PAULINE)
    b = em.effacer_definitivement(c, md.MARKUS)
    assert a["faits_purges"] >= 1 and b["faits_purges"] >= 1
    assert len(c.journal.evenements("PURGE")) == 2
    assert c.coffre.identite(md.MARKUS) is None


def test_b2_une_purge_qui_echoue_ne_laisse_pas_un_effacement_a_moitie(env, monkeypatch):
    c = Demo(TAX).club
    monkeypatch.setattr(c.journal, "reecrire", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("panne simulée")))
    with pytest.raises(RuntimeError):
        em.effacer_definitivement(c, md.PAULINE)
    assert c.coffre.identite(md.PAULINE) is not None                     # rien d'effacé : on peut recommencer
    assert not [e for e in c.journal.evenements("EFFACEMENT") if md.PAULINE in e.acteurs]


# ------------------------------------------------------------------ B3 : la pause bloque toute sollicitation
def test_b3_en_pause_ni_asks_ni_decouvertes_ni_sollicitable(env):
    c = Demo(TAX).club
    avec = next(p.id for p in c.r.profils if c.sollicitable(p.id) and c.asks_pour(p.id))
    em.mettre_en_pause(c, avec, c.jour + timedelta(days=30))
    assert not c.sollicitable(avec) and c.asks_pour(avec) == []
    nommes = sorted({m for o in c.scanner(force=True)["opportunites"] for m in o.consentements})
    for pid in nommes:
        em.mettre_en_pause(c, pid, c.jour + timedelta(days=30))
    encore = {m for o in c.scanner(force=True)["opportunites"] for m in o.consentements} & set(nommes)
    assert not encore


# ------------------------------------------------------------------ I5 : un autre lecteur ne garde pas le texte purgé
def test_i5_un_second_lecteur_voit_la_purge(tmp_path):
    f = str(tmp_path / "j.db")
    a, b = Memoire(f), Memoire(f)
    a.ajouter(Evt(type="NOTE", le=demo_jour(), acteurs=["x"], donnees={"texte": "SECRET à purger"}, statut=Statut.DECLARE))
    assert b.evenements()[0].donnees["texte"] == "SECRET à purger"
    a.reecrire(lambda e: e.model_copy(update={"donnees": {"texte": "[effacé]"}}))
    assert "SECRET" not in json.dumps([e.donnees for e in b.evenements()])


def demo_jour():
    from datetime import date
    return date(2026, 10, 6)


# ------------------------------------------------------------------ I4 : SQLite efface vraiment les octets
def test_i4_sqlite_secure_delete_est_allume(tmp_path):
    m = Memoire(str(tmp_path / "j.db"))
    assert m._db.executer("PRAGMA secure_delete").fetchone()[0] == 1


# ------------------------------------------------------------------ I6 : export complet (droit d'accès)
def test_i6_l_export_contient_mon_identite_et_mes_notes(env):
    c = Demo(TAX).club
    c.capturer(md.PAULINE, "Rappeler le fournisseur de cartons lundi.", None)
    x = em.exporter(c, md.PAULINE)
    ident = c.coffre.identite(md.PAULINE)
    texte = json.dumps(x, ensure_ascii=False)
    assert ident.nom in texte and ident.courriel in texte and "fournisseur de cartons" in texte


# ------------------------------------------------------------------ B4, I1 : comptes
@pytest.fixture
def comptes():
    t = [1_800_000_000.0]
    c = cp.Comptes(Memoire(), b"a" * 48, horloge=lambda: t[0])
    admin = c.amorcer_administration("Administration")
    return c, t, admin


def _activer(c, t, s):
    prep = c.preparer_totp(s)
    c.confirmer_totp(s, cp.code_totp(prep["secret"], t[0]))
    t[0] += 30
    c.elever(s, cp.code_totp(prep["secret"], t[0]))
    return prep["secret"]


def test_b4_le_second_facteur_ne_se_remplace_pas_avec_la_seule_session(comptes):
    c, t, admin = comptes
    _activer(c, t, admin)
    s = c.accepter(c.inviter(admin, role=cp.SECRETARIAT, etiquette="S", duree_s=600)["jeton"], appareil="x")
    _activer(c, t, s)
    t[0] += cp.DUREE_ELEVATION_S + 1                                  # l'élévation est retombée
    vole = c.nouvelle_session(s, appareil="voleur")                    # quelqu'un n'a que la session
    with pytest.raises(Interdit):
        c.preparer_totp(vole)


def test_i1_l_administration_exige_la_console(comptes):
    c, t, admin = comptes
    with pytest.raises(Interdit):
        c.inviter(admin, role=cp.ADMIN, etiquette="x", duree_s=60)     # pas de TOTP : refusé
    _activer(c, t, admin)
    c.inviter(admin, role=cp.MEMBRE, etiquette="m", duree_s=60)       # élevée : permis


def test_i1_le_dernier_administrateur_reste(comptes):
    c, t, admin = comptes
    _activer(c, t, admin)
    moi = c.verifier(admin)["compte"]
    with pytest.raises(Interdit):
        c.revoquer(admin, moi)
    with pytest.raises(Interdit):
        c.attribuer_role(admin, moi, cp.MEMBRE)


def test_i4_postgresql_le_texte_purge_quitte_les_fichiers_de_la_table():
    """Sur un PostgreSQL LOCAL (fichiers lisibles) : après la réécriture, le texte n'est plus dans le fichier de la table
    (VACUUM FULL). Le WAL garde l'ancienne version le temps de sa rétention : c'est documenté, pas caché."""
    import os
    from pathlib import Path
    url = os.environ.get("HACKVS_TEST_PG_URL", "")
    if not url:
        pytest.skip("PostgreSQL non configuré : non testé ici")
    import psycopg
    with psycopg.connect(url, autocommit=True) as cx:
        donnees = Path(cx.execute("SHOW data_directory").fetchone()[0])
    if not donnees.is_dir():
        pytest.skip("PostgreSQL distant (fichiers illisibles d'ici) : non testé ici")
    with psycopg.connect(url, autocommit=True) as cx:
        cx.execute("DROP TABLE IF EXISTS evenements, journal_meta, schema_migrations")
    m = Memoire(url)
    m.ajouter(Evt(type="NOTE", le=demo_jour(), acteurs=["x"], donnees={"texte": "ZORGLUB secret à purger"}, statut=Statut.DECLARE))
    with psycopg.connect(url, autocommit=True) as cx:
        cx.execute("CHECKPOINT")                           # les pages quittent la mémoire pour le fichier
        avant = donnees / cx.execute("SELECT pg_relation_filepath('evenements')").fetchone()[0]
    assert b"ZORGLUB" in avant.read_bytes()                # contre-épreuve : le texte est bien sur le disque avant
    m.reecrire(lambda e: e.model_copy(update={"donnees": {"texte": "[effacé]"}}))
    with psycopg.connect(url, autocommit=True) as cx:
        cx.execute("CHECKPOINT")
        chemin = cx.execute("SELECT pg_relation_filepath('evenements')").fetchone()[0]
    fichier = donnees / chemin
    assert fichier.exists() and b"ZORGLUB" not in fichier.read_bytes()
