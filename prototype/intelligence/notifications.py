"""ANNÉE 1 · LOT 5 — Notifications réelles.

- `SmtpGenerique` : n'importe quel serveur SMTP (STARTTLS par défaut, identifiants par l'environnement, jamais dans le
  dépôt) ; `FauxSms` : le faux fournisseur SMS des tests (même interface qu'un vrai) ; `Simule` : la démonstration —
  rien ne part, et c'est dit (« simule »).
- Modèles FR / DE (`MODELES`) : sujet, corps de l'e-mail, texte SMS (≤ 320 caractères). Un membre qui a choisi « en » ou
  « it » reçoit le français, et c'est noté dans le suivi (« repli fr »).
- Règles : seulement les canaux choisis par le membre (lot 3) ; RIEN pendant la pause ; rien sur un canal dont il s'est
  désinscrit (lien signé dans chaque message, et en-tête List-Unsubscribe).
- Suivi : chaque tentative est un fait NOTIF_ENVOI (canal, modèle, résultat, raison) — JAMAIS l'adresse, le numéro ni le
  contenu du message. Un échec est suivi, jamais caché ni réessayé en silence."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import smtplib
import ssl
from email.message import EmailMessage
from typing import TYPE_CHECKING, Optional, Protocol

from plateforme.affirmations import Statut

from . import espace_membre
from .erreurs import Invalide, NonAuthentifie

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

MODELES: dict[str, dict[str, dict[str, str]]] = {
    "demandes_en_attente": {
        "fr": {"sujet": "Le Club : {nombre} demande(s) attendent votre réponse",
               "corps": "Bonjour,\n\n{nombre} demande(s) de membres du Club attendent votre oui, votre non ou un « pas cette "
                        "fois ». Une réponse prend une minute :\n{lien}\n\nBelle journée,\nLe secrétariat du Club",
               "sms": "Le Club : {nombre} demande(s) attendent votre réponse (oui / non / pas cette fois). {lien}"},
        "de": {"sujet": "Der Club: {nombre} Anfragen warten auf Ihre Antwort",
               "corps": "Guten Tag\n\n{nombre} Anfragen von Clubmitgliedern warten auf Ihr Ja, Ihr Nein oder ein « diesmal "
                        "nicht ». Eine Antwort dauert eine Minute:\n{lien}\n\nFreundliche Grüsse\nDas Clubsekretariat",
               "sms": "Der Club: {nombre} Anfragen warten auf Ihre Antwort (ja / nein / diesmal nicht). {lien}"},
    },
    "bienvenue": {
        "fr": {"sujet": "Bienvenue au Club", "corps": "Bonjour,\n\nVotre accès au Club est ouvert :\n{lien}\n\nLe secrétariat du Club",
               "sms": "Bienvenue au Club : votre accès est ouvert. {lien}"},
        "de": {"sujet": "Willkommen im Club", "corps": "Guten Tag\n\nIhr Zugang zum Club ist offen:\n{lien}\n\nDas Clubsekretariat",
               "sms": "Willkommen im Club: Ihr Zugang ist offen. {lien}"},
    },
}
PIED = {"fr": "— Ne plus recevoir ces e-mails : {arret}", "de": "— Diese E-Mails nicht mehr erhalten: {arret}"}
CANAUX_ENVOYES = ("email", "sms")                     # « app » : l'application elle-même, rien à envoyer


class Adaptateur(Protocol):
    canal: str

    def envoyer(self, destinataire: str, sujet: str, texte: str, entetes: dict[str, str]) -> None: ...


class SmtpGenerique:
    canal = "email"

    def __init__(self, hote: str, port: int = 587, *, expediteur: str, utilisateur: str = "", mot_de_passe: str = "",
                 starttls: bool = True, delai_s: float = 15.0):
        self.hote, self.port, self.expediteur = hote, port, expediteur
        self._utilisateur, self._mdp, self.starttls, self.delai = utilisateur, mot_de_passe, starttls, delai_s

    def __repr__(self) -> str:                        # jamais le mot de passe dans une trace
        return f"SmtpGenerique({self.hote}:{self.port})"

    def envoyer(self, destinataire: str, sujet: str, texte: str, entetes: dict[str, str]) -> None:
        m = EmailMessage()
        m["From"], m["To"], m["Subject"] = self.expediteur, destinataire, sujet
        for k, v in entetes.items():
            m[k] = v
        m.set_content(texte)
        with smtplib.SMTP(self.hote, self.port, timeout=self.delai) as s:
            if self.starttls:
                s.starttls(context=ssl.create_default_context())
            if self._utilisateur:
                s.login(self._utilisateur, self._mdp)
            s.send_message(m)


class FauxSms:
    """Faux fournisseur SMS : garde les envois en mémoire (tests, démonstration). Un vrai fournisseur suit la même interface."""
    canal = "sms"

    def __init__(self) -> None:
        self.envoyes: list[dict] = []

    def envoyer(self, destinataire: str, sujet: str, texte: str, entetes: dict[str, str]) -> None:
        self.envoyes.append({"a": destinataire, "texte": texte})
        del self.envoyes[:-200]                           # borné


class Simule:
    """Démonstration : rien ne part. Le suivi dit « simule »."""

    def __init__(self, canal: str):
        self.canal = canal

    def envoyer(self, destinataire: str, sujet: str, texte: str, entetes: dict[str, str]) -> None:
        return None


class Notifications:
    def __init__(self, c: "ClubPulse", *, email: Adaptateur, sms: Adaptateur, base: str, secret: bytes):
        self.c, self.adaptateurs, self.base, self._secret = c, {"email": email, "sms": sms}, base.rstrip("/"), secret

    # ------------------------------------------------------------------ désinscription (lien signé)
    def _sig(self, pid: str, canal: str, nonce: str) -> str:
        return hmac.new(self._secret, f"desinscription|{pid}|{canal}|{nonce}".encode(), hashlib.sha256).hexdigest()[:32]

    def lien_desinscription(self, pid: str, canal: str) -> str:
        nonce = secrets.token_urlsafe(6).replace(".", "_")
        return f"{self.base}/desinscription#j={pid}.{canal}.{nonce}.{self._sig(pid, canal, nonce)}"

    def desinscrire(self, jeton: str) -> dict:
        morceaux = (jeton or "").split(".")
        if len(morceaux) != 4 or morceaux[1] not in CANAUX_ENVOYES:
            raise NonAuthentifie("lien de désinscription invalide")
        pid, canal, nonce, sig = morceaux
        if not hmac.compare_digest(self._sig(pid, canal, nonce), sig):
            raise NonAuthentifie("lien de désinscription invalide")
        if canal not in self._desinscrits(pid):
            self.c.banc._ecrire("NOTIF_DESINSCRIPTION", [pid], Statut.DECLARE, canal=canal)
        return {"canal": canal, "desinscrit": True}

    def _desinscrits(self, pid: str) -> set[str]:
        return {e.donnees["canal"] for e in self.c.journal.evenements("NOTIF_DESINSCRIPTION") if e.acteurs == [pid]}

    # ------------------------------------------------------------------ envoi
    def envoyer(self, pid: str, modele: str, donnees: dict, lien: Optional[str] = None) -> list[dict]:
        if modele not in MODELES:
            raise Invalide("modèle inconnu")
        ident = self.c.coffre.identite(pid)
        prefs = espace_membre.preferences(self.c, pid)
        langue = prefs["langue"] if prefs["langue"] in MODELES[modele] else "fr"
        res = []
        for canal in [x for x in CANAUX_ENVOYES if x in prefs["canaux"]]:
            raison = ("membre inconnu" if ident is None else "pause" if espace_membre.en_pause(self.c, pid)
                      else "desinscrit" if canal in self._desinscrits(pid)
                      else "sans numéro" if canal == "sms" and not ident.telephone else "")
            if raison:
                res.append(self._tracer(pid, canal, modele, "ignore", raison, langue))
                continue
            assert ident is not None
            t = MODELES[modele][langue]
            arret = self.lien_desinscription(pid, canal)
            valeurs = {**donnees, "lien": lien or self.base + "/app"}
            ad = self.adaptateurs[canal]
            try:
                if canal == "email":
                    corps = t["corps"].format(**valeurs) + "\n\n" + PIED[langue].format(arret=arret) + "\n"
                    ad.envoyer(ident.courriel, t["sujet"].format(**valeurs), corps, {"List-Unsubscribe": f"<{arret}>"})
                else:
                    ad.envoyer(ident.telephone, "", (t["sms"].format(**valeurs) + f" STOP : {arret}")[:320], {})
            except (OSError, smtplib.SMTPException) as e:
                res.append(self._tracer(pid, canal, modele, "echec", type(e).__name__, langue))
                continue
            res.append(self._tracer(pid, canal, modele, "simule" if isinstance(ad, Simule) else "envoye", "", langue))
        return res

    def _tracer(self, pid: str, canal: str, modele: str, statut: str, raison: str, langue: str) -> dict:
        self.c.banc._ecrire("NOTIF_ENVOI", [pid], Statut.OBSERVE, canal=canal, modele=modele, resultat=statut, raison=raison,
                            langue=langue)
        return {"canal": canal, "modele": modele, "statut": statut, "raison": raison, "langue": langue}

    def suivi(self) -> dict:
        """Agrégats seulement : par canal et statut (aucun destinataire)."""
        compte: dict[tuple[str, str], int] = {}
        for e in self.c.journal.evenements("NOTIF_ENVOI"):
            cle = (e.donnees["canal"], e.donnees["resultat"])
            compte[cle] = compte.get(cle, 0) + 1
        return {"envois": [{"canal": k[0], "statut": k[1], "nombre": n} for k, n in sorted(compte.items())],
                "desinscriptions": len(self.c.journal.evenements("NOTIF_DESINSCRIPTION"))}


def depuis_env(c: "ClubPulse", base: str, env: Optional[dict] = None) -> Notifications:
    """La configuration vient de l'environnement seulement (jamais du dépôt). Sans SMTP_HOST : e-mail SIMULÉ (la
    démonstration) ; SMS : faux fournisseur si HACKVS_SMS=faux, sinon simulé (aucun vrai fournisseur branché)."""
    import os
    e = os.environ if env is None else env
    if e.get("SMTP_HOST"):
        email: Adaptateur = SmtpGenerique(e["SMTP_HOST"], int(e.get("SMTP_PORT") or 587),
                                          expediteur=e.get("SMTP_EXPEDITEUR") or "club@exemple.invalid",
                                          utilisateur=e.get("SMTP_UTILISATEUR", ""), mot_de_passe=e.get("SMTP_MOT_DE_PASSE", ""),
                                          starttls=e.get("SMTP_STARTTLS", "1") != "0")
    else:
        email = Simule("email")
    sms: Adaptateur = FauxSms() if e.get("HACKVS_SMS") == "faux" else Simule("sms")
    secret = hmac.new(c.reglages.secret, b"notifications|annee-1", hashlib.sha256).digest()
    return Notifications(c, email=email, sms=sms, base=base, secret=secret)


def relancer_demandes(n: Notifications) -> dict:
    """Le secrétariat relance chaque membre qui a des demandes en attente (« demandes_en_attente », avec leur nombre).
    Rend des décomptes seulement."""
    compte = {"envoye": 0, "simule": 0, "ignore": 0, "echec": 0, "membres": 0}
    for p in n.c.r.profils:
        asks = n.c.asks_pour(p.id)
        if not asks:
            continue
        compte["membres"] += 1
        for x in n.envoyer(p.id, "demandes_en_attente", {"nombre": len(asks)}, lien=n.base + "/app"):
            compte[x["statut"]] += 1
    return compte
