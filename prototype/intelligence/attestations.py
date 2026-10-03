"""ANNÉE 1 · LOT 10 — PROTOTYPE e-ID : les reçus de consentement émis comme ATTESTATIONS VÉRIFIABLES.

Format : SD-JWT VC, tel que le décrit le profil suisse d'interopérabilité de swiyu (e-id-admin/open-source-community,
« tech-roadmap/swiss-profile.md », version Public Beta, consulté le 04.10.2026 depuis GitHub) :
- sérialisation compacte SD-JWT (`<jwt>~<divulgation>~…~`, ici sans liaison d'appareil) ;
- en-tête `alg` = ES256 (P-256), `typ` = `vc+sd-jwt`, `kid` = DID avec référence de clé ;
- `vct` et `iss` obligatoires, `iat` / `nbf` / `exp` présents, JAMAIS divulgables sélectivement ; toutes les autres
  affirmations divulgables (`_sd`, `_sd_alg` = `sha-256`).
Marqué « prototype, non connecté à swiyu » : l'émetteur est LOCAL (`did:jwk`, une clé dérivée du secret du serveur),
il n'est inscrit à aucun registre de base (le profil demande `did:tdw`) ; pas de liste de statut (Token Status List) ;
pas d'OID4VCI / OID4VP. Le vérificateur est local lui aussi."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import TYPE_CHECKING, Any, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

VCT = "clubpulse:recu-consentement:v1"
MENTION = "prototype, non connecté à swiyu"
DUREE_S = 365 * 24 * 3600
DIVULGABLES = ("finalite", "titre", "piece", "statut", "donne_le", "jusqu_au", "reference")
_N = int("FFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551", 16)   # ordre de P-256


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _deb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def maintenant_s() -> int:
    return int(time.time())


def _jwk(pub: ec.EllipticCurvePublicKey) -> dict:
    n = pub.public_numbers()
    return {"kty": "EC", "crv": "P-256", "x": _b64(n.x.to_bytes(32, "big")), "y": _b64(n.y.to_bytes(32, "big"))}


def _cle_publique(jwk: dict) -> ec.EllipticCurvePublicKey:
    if jwk.get("kty") != "EC" or jwk.get("crv") != "P-256":
        raise ValueError("clé non P-256")
    return ec.EllipticCurvePublicNumbers(int.from_bytes(_deb64(jwk["x"]), "big"), int.from_bytes(_deb64(jwk["y"]), "big"),
                                         ec.SECP256R1()).public_key()


def _did_jwk(jwk: dict) -> str:
    return "did:jwk:" + _b64(json.dumps(jwk, separators=(",", ":"), sort_keys=True).encode())


class Emetteur:
    """Émetteur LOCAL de démonstration : sa clé P-256 est dérivée du secret du serveur (stable d'un redémarrage à l'autre)."""

    def __init__(self, secret: bytes):
        d = int.from_bytes(hmac.new(secret, b"attestations|annee-1|es256", hashlib.sha256).digest(), "big") % (_N - 1) + 1
        self._cle = ec.derive_private_key(d, ec.SECP256R1())
        self.jwk = _jwk(self._cle.public_key())
        self.did = _did_jwk(self.jwk)

    def _signer(self, donnees: bytes) -> str:
        r, s = decode_dss_signature(self._cle.sign(donnees, ec.ECDSA(hashes.SHA256())))
        return _b64(r.to_bytes(32, "big") + s.to_bytes(32, "big"))   # JWS : r || s, 64 octets

    def emettre_affirmations(self, affirmations: dict[str, Any], maintenant: Optional[int] = None) -> str:
        t = maintenant_s() if maintenant is None else maintenant
        divulgations, empreintes = [], []
        for nom in DIVULGABLES:
            if affirmations.get(nom) in (None, ""):
                continue
            d = _b64(json.dumps([_b64(secrets.token_bytes(16)), nom, affirmations[nom]], ensure_ascii=False).encode())
            divulgations.append(d)
            empreintes.append(_b64(hashlib.sha256(d.encode("ascii")).digest()))
        corps = {"iss": self.did, "vct": VCT, "iat": t, "nbf": t, "exp": t + DUREE_S, "_sd": sorted(empreintes), "_sd_alg": "sha-256"}
        entete = {"alg": "ES256", "typ": "vc+sd-jwt", "kid": self.did + "#0"}
        signe = _b64(json.dumps(entete, separators=(",", ":")).encode()) + "." + _b64(json.dumps(corps, separators=(",", ":")).encode())
        return "~".join([signe + "." + self._signer(signe.encode("ascii")), *divulgations]) + "~"

    def emettre(self, c: "ClubPulse", pid: str, recu: dict, maintenant: Optional[int] = None) -> str:
        """Un reçu de consentement du membre → une attestation. Aucune identité : ni nom, ni identifiant du membre."""
        statut = "retire" if recu.get("retire_le") else ("valable" if recu.get("etat") == "valable" else "echu")
        return self.emettre_affirmations({"finalite": recu.get("finalite"), "titre": recu.get("titre"), "piece": recu.get("piece"),
                                          "statut": statut, "donne_le": recu.get("donne_le"), "jusqu_au": recu.get("jusqu_au"),
                                          "reference": recu.get("reference")}, maintenant)


def verifier(sd_jwt: str, maintenant: Optional[int] = None) -> dict:
    """Vérificateur LOCAL : signature ES256 (clé tirée du `kid` did:jwk), en-tête, `vct`, période de validité, chaque
    divulgation présentée doit correspondre à une empreinte signée (une divulgation absente : simplement non dite)."""
    t = maintenant_s() if maintenant is None else maintenant

    def non(raison: str) -> dict:
        return {"valide": False, "raison": raison, "mention": MENTION}
    try:
        jwt, *divulgations = (sd_jwt or "").split("~")
        h, p, s = jwt.split(".")
        entete, corps = json.loads(_deb64(h)), json.loads(_deb64(p))
        if entete.get("alg") != "ES256" or entete.get("typ") != "vc+sd-jwt":
            return non("en-tête inattendu")
        kid = entete.get("kid") or ""
        if not kid.startswith("did:jwk:") or kid.split("#")[0] != corps.get("iss"):
            return non("émetteur inconnu (seul l'émetteur local did:jwk est vérifié par ce prototype)")
        cle = _cle_publique(json.loads(_deb64(kid.split("#")[0][len("did:jwk:"):])))
        sig = _deb64(s)
        if len(sig) != 64:
            return non("signature mal formée")
        cle.verify(encode_dss_signature(int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big")),
                   f"{h}.{p}".encode("ascii"), ec.ECDSA(hashes.SHA256()))
    except InvalidSignature:
        return non("signature invalide")
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return non("attestation illisible")
    if corps.get("vct") != VCT or corps.get("_sd_alg") != "sha-256":
        return non("type d'attestation inconnu")
    if not corps.get("nbf", 0) <= t < corps.get("exp", 0):
        return non("attestation échue ou pas encore valable")
    signees = set(corps.get("_sd") or [])
    affirmations = {k: corps[k] for k in ("iss", "vct", "iat", "nbf", "exp")}
    for d in [x for x in divulgations if x]:
        if _b64(hashlib.sha256(d.encode("ascii")).digest()) not in signees:
            return non("divulgation non signée (modifiée ?)")
        try:
            _, nom, valeur = json.loads(_deb64(d))
        except (ValueError, json.JSONDecodeError):
            return non("divulgation illisible")
        affirmations[nom] = valeur
    return {"valide": True, "affirmations": affirmations, "mention": MENTION}
