"""ANNÉE 1 · LOT 1 — Fondations de production : le journal sur un stockage interchangeable (SQLite pour la démo,
PostgreSQL pour la production), des migrations avec retour arrière, une sauvegarde et une restauration vérifiées.

PostgreSQL : testé pour de vrai si HACKVS_TEST_PG_URL pointe vers une base jetable (psycopg installé) — sinon ces cas
sont SAUTÉS, et c'est dit (jamais « testé sur PostgreSQL » sans cette variable). Données FICTIVES."""
import json
import os
import threading
from datetime import date

import pytest

from plateforme import migrations, sauvegarde
from plateforme.affirmations import Statut
from plateforme.memoire import Evt, Memoire
from plateforme.stockage import ouvrir

PG = os.environ.get("HACKVS_TEST_PG_URL", "")
J = date(2026, 10, 6)


def _pg_disponible() -> bool:
    if not PG:
        return False
    try:
        import psycopg  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.fixture
def url_pg():
    if not _pg_disponible():
        pytest.skip("PostgreSQL non configuré (HACKVS_TEST_PG_URL) : non testé ici")
    import psycopg
    with psycopg.connect(PG, autocommit=True) as c:          # base jetable : on repart de zéro
        c.execute("DROP TABLE IF EXISTS evenements, journal_meta, schema_migrations")
    return PG


@pytest.fixture(params=["sqlite-memoire", "sqlite-fichier", "postgres"])
def url(request, tmp_path):
    if request.param == "sqlite-memoire":
        return ":memory:"
    if request.param == "sqlite-fichier":
        return str(tmp_path / "journal.db")
    return request.getfixturevalue("url_pg")


def _e(n: int, type_: str = "TEST") -> Evt:
    return Evt(type=type_, le=J, acteurs=[f"p{n}"], donnees={"n": n}, statut=Statut.SYNTHETIQUE)


# ------------------------------------------------------------------ le même journal, quel que soit le moteur
def test_le_journal_se_comporte_pareil_sur_chaque_moteur(url):
    m = Memoire(url)
    a = m.ajouter(_e(1))
    assert m.ajouter(_e(1)).seq == a.seq                      # idempotent
    m.ajouter(_e(2, "AUTRE"))
    assert [e.donnees["n"] for e in m.evenements()] == [1, 2]
    assert [e.donnees["n"] for e in m.evenements("AUTRE")] == [2]
    with pytest.raises(RuntimeError):
        with m.transaction():
            m.ajouter(_e(3))
            raise RuntimeError("tout ou rien")
    assert [e.donnees["n"] for e in m.evenements()] == [1, 2]  # la transaction annulée n'a rien laissé
    with m.transaction():
        m.ajouter(_e(4))
        m.ajouter(_e(5))
    assert len(m.evenements()) == 4
    v = m.version()
    m.vider()
    assert m.evenements() == [] and m.version() != v


def test_deux_lecteurs_du_meme_journal_voient_les_memes_faits(url):
    if url == ":memory:":
        pytest.skip("en mémoire, chaque connexion a sa propre base")
    a, b = Memoire(url), Memoire(url)
    a.vider()
    a.ajouter(_e(1))
    assert [e.donnees["n"] for e in b.evenements()] == [1]


def test_ecritures_concurrentes_sans_perte(url):
    m = Memoire(url)
    m.vider()

    def ecrire(k):
        for i in range(25):
            m.ajouter(_e(k * 100 + i))
    fils = [threading.Thread(target=ecrire, args=(k,)) for k in range(4)]
    [f.start() for f in fils]
    [f.join() for f in fils]
    assert len(m.evenements()) == 100


def test_le_moteur_se_choisit_par_l_adresse():
    assert ouvrir(":memory:").dialecte == "sqlite"
    with pytest.raises(ValueError):
        ouvrir("mysql://ailleurs/base")


def test_postgres_choisi_par_son_adresse(url_pg):
    assert ouvrir(url_pg).dialecte == "postgres"


# ------------------------------------------------------------------ migrations avec retour arrière
def test_migrations_montent_et_redescendent_sans_perdre_le_journal(url):
    b = ouvrir(url)
    migrations.migrer(b)
    haut = migrations.niveau(b)
    assert haut == migrations.DERNIERE >= 2
    m = Memoire(url) if url != ":memory:" else None
    if m:
        m.ajouter(_e(7))
    migrations.migrer(b, cible=1)                              # retour arrière : les métadonnées partent, pas le journal
    assert migrations.niveau(b) == 1
    migrations.migrer(b)
    assert migrations.niveau(b) == haut
    if m:
        assert [e.donnees["n"] for e in Memoire(url).evenements()] == [7]


