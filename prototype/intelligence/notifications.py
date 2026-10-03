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
SMS_MAX = 480                                         # trois SMS au plus ; le lien de désinscription n'est jamais coupé


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

    def _lire_jeton(self, jeton: str) -> Optional[tuple[str, str]]:
        """(membre, canal) si la signature est bonne, sinon None. Découpé par la DROITE (audit M3 : un identifiant de
        membre peut contenir des points)."""
        morceaux = (jeton or "").rsplit(".", 3)
        if len(morceaux) != 4 or morceaux[1] not in CANAUX_ENVOYES:
            return None
        pid, canal, nonce, sig = morceaux
        return (pid, canal) if hmac.compare_digest(self._sig(pid, canal, nonce), sig) else None

    def signature_valide(self, jeton: str) -> bool:
        return self._lire_jeton(jeton) is not None

    def desinscrire(self, jeton: str) -> dict:
        lu = self._lire_jeton(jeton)
        if lu is None:
            raise NonAuthentifie("lien de désinscription invalide")
        pid, canal = lu
        if canal not in self._desinscrits(pid):
            self.c.banc._ecrire("NOTIF_DESINSCRIPTION", [pid], Statut.DECLARE, canal=canal)
        return {"canal": canal, "desinscrit": True}

    def _desinscrits(self, pid: str) -> set[str]:
        return {e.donnees["canal"] for e in self.c.journal.evenements("NOTIF_DESINSCRIPTION") if e.acteurs == [pid]}

    # ------------------------------------------------------------------ envoi : préparer (verrou), expédier (sans), tracer (verrou)
    def preparer(self, pid: str, modele: str, donnees: dict, lien: Optional[str] = None) -> list[dict]:
        """AUDIT des lots 4-5, B1 : tout ce qui lit le monde se fait ici (sous le verrou) ; l'envoi réseau, jamais."""
        if modele not in MODELES:
            raise Invalide("modèle inconnu")
        ident = self.c.coffre.identite(pid)
        prefs = espace_membre.preferences(self.c, pid)
        langue = prefs["langue"] if prefs["langue"] in MODELES[modele] else "fr"
        repli = langue != prefs["langue"]
        deja = {e.donnees["canal"] for e in self.c.journal.evenements("NOTIF_ENVOI") if e.acteurs == [pid]
                and e.donnees["modele"] == modele and e.donnees["resultat"] in ("envoye", "simule") and e.le == self.c.jour}
        res = []
        for canal in [x for x in CANAUX_ENVOYES if x in prefs["canaux"]]:
            env = {"pid": pid, "canal": canal, "modele": modele, "langue": langue, "statut": "ignore", "raison": ""}
            env["raison"] = ("membre inconnu" if ident is None else "pause" if espace_membre.en_pause(self.c, pid)
                             else "desinscrit" if canal in self._desinscrits(pid)
                             else "déjà envoyé aujourd'hui" if canal in deja           # audit I2 : jamais de doublon
                             else "sans numéro" if canal == "sms" and not ident.telephone else "")
            if env["raison"]:
                res.append(env)
                continue
            assert ident is not None
            t = MODELES[modele][langue]
            arret = self.lien_desinscription(pid, canal)
            valeurs = {**donnees, "lien": lien or self.base + "/app"}
            if canal == "email":
                env |= {"a": ident.courriel, "sujet": t["sujet"].format(**valeurs),
                        "texte": t["corps"].format(**valeurs) + "\n\n" + PIED[langue].format(arret=arret) + "\n",
                        "entetes": {"List-Unsubscribe": f"<{arret}>"}}
            else:
                stop = f" STOP : {arret}"                           # audit M1 : le corps est coupé, jamais le lien
                env |= {"a": ident.telephone, "sujet": "", "texte": t["sms"].format(**valeurs)[:SMS_MAX - len(stop)] + stop,
                        "entetes": {}}
            if not _adresse_sure(canal, env["a"]):
                env |= {"statut": "echec", "raison": "adresse invalide"}            # audit I1 : suivi, jamais envoyé
            else:
                env |= {"statut": "a_envoyer", "raison": "repli fr" if repli else ""}
            res.append(env)
        return res

    def expedier(self, envois: list[dict]) -> list[dict]:
        """SANS le verrou du monde : chaque envoi est indépendant ; toute erreur est un échec suivi (audit I1)."""
        for env in envois:
            if env["statut"] != "a_envoyer":
                continue
            ad = self.adaptateurs[env["canal"]]
            try:
                ad.envoyer(env["a"], env["sujet"], env["texte"], env["entetes"])
                env["statut"] = "simule" if isinstance(ad, Simule) else "envoye"
            except Exception as e:  # noqa: BLE001 — une ligne ne casse jamais la relance
                env |= {"statut": "echec", "raison": type(e).__name__}
        return envois

    def tracer(self, envois: list[dict]) -> list[dict]:
        res = []
        for env in envois:
            self.c.banc._ecrire("NOTIF_ENVOI", [env["pid"]], Statut.OBSERVE, canal=env["canal"], modele=env["modele"],
                                resultat=env["statut"], raison=env["raison"], langue=env["langue"])
            res.append({k: env[k] for k in ("canal", "modele", "statut", "raison", "langue")})
        return res

    def envoyer(self, pid: str, modele: str, donnees: dict, lien: Optional[str] = None) -> list[dict]:
        """Les trois temps d'un coup (usage hors serveur : scripts, tests)."""
        return self.tracer(self.expedier(self.preparer(pid, modele, donnees, lien)))

    def suivi(self) -> dict:
        """Agrégats seulement : par canal et statut (aucun destinataire)."""
        compte: dict[tuple[str, str], int] = {}
        for e in self.c.journal.evenements("NOTIF_ENVOI"):
            cle = (e.donnees["canal"], e.donnees["resultat"])
            compte[cle] = compte.get(cle, 0) + 1
        return {"envois": [{"canal": k[0], "statut": k[1], "nombre": n} for k, n in sorted(compte.items())],
                "desinscriptions": len(self.c.journal.evenements("NOTIF_DESINSCRIPTION"))}


