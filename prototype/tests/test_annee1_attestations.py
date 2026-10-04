"""ANNÉE 1 · LOT 10 — Prototype e-ID : les reçus de consentement émis comme ATTESTATIONS VÉRIFIABLES au format SD-JWT VC
(celui du profil suisse de swiyu : ES256 sur P-256, `vct` et `iss` obligatoires et jamais divulgables sélectivement, les
autres affirmations divulgables, SHA-256), avec un émetteur et un vérificateur LOCAUX de démonstration. Marqué
« prototype, non connecté à swiyu » : l'émetteur n'est pas inscrit au registre de base (did:jwk local, pas did:tdw).
Données FICTIVES."""
import base64
import json

import pytest

from app.taxonomy import charger_taxonomie
from intelligence import attestations as at
from intelligence.demo import Demo

TAX = charger_taxonomie()


def _b64(x: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(x + "=" * (-len(x) % 4)))


@pytest.fixture
def emis(monkeypatch, tmp_path):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    demo = Demo(TAX)
    demo.rejouer(9)
    c = demo.club
    pid, recu = next((p.id, r) for p in c.r.profils for r in c.capacites.recus(p.id))
    e = at.Emetteur(b"e" * 32)
    return c, e, e.emettre(c, pid, recu)


def test_le_format_suit_le_profil_suisse(emis):
    c, e, sd = emis
    jwt, *disclosures = sd.split("~")
    assert sd.endswith("~") and disclosures[-1] == ""                       # compact, sans liaison d'appareil
    entete, corps = (_b64(x) for x in jwt.split(".")[:2])
    assert entete["alg"] == "ES256" and entete["typ"] == "vc+sd-jwt" and entete["kid"].startswith(corps["iss"] + "#")
    assert corps["iss"].startswith("did:jwk:") and corps["vct"] == at.VCT and corps["_sd_alg"] == "sha-256"
    assert {"iat", "nbf", "exp"} <= set(corps)
    assert not {"finalite", "titre", "statut", "donne_le"} & set(corps)      # divulgables : seulement dans les _sd
    assert len(corps["_sd"]) == len([d for d in disclosures if d])


def test_le_verificateur_local_accepte_et_lit(emis):
    c, e, sd = emis
    r = at.verifier(sd, emetteurs={e.did}, maintenant=at.maintenant_s())
    assert r["valide"] is True and r["affirmations"]["vct"] == at.VCT and "finalite" in r["affirmations"]
    assert r["mention"] == "prototype, non connecté à swiyu"


def test_divulgation_selective(emis):
    c, e, sd = emis
    jwt, *disclosures = sd.split("~")
    garde = [d for d in disclosures if d and _b64(d)[1] != "titre"]
    r = at.verifier("~".join([jwt, *garde]) + "~", emetteurs={e.did}, maintenant=at.maintenant_s())
    assert r["valide"] and "titre" not in r["affirmations"] and "finalite" in r["affirmations"]


@pytest.mark.parametrize("falsification", ["divulgation", "corps", "signature"])
def test_une_falsification_est_refusee(emis, falsification):
    c, e, sd = emis
    jwt, *disclosures = sd.split("~")
    h, p, s = jwt.split(".")
    if falsification == "divulgation":
        d = _b64(disclosures[0])
        d[2] = "valeur changée"
        disclosures[0] = base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    elif falsification == "corps":
        corps = _b64(p)
        corps["exp"] += 10_000_000
        p = base64.urlsafe_b64encode(json.dumps(corps).encode()).decode().rstrip("=")
    else:
        s = s[:-4] + ("AAAA" if s[-4:] != "AAAA" else "BBBB")
    r = at.verifier("~".join([f"{h}.{p}.{s}", *disclosures]), emetteurs={e.did}, maintenant=at.maintenant_s())
    assert r["valide"] is False and r["raison"]


def test_une_attestation_echue_est_refusee(emis):
    c, e, sd = emis
    corps = _b64(sd.split("~")[0].split(".")[1])
    r = at.verifier(sd, emetteurs={e.did}, maintenant=corps["exp"] + 1)
    assert r["valide"] is False and "échue" in r["raison"]


def test_la_cle_de_l_emetteur_est_stable_pour_un_meme_secret():
    assert at.Emetteur(b"x" * 32).did == at.Emetteur(b"x" * 32).did != at.Emetteur(b"y" * 32).did


def test_par_http_puis_dans_un_vrai_navigateur(tmp_path):
    import json as js
    import urllib.request

    from playwright.sync_api import sync_playwright

    from intelligence import monde_demo as md
    from tests.test_e2e_scene import _chromium, serveur
    with serveur(HACKVS_EID="1", HACKVS_ESSAIS_DB=str(tmp_path / "j.db"), HACKVS_FOIRE="1") as base, sync_playwright() as p:
        console = {"X-Pulse-Console": "1"}
        urllib.request.urlopen(urllib.request.Request(base + "/api/pulse/demo/aller/9", data=b"{}", headers={**console, "Content-Type": "application/json"}))
        personas = js.load(urllib.request.urlopen(urllib.request.Request(base + "/api/pulse/console/personas", headers=console)))
        lot = None
        for x in personas:
            if not x.get("session"):
                continue
            d = js.load(urllib.request.urlopen(urllib.request.Request(base + "/api/pulse/moi/attestations", headers={"X-Pulse-Session": x["session"]})))
            if d["attestations"]:
                lot = d
                break
        assert lot and lot["mention"] == "prototype, non connecté à swiyu" and lot["emetteur"].startswith("did:jwk:")
        sd = lot["attestations"][0]["sd_jwt"]
        assert md.PAULINE not in sd                                         # aucun identifiant du membre dans l'attestation
        b = _chromium(p)
        pg = b.new_page()
        erreurs: list[str] = []
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.goto(f"{base}/attestation")
        pg.fill("#sd", sd)
        pg.click("#verifier")
        pg.locator("#verdict.ok").wait_for()
        pg.fill("#sd", sd.replace("~", "x~", 1))
        pg.click("#verifier")
        pg.locator("#verdict.ko").wait_for()
        b.close()
    assert not erreurs, erreurs
