"""PACK « DEUX DOUBLE-CLICS » (jour J) : le film trouvé seul sur le Bureau, le jeton rangé hors du dépôt, la check-list à
voyants (terminal et page locale /preflight), l'écran de la salle intégrable dans le deck — et seulement par le deck.
Aucune vidéo réelle : des octets d'en-tête MP4 suivis de zéros."""
import os
import stat
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import jour_j as jj

RACINE = Path(__file__).resolve().parents[2]
MO = 1024 * 1024


def _video(chemin: Path, taille: int = 2 * MO, entete: bytes = b"\x00\x00\x00\x20ftypisom") -> Path:
    chemin.write_bytes(entete + b"\x00" * (taille - len(entete)))
    return chemin


# ------------------------------------------------------------------ le film sur le Bureau
def test_aucune_video_sur_le_bureau_est_un_voyant_rouge(tmp_path):
    (tmp_path / "notes.txt").write_text("x")
    r = jj.chercher_film(tmp_path)
    assert r["couleur"] == "rouge" and r["message"] == "FILM ABSENT DU BUREAU" and r["source"] is None


def test_une_seule_video_est_trouvee_et_les_sous_dossiers_sont_ignores(tmp_path):
    _video(tmp_path / "Film Club Pulse.mp4")
    (tmp_path / "rushes").mkdir()
    _video(tmp_path / "rushes" / "brouillon.mp4")
    r = jj.chercher_film(tmp_path)
    assert r["couleur"] == "vert" and r["source"].name == "Film Club Pulse.mp4"


def test_plusieurs_videos_rouge_avec_la_liste_sans_jamais_deviner(tmp_path):
    _video(tmp_path / "a.mp4")
    _video(tmp_path / "b.M4V")
    r = jj.chercher_film(tmp_path)
    assert r["couleur"] == "rouge" and r["source"] is None
    assert "a.mp4" in r["message"] and "b.M4V" in r["message"]


def test_un_mov_est_orange(tmp_path):
    _video(tmp_path / "film.mov", entete=b"\x00\x00\x00\x14ftypqt  ")
    r = jj.chercher_film(tmp_path)
    assert r["couleur"] == "orange" and r["source"].name == "film.mov" and "Chrome" in r["message"]


def test_une_icone_icloud_n_est_pas_un_film(tmp_path):
    (tmp_path / ".film.mp4.icloud").write_bytes(b"bplist00")
    r = jj.chercher_film(tmp_path)
    assert r["couleur"] == "rouge" and "iCloud" in r["message"] and r["source"] is None


def test_une_icone_icloud_a_cote_d_un_film_est_une_ambiguite(tmp_path):
    _video(tmp_path / "film.mp4")
    (tmp_path / ".autre.mov.icloud").write_bytes(b"bplist00")
    assert jj.chercher_film(tmp_path)["couleur"] == "rouge"


def test_un_fichier_trop_petit_ou_qui_n_est_pas_une_video_est_rouge(tmp_path):
    (tmp_path / "film.mp4").write_bytes(b"\x00\x00\x00\x20ftypisom")
    assert jj.chercher_film(tmp_path)["couleur"] == "rouge"
    _video(tmp_path / "film.mp4", entete=b"<html>pas une video")
    r = jj.chercher_film(tmp_path)
    assert r["couleur"] == "rouge" and "vidéo" in r["message"]


def test_la_copie_n_est_refaite_que_si_le_film_a_change(tmp_path):
    src = _video(tmp_path / "film.mp4")
    cible = tmp_path / "deck" / "film.mp4"
    assert jj.copier_film(src, cible) is True and cible.read_bytes() == src.read_bytes()
    assert jj.copier_film(src, cible) is False                      # même taille, même empreinte : rien
    donnees = bytearray(src.read_bytes())
    donnees[-1] = 1                                                 # même taille, contenu différent : recopié
    src.write_bytes(bytes(donnees))
    assert jj.copier_film(src, cible) is True and cible.read_bytes() == src.read_bytes()