def _adresse_sure(canal: str, a: str) -> bool:
    """Une seule adresse, sans retour à la ligne (audit I1 : injection d'en-têtes, plusieurs destinataires)."""
    if not a or "\r" in a or "\n" in a:
        return False
    if canal == "sms":
        return all(ch.isdigit() or ch in "+ -()" for ch in a)
    from email.utils import getaddresses
    adresses = getaddresses([a])
    return len(adresses) == 1 and "@" in adresses[0][1] and adresses[0][1] == a.strip() and "," not in a


def depuis_env(c: "ClubPulse", base: str, env: Optional[dict] = None) -> Notifications:
    """La configuration vient de l'environnement seulement (jamais du dépôt). Sans SMTP_HOST : e-mail SIMULÉ (la
    démonstration) ; SMS : faux fournisseur si HACKVS_SMS=faux, sinon simulé (aucun vrai fournisseur branché)."""
    import os
    e = os.environ if env is None else env
    if e.get("SMTP_HOST"):
        email: Adaptateur = SmtpGenerique(e["SMTP_HOST"], int(e.get("SMTP_PORT") or 587),
                                          expediteur=e.get("SMTP_EXPEDITEUR") or "club@exemple.invalid",
                                          utilisateur=e.get("SMTP_UTILISATEUR", ""), mot_de_passe=e.get("SMTP_MOT_DE_PASSE", ""),
                                          starttls=e.get("SMTP_STARTTLS", "1") != "0", delai_s=float(e.get("SMTP_DELAI_S") or 15))
    else:
        email = Simule("email")
    sms: Adaptateur = FauxSms() if e.get("HACKVS_SMS") == "faux" else Simule("sms")
    secret = hmac.new(c.reglages.secret, b"notifications|annee-1", hashlib.sha256).digest()
    return Notifications(c, email=email, sms=sms, base=base, secret=secret)


def preparer_relance(n: Notifications) -> list[dict]:
    """Sous le verrou : la liste des envois de la relance (chaque membre qui a des demandes en attente)."""
    envois: list[dict] = []
    for p in n.c.r.profils:
        asks = n.c.asks_pour(p.id)
        if asks:
            envois += n.preparer(p.id, "demandes_en_attente", {"nombre": len(asks)}, lien=n.base + "/app")
    return envois


def bilan_relance(envois: list[dict]) -> dict:
    compte = {"envoye": 0, "simule": 0, "ignore": 0, "echec": 0, "membres": len({e["pid"] for e in envois})}
    for e in envois:
        compte[e["statut"]] += 1
    return compte


def relancer_demandes(n: Notifications) -> dict:
    """Les trois temps d'un coup (hors serveur). Le serveur, lui, n'expédie JAMAIS sous le verrou du monde."""
    envois = n.expedier(preparer_relance(n))
    n.tracer(envois)
    return bilan_relance(envois)