def test_descendre_sous_le_journal_exige_une_confirmation(url):
    b = ouvrir(url)
    migrations.migrer(b)
    with pytest.raises(migrations.Destructeur):
        migrations.migrer(b, cible=0)
    migrations.migrer(b, cible=0, confirmer_destruction=True)
    assert migrations.niveau(b) == 0
    migrations.migrer(b)
    assert migrations.niveau(b) == migrations.DERNIERE


def test_un_journal_d_avant_les_migrations_est_adopte_sans_perte(tmp_path):
    """Le journal de la démo (créé avant ce lot) n'a pas de table de migrations : il est adopté tel quel."""
    import sqlite3
    f = tmp_path / "ancien.db"
    c = sqlite3.connect(f)
    c.execute("CREATE TABLE evenements (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE, donnees TEXT)")
    c.execute("INSERT INTO evenements (id, donnees) VALUES (?, ?)", (_e(9).id, _e(9).model_dump_json(exclude={"seq"})))
    c.commit()
    c.close()
    m = Memoire(str(f))
    assert [e.donnees["n"] for e in m.evenements()] == [9]
    assert migrations.niveau(ouvrir(str(f))) == migrations.DERNIERE


# ------------------------------------------------------------------ sauvegarde et restauration
def test_sauvegarde_puis_restauration_meme_empreinte(url, tmp_path):
    src = Memoire(url)
    src.vider()
    for i in range(30):
        src.ajouter(_e(i, "A" if i % 2 else "B"))
    fichier = tmp_path / "sauvegarde.jsonl"
    entete = sauvegarde.sauvegarder(src, fichier)
    assert entete["nombre"] == 30 and entete["empreinte"] == src.empreinte()
    cible = Memoire(str(tmp_path / "restaure.db"))
    sauvegarde.restaurer(cible, fichier)
    assert cible.empreinte() == src.empreinte()
    assert [e.type for e in cible.evenements()] == [e.type for e in src.evenements()]


def test_restauration_d_un_moteur_vers_l_autre(url_pg, tmp_path):
    src = Memoire(str(tmp_path / "demo.db"))
    for i in range(10):
        src.ajouter(_e(i))
    sauvegarde.sauvegarder(src, tmp_path / "s.jsonl")
    pg = Memoire(url_pg)
    sauvegarde.restaurer(pg, tmp_path / "s.jsonl")
    assert pg.empreinte() == src.empreinte()


def test_la_restauration_refuse_un_fichier_altere_ou_une_cible_non_vide(tmp_path):
    src = Memoire(str(tmp_path / "a.db"))
    for i in range(5):
        src.ajouter(_e(i))
    f = tmp_path / "s.jsonl"
    sauvegarde.sauvegarder(src, f)
    lignes = f.read_text(encoding="utf-8").splitlines()
    altere = json.loads(lignes[2])
    altere["donnees"]["n"] = 999
    (tmp_path / "altere.jsonl").write_text("\n".join([lignes[0], lignes[1], json.dumps(altere), *lignes[3:]]) + "\n", encoding="utf-8")
    with pytest.raises(sauvegarde.SauvegardeInvalide):
        sauvegarde.restaurer(Memoire(str(tmp_path / "b.db")), tmp_path / "altere.jsonl")
    assert Memoire(str(tmp_path / "b.db")).evenements() == []          # rien d'écrit : tout ou rien
    with pytest.raises(sauvegarde.SauvegardeInvalide):
        sauvegarde.restaurer(src, f)                                     # cible non vide : jamais de mélange


def test_le_serveur_complet_demarre_sur_postgres_et_se_dit_pret(url_pg):
    """Intégration : le vrai serveur (sous-processus), le journal du Club sur PostgreSQL, /sante/pret à 200."""
    import urllib.request

    from tests.test_e2e_scene import serveur
    with serveur(HACKVS_ESSAIS_DB=url_pg, HACKVS_FOIRE="1") as base:
        d = json.load(urllib.request.urlopen(base + "/sante/pret", timeout=10))
        assert d["pret"] is True and d["faits"] > 0
    with serveur(HACKVS_ESSAIS_DB=url_pg, HACKVS_FOIRE="1") as base:    # redémarrage : le journal est REPRIS
        assert json.load(urllib.request.urlopen(base + "/sante/pret", timeout=10))["faits"] >= d["faits"]
