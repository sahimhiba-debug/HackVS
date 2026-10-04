"""ANNÉE 1 · audit des lots 9-10 (sous-agent, 04.10) : chaque constat corrigé a d'abord un test rouge ici.
Données FICTIVES."""
import hashlib
import json
import secrets
from datetime import datetime, timezone

import pytest

from app.taxonomy import charger_taxonomie
from intelligence import attestations as at
from intelligence import foire_allumage as fa
from intelligence.demo import Demo
from intelligence.erreurs import ErreurMetier

TAX = charger_taxonomie()
VRAI = at.Emetteur(b"secret-du-serveur" * 2)


def _app(monkeypatch, tmp_path, **env):
    from fastapi import FastAPI

    from app.pulse_api import creer_routeur
    for k, v in ({"HACKVS_ESSAIS_DB": str(tmp_path / "j.db"), "HACKVS_SECRET": "s" * 40, "HACKVS_FOIRE": "1"} | env).items():
        monkeypatch.setenv(k, v)
    routeur = creer_routeur(TAX)
    app = FastAPI()
    app.include_router(routeur)
    app.state.routeur = routeur
    return app


def _divulgation(nom, valeur):
    d = at._b64(json.dumps([at._b64(secrets.token_bytes(16)), nom, valeur]).encode())
    return d, at._b64(hashlib.sha256(d.encode()).digest())


def _signer(emetteur, corps_en_plus, divulgations):
    t = at.maintenant_s()
    corps = {"iss": emetteur.did, "vct": at.VCT, "iat": t, "nbf": t, "exp": t + 3600,
             "_sd": sorted(h for _, h in divulgations), "_sd_alg": "sha-256"} | corps_en_plus
    ent = {"alg": "ES256", "typ": "vc+sd-jwt", "kid": emetteur.did + "#0"}
    signe = at._b64(json.dumps(ent).encode()) + "." + at._b64(json.dumps(corps).encode())
    return "~".join([signe + "." + emetteur._signer(signe.encode()), *(d for d, _ in divulgations)]) + "~"


# ------------------------------------------------------------------ B1 : émetteur attendu, noms réservés, doublons
def test_b1_une_cle_etrangere_n_est_jamais_valide():
    pirate = at.Emetteur(secrets.token_bytes(32))
    sd = pirate.emettre_affirmations({"titre": "Accord jamais donné", "statut": "valable"})
    assert at.verifier(sd, emetteurs={VRAI.did})["valide"] is False
    assert at.verifier(VRAI.emettre_affirmations({"titre": "vrai"}), emetteurs={VRAI.did})["valide"] is True


def test_b1_sans_emetteur_de_confiance_rien_n_est_valide():
    with pytest.raises(TypeError):
        at.verifier(VRAI.emettre_affirmations({"titre": "vrai"}))           # l'émetteur attendu est OBLIGATOIRE


@pytest.mark.parametrize("nom", ["iss", "vct", "iat", "nbf", "exp", "cnf", "status", "_sd", "_sd_alg", "..."])
def test_b1_une_divulgation_ne_peut_pas_ecraser_une_affirmation_reservee(nom):
    sd = _signer(VRAI, {}, [_divulgation(nom, "x"), _divulgation("titre", "t")])
    r = at.verifier(sd, emetteurs={VRAI.did})
    assert r["valide"] is False and "réservé" in r["raison"]


def test_b1_divulgation_dupliquee_ou_nom_repete_refuses():
    sd = VRAI.emettre_affirmations({"titre": "t", "statut": "valable"})
    jwt, *ds = sd.split("~")
    assert at.verifier("~".join([jwt, ds[0], ds[0]]) + "~", emetteurs={VRAI.did})["valide"] is False
    sd2 = _signer(VRAI, {}, [_divulgation("statut", "valable"), _divulgation("statut", "retire")])
    assert at.verifier(sd2, emetteurs={VRAI.did})["valide"] is False


