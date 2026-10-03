"""ANNÉE 1 · LOT 2 — Comptes, rôles, sessions, double authentification (domaine, sans HTTP).

- **Invitation personnelle** envoyée par le Club : un lien à usage unique qui expire. Le journal ne garde que
  l'EMPREINTE du jeton (HMAC), jamais le jeton.
- **Sessions signées** (`sid.expiration.signature`, HMAC-SHA256) ; chaque session est un fait du journal (appareil,
  ouverture) ; déconnexion, déconnexion d'un autre appareil, liste de ses appareils ; révoquer un compte coupe tout.
- **Rôles** : membre, invité, secrétariat, administration. Le secrétariat a des comptes NOMINATIFS (une étiquette
  choisie par le Club, ex. « Secrétariat 1 » ; l'identité civile reste dans l'annuaire du Club, hors du journal). Le
  jeton partagé de la console reste pour la DÉMO seulement.
- **Double authentification (TOTP, RFC 6238)** obligatoire pour la console : le secret n'est JAMAIS stocké — il est
  dérivé de HACKVS_SECRET et d'un nonce journalisé ; un code ne sert qu'une fois (le pas consommé est journalisé).
- **Journal des actions d'administration** : chaque invitation, attribution de rôle, révocation y est écrite.
- **Limite par session** (écritures par minute), en mémoire.
L'état est un REPLI du journal : il survit à un redémarrage, et au changement de moteur (lot 1)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import threading
import time
from datetime import date
from typing import Callable, Optional
from urllib.parse import quote

from plateforme.affirmations import Statut
from plateforme.memoire import Evt, Memoire

from .erreurs import Interdit, Limite, NonAuthentifie

MEMBRE, INVITE, SECRETARIAT, ADMIN = "membre", "invite", "secretariat", "administration"
ROLES = (MEMBRE, INVITE, SECRETARIAT, ADMIN)
DUREE_SESSION_S = 30 * 24 * 3600            # un membre : un mois ; la console exige en plus une élévation par code
DUREE_ELEVATION_S = 12 * 3600               # une élévation TOTP vaut une journée de travail
LIMITE_ECRITURES_MINUTE = 60
TropDeRequetes = Limite
TYPES = ("COMPTE_ADMIN_AMORCE", "COMPTE_INVITATION", "COMPTE_CREE", "COMPTE_ROLE", "COMPTE_REVOQUE", "SESSION_OUVERTE",
         "SESSION_FERMEE", "SESSION_ELEVEE", "TOTP_PREPARE", "TOTP_ACTIF", "TOTP_PAS_CONSOMME", "ADMIN_ACTION")
# qui peut inviter qui (lot 2 : les membres n'invitent pas encore)
PEUT_INVITER = {ADMIN: set(ROLES), SECRETARIAT: {MEMBRE, INVITE}}


def code_totp(secret_b32: str, t: float, pas: int = 30) -> str:
    """RFC 6238 (HMAC-SHA1, 6 chiffres, pas de 30 s) — compatible avec les applications d'authentification usuelles."""
    cle = base64.b32decode(secret_b32 + "=" * (-len(secret_b32) % 8))
    h = hmac.new(cle, struct.pack(">Q", int(t // pas)), hashlib.sha1).digest()
    o = h[-1] & 0x0F
    return f"{(struct.unpack('>I', h[o:o + 4])[0] & 0x7FFFFFFF) % 1_000_000:06d}"


class Comptes:
    def __init__(self, journal: Memoire, secret: bytes, horloge: Callable[[], float] = time.time, emetteur: str = "Club Pulse"):
        self.j, self._secret, self._h, self.emetteur = journal, secret, horloge, emetteur
        self._v = threading.RLock()
        self._ecritures: dict[str, list[float]] = {}

    # ------------------------------------------------------------------ outils
    def _mac(self, usage: str, *parts: str) -> str:
        return hmac.new(self._secret, "|".join((usage, *parts)).encode(), hashlib.sha256).hexdigest()

    def _ecrire(self, type_: str, acteurs: list[str], **donnees) -> None:
        self.j.ajouter(Evt(type=type_, le=date.fromtimestamp(self._h()), acteurs=acteurs,
                           donnees={**donnees, "t": round(self._h(), 3), "n": secrets.token_hex(4)}, statut=Statut.OBSERVE))

    def _evts(self, *types: str) -> list[Evt]:
        return self.j.evenements(*(types or TYPES))

    def _etat(self) -> dict:
        """Repli du journal : comptes, rôles, révocations, invitations utilisées, sessions, TOTP."""
        comptes: dict[str, dict] = {}
        invit: dict[str, dict] = {}
        sessions: dict[str, dict] = {}
        for e in self._evts():
            d = e.donnees
            if e.type == "COMPTE_ADMIN_AMORCE":
                comptes[d["compte"]] = {"role": ADMIN, "etiquette": d["etiquette"], "revoque": False, "totp": None, "pas": set()}
            elif e.type == "COMPTE_INVITATION":
                invit[d["empreinte"]] = {"role": d["role"], "etiquette": d["etiquette"], "expire": d["expire"], "utilisee": False}
            elif e.type == "COMPTE_CREE":
                comptes[d["compte"]] = {"role": d["role"], "etiquette": d["etiquette"], "revoque": False, "totp": None, "pas": set()}
                if d["empreinte"] in invit:
                    invit[d["empreinte"]]["utilisee"] = True
            elif e.type == "COMPTE_ROLE" and d["compte"] in comptes:
                comptes[d["compte"]]["role"] = d["role"]
            elif e.type == "COMPTE_REVOQUE" and d["compte"] in comptes:
                comptes[d["compte"]]["revoque"] = True
            elif e.type == "SESSION_OUVERTE":
                sessions[d["sid"]] = {"compte": d["compte"], "appareil": d["appareil"], "ouverte": d["t"], "expire": d["expire"],
                                      "fermee": False, "elevee_jusqu_a": 0.0}
            elif e.type == "SESSION_FERMEE" and d["sid"] in sessions:
                sessions[d["sid"]]["fermee"] = True
            elif e.type == "SESSION_ELEVEE" and d["sid"] in sessions:
                sessions[d["sid"]]["elevee_jusqu_a"] = d["jusqu_a"]
            elif e.type == "TOTP_PREPARE" and d["compte"] in comptes:
                comptes[d["compte"]]["totp_prepare"] = d["nonce"]
            elif e.type == "TOTP_ACTIF" and d["compte"] in comptes:
                comptes[d["compte"]]["totp"] = d["nonce"]
            elif e.type == "TOTP_PAS_CONSOMME" and d["compte"] in comptes:
                comptes[d["compte"]]["pas"].add(d["pas"])
        return {"comptes": comptes, "invitations": invit, "sessions": sessions}

    def _jeton_session(self, sid: str, expire: int) -> str:
        return f"{sid}.{expire}.{self._mac('session', sid, str(expire))[:32]}"

    def _ouvrir_session(self, compte: str, appareil: str) -> str:
        sid = secrets.token_urlsafe(12).replace(".", "_")
        expire = int(self._h()) + DUREE_SESSION_S
        self._ecrire("SESSION_OUVERTE", [compte], sid=sid, compte=compte, appareil=(appareil or "appareil")[:60], expire=expire)
        return self._jeton_session(sid, expire)

    def _session(self, jeton: str) -> tuple[str, dict, dict, dict]:
        morceaux = (jeton or "").split(".")
        if len(morceaux) != 3 or not morceaux[1].isdigit():
            raise NonAuthentifie("session invalide")
        sid, exp = morceaux[0], int(morceaux[1])
        if not hmac.compare_digest(self._mac("session", sid, str(exp))[:32], morceaux[2]):
            raise NonAuthentifie("session invalide")
        if exp < self._h():
            raise NonAuthentifie("session expirée")
        etat = self._etat()
        s = etat["sessions"].get(sid)
        if not s or s["fermee"]:
            raise NonAuthentifie("session fermée")
        c = etat["comptes"].get(s["compte"])
        if not c or c["revoque"]:
            raise NonAuthentifie("compte révoqué")
        return sid, s, c, etat

    def _secret_totp(self, compte: str, nonce: str) -> str:
        brut = hmac.new(self._secret, f"totp|{compte}|{nonce}".encode(), hashlib.sha256).digest()[:20]
        return base64.b32encode(brut).decode().rstrip("=")

    def _admin(self, par: str, action: str, cible: str, **details) -> None:
        self._ecrire("ADMIN_ACTION", [par], par=par, action=action, cible=cible, **details)

    # ------------------------------------------------------------------ amorçage, invitations
    def amorcer_administration(self, etiquette: str) -> str:
        """Le tout premier compte (administration), une seule fois dans la vie du journal. Rend une session."""
        with self._v:
            if self._evts("COMPTE_ADMIN_AMORCE"):
                raise Interdit("l'administration est déjà amorcée")
            compte = "c_" + secrets.token_hex(6)
            self._ecrire("COMPTE_ADMIN_AMORCE", [compte], compte=compte, etiquette=etiquette[:60])
            return self._ouvrir_session(compte, "amorçage")

    def inviter(self, session: str, *, role: str, etiquette: str, duree_s: int) -> dict:
        with self._v:
            _, _, c, _ = self._session(session)
            if role not in ROLES:
                raise Interdit(f"rôle inconnu : {role}")
            if role not in PEUT_INVITER.get(c["role"], set()):
                raise Interdit("votre rôle ne permet pas cette invitation")
            iid = secrets.token_urlsafe(9).replace(".", "_")
            expire = int(self._h()) + max(60, min(duree_s, 30 * 24 * 3600))
            jeton = f"{iid}.{expire}.{self._mac('invitation', iid, str(expire))[:32]}"
            empreinte = self._mac("empreinte-invitation", jeton)[:32]
            self._ecrire("COMPTE_INVITATION", [], empreinte=empreinte, role=role, etiquette=etiquette[:60], expire=expire)
            par = self._session(session)[1]["compte"]
            self._admin(par, "inviter", empreinte[:8], role=role)
            return {"jeton": jeton, "expire": expire, "role": role}

    def accepter(self, jeton: str, appareil: str) -> str:
        with self._v:
            morceaux = (jeton or "").split(".")
            if len(morceaux) != 3 or not morceaux[1].isdigit() or \
                    not hmac.compare_digest(self._mac("invitation", morceaux[0], morceaux[1])[:32], morceaux[2]):
                raise NonAuthentifie("invitation invalide")
            if int(morceaux[1]) < self._h():
                raise NonAuthentifie("invitation expirée : demandez-en une nouvelle au Club")
            empreinte = self._mac("empreinte-invitation", jeton)[:32]
            inv = self._etat()["invitations"].get(empreinte)
            if not inv or inv["utilisee"]:
                raise NonAuthentifie("invitation déjà utilisée")
            compte = "c_" + secrets.token_hex(6)
            self._ecrire("COMPTE_CREE", [compte], compte=compte, role=inv["role"], etiquette=inv["etiquette"], empreinte=empreinte)
            return self._ouvrir_session(compte, appareil)

    # ------------------------------------------------------------------ sessions et appareils
    def verifier(self, session: str) -> dict:
        sid, s, c, _ = self._session(session)
        return {"compte": s["compte"], "role": c["role"], "etiquette": c["etiquette"], "session": sid,
                "elevee": s["elevee_jusqu_a"] > self._h()}

    def nouvelle_session(self, session: str, appareil: str) -> str:
        with self._v:
            _, s, _, _ = self._session(session)
            return self._ouvrir_session(s["compte"], appareil)

    def mes_appareils(self, session: str) -> list[dict]:
        sid, s, _, etat = self._session(session)
        return [{"id": k, "appareil": x["appareil"], "ouverte": x["ouverte"], "celui_ci": k == sid}
                for k, x in etat["sessions"].items()
                if x["compte"] == s["compte"] and not x["fermee"] and x["expire"] >= self._h()]

    def deconnecter(self, session: str) -> None:
        with self._v:
            sid, s, _, _ = self._session(session)
            self._ecrire("SESSION_FERMEE", [s["compte"]], sid=sid)

    def deconnecter_appareil(self, session: str, sid_cible: str) -> None:
        with self._v:
            _, s, _, etat = self._session(session)
            cible = etat["sessions"].get(sid_cible)
            if not cible or cible["compte"] != s["compte"]:
                raise Interdit("cet appareil n'est pas le vôtre")
            self._ecrire("SESSION_FERMEE", [s["compte"]], sid=sid_cible)

    # ------------------------------------------------------------------ rôles et révocation (administration)
    def attribuer_role(self, session: str, compte: str, role: str) -> None:
        with self._v:
            _, s, c, etat = self._session(session)
            if c["role"] != ADMIN:
                raise Interdit("seule l'administration change un rôle")
            if role not in ROLES or compte not in etat["comptes"]:
                raise Interdit("compte ou rôle inconnu")
            self._ecrire("COMPTE_ROLE", [compte], compte=compte, role=role)
            self._admin(s["compte"], "attribuer_role", compte, role=role)

    def revoquer(self, session: str, compte: str) -> None:
        with self._v:
            _, s, c, etat = self._session(session)
            cible = etat["comptes"].get(compte)
            if not cible:
                raise Interdit("compte inconnu")
            if c["role"] != ADMIN and not (c["role"] == SECRETARIAT and cible["role"] in (MEMBRE, INVITE)):
                raise Interdit("votre rôle ne permet pas cette révocation")
            self._ecrire("COMPTE_REVOQUE", [compte], compte=compte)
            self._admin(s["compte"], "revoquer", compte)

    def journal_admin(self, session: str) -> list[dict]:
        _, _, c, _ = self._session(session)
        if c["role"] != ADMIN:
            raise Interdit("journal réservé à l'administration")
        return [{"le": e.donnees["t"], "par": e.donnees["par"], "action": e.donnees["action"], "cible": e.donnees["cible"]}
                for e in self._evts("ADMIN_ACTION")]

    # ------------------------------------------------------------------ double authentification (TOTP)
    def preparer_totp(self, session: str) -> dict:
        """Prépare un secret (montré UNE fois, à scanner) ; il ne vaut qu'après confirmation par un premier code."""
        with self._v:
            _, s, c, _ = self._session(session)
            nonce = secrets.token_hex(8)
            self._ecrire("TOTP_PREPARE", [s["compte"]], compte=s["compte"], nonce=nonce)
            secret = self._secret_totp(s["compte"], nonce)
            nom = quote(f"{self.emetteur}:{c['etiquette']}")
            return {"secret": secret, "uri": f"otpauth://totp/{nom}?secret={secret}&issuer={quote(self.emetteur)}&digits=6&period=30"}

    def _code_valide(self, compte: str, nonce: str, code: str, consommes: set) -> Optional[int]:
        pas = int(self._h() // 30)
        for p in (pas, pas - 1, pas + 1):                    # un pas de décalage toléré, pas plus
            if p not in consommes and hmac.compare_digest(code_totp(self._secret_totp(compte, nonce), p * 30), (code or "").strip()):
                return p
        return None

    def confirmer_totp(self, session: str, code: str) -> None:
        with self._v:
            _, s, c, _ = self._session(session)
            nonce = c.get("totp_prepare")
            p = self._code_valide(s["compte"], nonce, code, c["pas"]) if nonce else None
            if p is None:
                raise NonAuthentifie("code incorrect")
            self._ecrire("TOTP_PAS_CONSOMME", [s["compte"]], compte=s["compte"], pas=p)
            self._ecrire("TOTP_ACTIF", [s["compte"]], compte=s["compte"], nonce=nonce)

    def elever(self, session: str, code: str) -> None:
        with self._v:
            sid, s, c, _ = self._session(session)
            if not c["totp"]:
                raise Interdit("double authentification non activée")
            p = self._code_valide(s["compte"], c["totp"], code, c["pas"])
            if p is None:
                raise NonAuthentifie("code incorrect ou déjà utilisé")
            self._ecrire("TOTP_PAS_CONSOMME", [s["compte"]], compte=s["compte"], pas=p)
            self._ecrire("SESSION_ELEVEE", [s["compte"]], sid=sid, jusqu_a=round(self._h() + DUREE_ELEVATION_S, 3))

    def exiger_console(self, session: str) -> dict:
        """La console : compte nominatif du secrétariat ou de l'administration, TOTP actif, session élevée par un code."""
        sid, s, c, _ = self._session(session)
        if c["role"] not in (SECRETARIAT, ADMIN):
            raise Interdit("la console est réservée au secrétariat et à l'administration")
        if not c["totp"]:
            raise Interdit("activez la double authentification pour ouvrir la console")
        if s["elevee_jusqu_a"] <= self._h():
            raise Interdit("entrez le code de votre application d'authentification")
        return {"compte": s["compte"], "role": c["role"], "etiquette": c["etiquette"], "session": sid}

    # ------------------------------------------------------------------ limite par session
    def compter_ecriture(self, session: str) -> None:
        sid = self._session(session)[0]
        with self._v:
            maintenant = self._h()
            fenetre = [x for x in self._ecritures.get(sid, []) if x > maintenant - 60]
            if len(fenetre) >= LIMITE_ECRITURES_MINUTE:
                raise TropDeRequetes("trop d'actions en une minute : réessayez dans un instant")
            fenetre.append(maintenant)
            self._ecritures[sid] = fenetre
            if len(self._ecritures) > 10_000:                 # borne (H2) : on oublie les plus anciennes sessions
                for k in list(self._ecritures)[:5_000]:
                    del self._ecritures[k]