def test_le_film_du_deck_est_ignore_par_git():
    assert jj.film_ignore_par_git(RACINE) is True


def test_preparer_le_film_copie_et_note_le_film_hors_du_depot(tmp_path):
    bureau, dossier = tmp_path / "Bureau", tmp_path / "clubpulse"
    bureau.mkdir()
    _video(bureau / "film.mp4")
    cible = tmp_path / "deck" / "film.mp4"
    v = jj.preparer_film(bureau, cible, RACINE, dossier)
    assert v.couleur == "vert" and cible.exists() and "copié" in v.detail
    assert jj.preparer_film(bureau, cible, RACINE, dossier).detail.count("déjà à jour") == 1
    assert jj.voyant_film(bureau, cible, dossier).couleur == "vert"
    (bureau / "film.mp4").unlink()
    assert jj.voyant_film(bureau, cible, dossier).couleur == "rouge"


# ------------------------------------------------------------------ le jeton de la console
def test_le_jeton_est_cree_une_fois_hors_du_depot_en_600(tmp_path):
    dossier = tmp_path / ".clubpulse"
    j = jj.jeton(dossier)
    f = dossier / "jeton"
    assert len(j) >= 16 and f.read_text().strip() == j
    assert stat.S_IMODE(f.stat().st_mode) == 0o600 and stat.S_IMODE(dossier.stat().st_mode) == 0o700
    assert jj.jeton(dossier) == j                                    # réutilisé, jamais régénéré en silence
    os.chmod(f, 0o644)
    jj.jeton(dossier)
    assert stat.S_IMODE(f.stat().st_mode) == 0o600                  # droits réparés


def test_le_jeton_refuse_un_dossier_dans_le_depot():
    with pytest.raises(ValueError):
        jj.jeton(RACINE / "prototype" / "var" / "clubpulse-test")


# ------------------------------------------------------------------ voyants et verdict
def test_secteur_lu_dans_pmset():
    assert jj.voyant_secteur("Now drawing from 'AC Power'\n -InternalBattery-0 100%; charged").couleur == "vert"
    assert jj.voyant_secteur("Now drawing from 'Battery Power'\n -InternalBattery-0 80%").couleur == "rouge"
    assert jj.voyant_secteur(None).couleur == "orange"


def test_salle_reinitialisee_ou_deja_servie():
    assert jj.voyant_salle(None).couleur == "vert"                   # jamais créée depuis le lancement : vierge
    assert jj.voyant_salle({"ouverte": True, "invitee": False, "demande": None, "vue": "salle", "participants": "< 3"}).couleur == "vert"
    deja = jj.voyant_salle({"ouverte": True, "invitee": True, "demande": {"titre": "x"}, "vue": "salle", "participants": 7})
    assert deja.couleur == "rouge" and "Réinitialiser" in deja.detail
    assert jj.voyant_salle({"injoignable": True}).couleur == "rouge"


def _voyants(**rouges):
    cles = ("film", "serveur", "public", "deck", "secteur", "salle")
    return [jj.Voyant(c, "rouge" if c in rouges else "vert", c, rouges.get(c, "ok")) for c in cles]


def test_feu_vert_v2_seulement_si_tout_est_vert():
    assert jj.verdict(_voyants())[0] == "FEU VERT v2"
    texte, raisons = jj.verdict(_voyants(public="adresse publique injoignable"))
    assert texte == "PASSER EN v1" and any("adresse publique" in r for r in raisons)
    texte, _ = jj.verdict([*_voyants()[:-1], jj.Voyant("salle", "orange", "salle", "?")])
    assert texte == "PASSER EN v1"


