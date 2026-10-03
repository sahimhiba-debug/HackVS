"""AUDIT DE NUIT (03.10, sur e2b1745) — tests ROUGES : chacun démontre un défaut consigné dans
docs/audit/AUDIT_NUIT.md et échoue sur e2b1745. Ils passeront quand le correctif proposé sera appliqué.
Données FICTIVES."""
import pytest

from app.taxonomy import charger_taxonomie
from intelligence import annonces
from intelligence import monde_demo as md
from intelligence.demo import Demo
from intelligence.salle import Salle

TAX = charger_taxonomie()


@pytest.fixture
def c(monkeypatch, tmp_path):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    return Demo(TAX).club


def test_audit_d1_la_salle_ouverte_avant_le_pitch_ne_bascule_pas_avant_l_invitation():
    """D1 — runbook v2 § 1.3 : la salle est ouverte à H-30 et 2 téléphones de l'équipe la scannent. 30 min plus tard,
    au moment de « Sortez vos téléphones », l'écran géant ne doit pas déjà réclamer la démo scriptée (salle-ecran.html
    redirige alors vers /etabli 5 s après). Sur e2b1745 : bascule = True dès la 61e seconde après l'ouverture."""
    t = [0.0]
    s = Salle(b"x" * 32, horloge=lambda: t[0])
    jeton = s.ouvrir()["jeton_salle"]
    for _ in range(2):
        s.entrer(jeton)
    t[0] = 30 * 60
    assert s.ecran()["bascule"] is False


def test_audit_d2_le_nom_d_entreprise_d_un_invite_reste_hors_du_journal(c):
    """D2 — « le nom d'entreprise confirmé hors du journal » : vrai pour la carte (identites_profil), FAUX pour le passe
    découverte — DECOUVERTE_DECLARATION écrit `entreprise` dans le journal append-only, sans route d'effacement."""
    p = c.decouverte.emettre("stand")
    inv = c.decouverte.activer(p["jeton"])["invite"]
    c.decouverte.declarer(inv, "Fromagerie Témoin d'Audit SA", "transport", "Haute-Savoie")
    contenu = [str(e.donnees) for e in c.journal.evenements("DECOUVERTE_DECLARATION")]
    assert contenu and not any("Fromagerie Témoin" in x for x in contenu)


def test_audit_d3_seuil_des_invites_compte_en_entreprises_distinctes(c):
    """D3 — le seuil « < 3 » se compte en ENTREPRISES distinctes partout ; Decouverte.statistiques compte des PASSES :
    trois passes de la même entreprise affichent « 3 invités actifs »."""
    for _ in range(3):
        p = c.decouverte.emettre("stand")
        inv = c.decouverte.activer(p["jeton"])["invite"]
        c.decouverte.declarer(inv, "Même Entreprise SA", "transport", "Haute-Savoie")
    st = c.decouverte.statistiques(None, 3)
    assert st["actifs"] == "< 3"


def test_audit_d4_un_chiffre_d_annonce_n_est_jamais_reattribue(c):
    """D4 — le chiffre vaut len(annonces visibles) + 1 ; un auteur effacé fait baisser ce nombre, et l'annonce suivante
    reprend le chiffre d'une annonce existante, qui disparaît (écrasée dans _annonces)."""
    a1 = annonces.publier(c, md.PAULINE, "Cherche un local de stockage à Martigny.")["chiffre"]
    a2 = annonces.publier(c, md.MARKUS, "Cherche un traducteur allemand pour un salon.")["chiffre"]
    assert (a1, a2) == ("A-001", "A-002")
    c.effacer(md.PAULINE)
    a3 = annonces.publier(c, md.LEA, "Cherche une salle pour 20 personnes.")["chiffre"]
    assert a3 != a2
    assert [x["chiffre"] for x in annonces.mes_annonces(c, md.MARKUS)] == [a2]


def test_audit_d5_le_jeton_de_la_salle_ne_sort_pas_par_le_tunnel(monkeypatch):
    """D5 — /qr/salle.txt et /qr/salle.svg sont publics : à travers le tunnel (adresse *.ts.net / trycloudflare.com,
    découvrable), n'importe qui lit le jeton de la salle et peut occuper les 80 places (plafond) avant le pitch.
    Attendu : servis seulement à cette machine (est_local) ou avec le jeton de console."""
    from fastapi.testclient import TestClient

    from app.main import app
    monkeypatch.delenv("HACKVS_CONSOLE_JETON", raising=False)
    cl = TestClient(app)
    console = {"X-Pulse-Console": "1"}
    cl.post("/api/pulse/console/salle/purger", headers=console)
    cl.post("/api/pulse/console/salle/ouvrir", headers=console)
    try:
        r = cl.get("/qr/salle.txt", headers={"Tailscale-Funnel-Request": "?1", "X-Forwarded-For": "203.0.113.9"})
        assert "#s=" not in r.text
    finally:
        cl.post("/api/pulse/console/salle/purger", headers=console)