def test_b1_la_route_publique_ne_reconnait_que_l_emetteur_du_serveur(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    client = TestClient(_app(monkeypatch, tmp_path, HACKVS_EID="1"))
    pirate = at.Emetteur(secrets.token_bytes(32))
    r = client.post("/api/pulse/attestations/verifier", json={"sd_jwt": pirate.emettre_affirmations({"titre": "faux"})})
    assert r.status_code == 200 and r.json()["valide"] is False


# ------------------------------------------------------------------ I1 : jamais d'erreur 500 sur la route publique
def _brut(entete, corps, divulgations=()):
    h = at._b64(json.dumps(entete).encode())
    p = at._b64(json.dumps(corps).encode())
    return f"{h}.{p}." + at._b64(b"\0" * 64) + "~" + "~".join(divulgations) + "~"


def _corps_signe(corps, divulgations=()):
    ent = {"alg": "ES256", "typ": "vc+sd-jwt", "kid": VRAI.did + "#0"}
    signe = at._b64(json.dumps(ent).encode()) + "." + at._b64(json.dumps(corps).encode())
    return "~".join([signe + "." + VRAI._signer(signe.encode()), *divulgations]) + "~"


@pytest.mark.parametrize("cas", ["entete_liste", "nbf_chaine", "iat_absent", "divulgation_non_ascii", "nom_liste", "corps_liste"])
def test_i1_entrees_hostiles_refusees_proprement(cas):
    t = at.maintenant_s()
    base = {"iss": VRAI.did, "vct": at.VCT, "iat": t, "nbf": t, "exp": t + 60, "_sd_alg": "sha-256", "_sd": []}
    d_liste = at._b64(json.dumps(["sel", ["a"], 1]).encode())
    sd = {"entete_liste": lambda: _brut(["x"], base),
          "nbf_chaine": lambda: _corps_signe(base | {"nbf": "hier"}),
          "iat_absent": lambda: _corps_signe({k: v for k, v in base.items() if k != "iat"}),
          "divulgation_non_ascii": lambda: _corps_signe(base, ["é"]),
          "nom_liste": lambda: _corps_signe(base | {"_sd": [at._b64(hashlib.sha256(d_liste.encode()).digest())]}, [d_liste]),
          "corps_liste": lambda: _corps_signe([1, 2])}[cas]()
    r = at.verifier(sd, emetteurs={VRAI.did})
    assert r["valide"] is False


# ------------------------------------------------------------------ I4 : exp bornée par l'accord, statut exact
def test_i4_l_attestation_ne_survit_pas_a_l_accord():
    e = at.Emetteur(b"e" * 32)
    t0 = int(datetime(2026, 9, 10, tzinfo=timezone.utc).timestamp())
    recu = {"finalite": "f", "titre": "t", "piece": "p", "etat": "valable", "donne_le": "2026-09-01", "jusqu_au": "2026-09-30",
            "reference": "R-1"}
    sd = e.emettre(None, "pid", recu, maintenant=t0)
    assert at.verifier(sd, maintenant=t0, emetteurs={e.did})["valide"] is True
    apres = int(datetime(2026, 10, 2, tzinfo=timezone.utc).timestamp())
    assert at.verifier(sd, maintenant=apres, emetteurs={e.did})["valide"] is False


def test_i4_un_etat_inconnu_n_est_jamais_signe_echu_ni_valable():
    e = at.Emetteur(b"e" * 32)
    recu = {"finalite": "f", "titre": "t", "piece": "p", "etat": "cette pièce n'existe plus", "donne_le": "2026-09-01",
            "jusqu_au": "2030-09-30", "reference": "R-1"}
    r = at.verifier(e.emettre(None, "pid", recu), emetteurs={e.did})
    assert r["affirmations"]["statut"] == "invalide"


# ------------------------------------------------------------------ I2 / I3 : allumage Foire
@pytest.fixture
def club(monkeypatch, tmp_path):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    return Demo(TAX).club


def test_i2_un_retrait_efface_la_declaration_meme_apres_coup(club):
    lot = fa.emettre_lot(club, 2, origine="borne")
    s = [club.decouverte.activer(x["jeton"])["invite"] for x in lot]
    for i, (ent, met) in enumerate((("Seule Entreprise SA", "conseil"), ("Autre SA", "transport"))):
        club.decouverte.declarer(s[i], ent, met, "Valais romand")
        club.decouverte.rejoindre(s[i])
    club.decouverte.retirer(s[1])
    retire = [p for p in club.decouverte.passes().values() if p["revoque"]]
    assert len(retire) == 1 and retire[0]["declaration"] is None
    refs = [x["reference"] for x in fa.intentions(club)]
    assert len(refs) == 1                                             # l'invité qui a retiré n'est plus listé…
    ref_retire = fa._ref(retire[0]["nonce"])
    with pytest.raises(ErreurMetier):
        fa.confirmer_adhesion(club, ref_retire)                       # … ni confirmable


def test_i2_la_console_ne_liste_plus_metier_ni_region_par_intention(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from tests.test_autorisation_balayage import _secretariat_eleve
    app = _app(monkeypatch, tmp_path, HACKVS_FOIRE_ALLUMAGE="1", HACKVS_COMPTES="1", HACKVS_SECRETARIAT="1")
    client = TestClient(app)
    admin = _secretariat_eleve(app)
    d = client.get("/api/pulse/secretariat/foire", headers={"X-Pulse-Compte": admin}).json()
    assert "par_origine" in d and "intentions" not in d


@pytest.mark.parametrize("cellule", ['=HYPERLINK("http://x","y")', "+41 27", "-1", "@SUM(1)", "\tx", "\rx"])
def test_i3_pas_de_formule_dans_le_csv_rendu(club, cellule):
    entree = "exposant;metier;stand\n" + json.dumps(cellule).replace('\\"', '""') + ";conseil;" + json.dumps(cellule).replace('\\"', '""') + "\n"
    r = fa.importer_exposants(club, entree, base="https://club.exemple")
    ligne = r["csv"].splitlines()[1]
    for champ in ligne.split(";")[:3]:
        assert not champ.strip('"').startswith(("=", "+", "-", "@", "\t", "\r")), ligne


def test_m2_avancer_la_date_simulee_ne_remet_pas_le_plafond_de_la_borne(club, monkeypatch):
    from datetime import timedelta
    monkeypatch.setattr(fa, "BORNE_PAR_JOUR", 2)
    secret = b"b" * 32
    horloge = [1000.0]
    borne = fa.Borne(secret, horloge=lambda: horloge[0])
    jeton = fa.jeton_borne(secret, "stand-A")
    for _ in range(2):
        borne.passe(club, jeton)
        horloge[0] += fa.BORNE_INTERVALLE_S
    avant = club.jour
    club.avancer(1)
    assert club.jour == avant + timedelta(days=1)
    with pytest.raises(fa.TropVite):
        borne.passe(club, jeton)


# ------------------------------------------------------------------ M1 (repris) : jeton de borne échu, révocable
def test_m1_un_jeton_de_borne_echu_est_refuse():
    from intelligence.erreurs import NonAuthentifie
    secret = b"b" * 32
    jeton = fa.jeton_borne(secret, "stand-A", jusqu_a=2_000)
    assert fa.verifier_borne(secret, jeton, maintenant=1_999) == "stand-A"
    with pytest.raises(NonAuthentifie):
        fa.verifier_borne(secret, jeton, maintenant=2_000)


def test_m1_l_ancien_format_sans_echeance_est_refuse():
    import hmac as h
    from intelligence.erreurs import NonAuthentifie
    secret = b"b" * 32
    ancien = f"b1.stand-A.{h.new(secret, b'borne|stand-A', hashlib.sha256).hexdigest()[:32]}"
    with pytest.raises(NonAuthentifie):
        fa.verifier_borne(secret, ancien)


def test_m1_une_borne_revoquee_n_emet_plus_rien_et_le_journal_ne_garde_que_son_nom(club):
    secret = b"b" * 32
    borne = fa.Borne(secret)
    jeton = fa.jeton_borne(secret, "stand-A")
    borne.passe(club, jeton)
    fa.revoquer_borne(club, "stand-A", par="Secrétariat (fictif)")
    from intelligence.erreurs import NonAuthentifie
    with pytest.raises(NonAuthentifie):
        fa.Borne(secret).passe(club, jeton)
    e = club.journal.evenements("BORNE_REVOQUEE")[-1]
    assert set(e.donnees) - {"n"} == {"nom", "par"} and e.donnees["nom"] == "stand-A"     # « n » : rang dans le journal


def test_m1_par_http_le_secretariat_revoque_une_borne(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from tests.test_autorisation_balayage import _secretariat_eleve
    app = _app(monkeypatch, tmp_path, HACKVS_FOIRE_ALLUMAGE="1", HACKVS_COMPTES="1", HACKVS_SECRETARIAT="1")
    client = TestClient(app)
    sec = {"X-Pulse-Compte": _secretariat_eleve(app)}
    r = client.post("/api/pulse/secretariat/foire/bornes", headers=sec).json()
    assert r["jusqu_au"] and r["nom"].startswith("borne-")
    jeton = r["lien"].split("#b=")[1]
    assert client.post("/api/pulse/borne/passe", headers={"X-Pulse-Borne": jeton}).status_code == 200
    assert client.post("/api/pulse/secretariat/foire/bornes/revoquer", headers=sec, json={"nom": r["nom"]}).status_code == 200
    assert client.post("/api/pulse/borne/passe", headers={"X-Pulse-Borne": jeton}).status_code == 401
    assert {"nom": r["nom"], "revoquee": True} in [{k: b[k] for k in ("nom", "revoquee")}
                                                   for b in client.get("/api/pulse/secretariat/foire", headers=sec).json()["bornes"]]


def test_m1_dans_la_console_preparer_puis_revoquer_une_borne(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path

    from playwright.sync_api import sync_playwright

    from tests.aide_comptes import elever_http
    from tests.test_e2e_scene import _chromium, serveur
    env = {"HACKVS_COMPTES": "1", "HACKVS_SECRETARIAT": "1", "HACKVS_FOIRE_ALLUMAGE": "1", "HACKVS_FOIRE": "1",
           "HACKVS_ESSAIS_DB": str(tmp_path / "j.db"), "HACKVS_SECRET": "r" * 40}
    with serveur(**env) as base, sync_playwright() as p:
        admin = subprocess.run([sys.executable, "scripts/comptes.py", "amorcer", "Administration fictive"], capture_output=True,
                               text=True, cwd=Path(__file__).resolve().parents[1],
                               env={**os.environ, **env}).stdout.strip().splitlines()[-1]
        elever_http(base, admin)
        erreurs: list[str] = []
        b = _chromium(p)
        pg = b.new_page(viewport={"width": 1100, "height": 900})
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.goto(base + "/compte")
        pg.evaluate("(s) => sessionStorage.setItem('compte-session', s)", admin)
        pg.goto(base + "/secretariat")
        pg.click("#borne-ok")
        pg.locator("#bornes tr:has-text('active')").wait_for()
        nom = pg.inner_text("#bornes tr td")
        pg.fill("#borne-nom", nom)
        pg.click("#borne-revoquer")
        pg.locator("#bornes tr:has-text('révoquée')").wait_for()
        b.close()
    assert not erreurs, erreurs