def test_le_film_absent_ne_change_pas_la_version_mais_rappelle_le_plan_b():
    """v1 et v2 lisent le MÊME film : son absence ne se règle pas en passant en v1 — le deck bascule seul sur son plan B."""
    texte, raisons = jj.verdict(_voyants(film="FILM ABSENT DU BUREAU"))
    assert texte == "FEU VERT v2"
    assert any("plan B raconté" in r for r in raisons)


def test_le_texte_du_terminal_porte_chaque_voyant_et_le_verdict_en_derniere_ligne():
    t = jj.en_texte(_voyants(public="adresse publique injoignable"), couleurs=False)
    lignes = [x for x in t.splitlines() if x.strip()]
    assert lignes[-1].startswith("PASSER EN v1") and "ROUGE" in t and "VERT" in t


def test_controles_complets_avec_sondes_injectees(tmp_path):
    bureau = tmp_path / "Bureau"
    bureau.mkdir()
    vus = []
    vs = jj.controles(bureau=bureau, cible=tmp_path / "film.mp4", dossier=tmp_path / "d", base_locale="http://127.0.0.1:1",
                      base_publique="https://clubpulse.example", deck_url="http://127.0.0.1:2/v2.html",
                      salle=None, sonde=lambda u: vus.append(u) or True, pmset=lambda: "Now drawing from 'AC Power'")
    assert [v.cle for v in vs] == ["film", "serveur", "public", "deck", "secteur", "salle"]
    assert "https://clubpulse.example/sante" in vus and "http://127.0.0.1:2/v2.html" in vus
    assert {v.cle: v.couleur for v in vs}["film"] == "rouge"
    assert jj.verdict(vs)[0] == "FEU VERT v2"


# ------------------------------------------------------------------ la page /preflight : cette machine seulement
@pytest.fixture
def client(monkeypatch, tmp_path):
    from app import main
    monkeypatch.setenv("CLUBPULSE_BUREAU", str(tmp_path))
    monkeypatch.setenv("CLUBPULSE_DOSSIER", str(tmp_path / "d"))
    monkeypatch.setattr(jj, "sonde_http", lambda url, delai=3.0: True)
    return TestClient(main.app)


def test_preflight_sert_la_check_list_a_cette_machine(client):
    r = client.get("/preflight.json")
    assert r.status_code == 200
    d = r.json()
    assert [v["cle"] for v in d["voyants"]] == ["film", "serveur", "public", "deck", "secteur", "salle"]
    assert d["verdict"] in ("FEU VERT v2", "PASSER EN v1")
    page = client.get("/preflight")
    assert page.status_code == 200 and "preflight.json" in page.text


def test_preflight_ne_sort_jamais_par_le_tunnel(client):
    """Le nom du film du Bureau et l'état de la machine ne regardent que cette machine."""
    relais = {"Tailscale-Funnel-Request": "?1", "X-Forwarded-For": "203.0.113.9"}
    assert client.get("/preflight.json", headers=relais).status_code == 404
    assert client.get("/preflight", headers=relais).status_code == 404


# ------------------------------------------------------------------ l'écran de la salle, intégré au deck (et à lui seul)
def test_l_ecran_de_la_salle_s_integre_seulement_dans_le_deck_local():
    from app.main import app
    cl = TestClient(app)
    for chemin in ("/salle/ecran", "/etabli"):                     # /etabli : la bascule scriptée y mène, dans le cadre
        r = cl.get(chemin)
        csp = r.headers["content-security-policy"]
        assert "frame-ancestors 'self' http://127.0.0.1:8765 http://localhost:8765;" in csp, chemin
        assert "x-frame-options" not in r.headers, chemin            # sinon SAMEORIGIN l'emporte dans certains navigateurs
    for chemin in ("/app", "/salle/regie", "/console", "/salle"):   # tout le reste : jamais intégrable ailleurs
        r = cl.get(chemin)
        assert "frame-ancestors 'self';" in r.headers["content-security-policy"], chemin
        assert r.headers["x-frame-options"] == "SAMEORIGIN", chemin
