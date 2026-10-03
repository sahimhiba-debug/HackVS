"""MODE SALLE — « LE CLUB, C'EST VOUS » (Foire 2026 · P0, interrupteur HACKVS_SALLE).

Pendant le pitch, la salle (jusqu'à 80 téléphones) scanne UN QR et devient le Club pendant cinq minutes.

- QR « salle » MULTI-USAGE (signé, valable le temps de la séance) ; chaque scan ÉMET un passe INDIVIDUEL, rôle
  invité, 2 heures, sans compte ; PLAFOND configurable (80 par défaut, `HACKVS_SALLE_PLAFOND`) ; débit limité par les
  routes (par passe et global, jamais par adresse IP : une salle partage la même).
- Accueil en DEUX GESTES : choisir UNE capacité dans une courte liste, puis consentir — un reçu.
- Le présentateur LANCE la demande « Accueillir une délégation d'acheteurs germanophones » : trois pièces (voiture,
  salle, allemand). Chaque participant qui porte une de ces capacités la reçoit : Oui / Non / Pas cette fois. Le premier
  oui par pièce la FOURNIT, les suivants sont EN RÉSERVE (consentement donné pour cette finalité). L'anneau se ferme
  quand les trois pièces sont fournies.
- RETRAIT (par le participant, ou déclenché par la télécommande — « simulé en démonstration ») : la pièce se libère,
  la réserve la reprend (RECOMPOSITION), sinon la demande repart. Sous 3 porteurs d'une capacité, le rôle n'est PAS dit.
- ÉCRAN GÉANT : participants, capacités par métier (k = 3), anneau, fil des faits en RÔLES — jamais de nom (il n'y en a
  pas : personne ne donne son nom). BASCULE : moins de N participants (`HACKVS_SALLE_MIN`, 5) 60 s après l'ouverture →
  l'écran propose la démonstration scriptée.
- PURGE TOTALE : une commande efface TOUT (passes, capacités, réponses, reçus) et change la clé de la séance — un
  ancien passe ne vaut plus rien. L'état vit EN MÉMOIRE, hors du journal du Club : rien n'en reste après la purge ou
  l'arrêt du serveur (« Démonstration : vos données sont effacées après la présentation »)."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from collections import Counter
from typing import Callable, Optional

from .erreurs import Conflit, Invalide, Limite, NonAuthentifie

CAPACITES = [  # (id, libellé FR, libellé DE, métier de la taxonomie)
    ("voiture", "J'ai une voiture", "Ich habe ein Auto", "transport"),
    ("salle", "J'ai une salle de réunion", "Ich habe einen Sitzungsraum", "salle"),
    ("allemand", "Je parle allemand", "Ich spreche Deutsch", "interprete"),
    ("traiteur", "Je peux nourrir 20 personnes", "Ich kann 20 Personen verpflegen", "traiteur"),
    ("informatique", "Je m'y connais en informatique", "Ich kenne mich mit Informatik aus", "informatique"),
    ("materiel", "J'ai du matériel (tables, sono)", "Ich habe Material (Tische, Tonanlage)", "logistique"),
]
IDS = [c[0] for c in CAPACITES]
ROLE = {"voiture": "transport", "salle": "lieu", "allemand": "voix", "traiteur": "traiteur", "informatique": "informatique",
        "materiel": "matériel"}
DEMANDE: dict = {"titre": "Accueillir une délégation d'acheteurs germanophones", "titre_de": "Eine Delegation deutschsprachiger Einkäufer empfangen",
           "pieces": ["voiture", "salle", "allemand"],
           "texte": "Vendredi, le Club accueille huit acheteurs germanophones : il faut une voiture, une salle, et quelqu'un qui parle allemand.",
           "texte_de": "Am Freitag empfängt der Club acht deutschsprachige Einkäufer: Es braucht ein Auto, einen Raum und jemanden, der Deutsch spricht."}
FINALITE = "Mode salle : utiliser la capacité que je déclare pour la demande lancée pendant cette présentation, et rien d'autre."
EFFACEMENT = "Démonstration : vos données sont effacées après la présentation."
CHOIX = ("oui", "non", "pas cette fois")


def _k(n: int, k: int):
    return f"< {k}" if 0 < n < k else n


class Salle:
    def __init__(self, secret: bytes, plafond: int = 80, minimum: int = 5, duree_passe_s: int = 2 * 3600, k: int = 3,
                 horloge: Callable[[], float] = time.time):
        self._secret_base, self.plafond, self.minimum, self.duree, self.k, self._h = secret, plafond, minimum, duree_passe_s, k, horloge
        self._v = threading.RLock()
        self.purger()
        self.purges = 0

    # ------------------------------------------------------------------ séance
    def purger(self) -> dict:
        """Efface TOUT et change la clé de la séance : aucun passe émis avant ne vaut plus rien."""
        with self._v:
            self._cle = hmac.new(self._secret_base, b"salle|" + secrets.token_bytes(16), hashlib.sha256).digest()
            self.ouverte_le: Optional[float] = None
            self.invitee_le: Optional[float] = None          # « Sortez vos téléphones » (régie) : la minute de bascule part d'ici
            self.participants: dict[str, dict] = {}          # nonce → {capacite, consenti_le, reponse, statut, retire}
            self.demande_le: Optional[float] = None
            self.fournisseurs: dict[str, Optional[str]] = {}  # pièce → nonce
            self.fil: list[dict] = []
            self.ferme_le: Optional[float] = None
            self.vue = "salle"                               # ce que montre l'écran géant : « salle » ou « bilan »
            self.purges = getattr(self, "purges", 0) + 1
            return {"purge": True, "message": EFFACEMENT}

    def _sig(self, usage: str, x: str) -> str:
        return hmac.new(self._cle, f"{usage}|{x}".encode(), hashlib.sha256).hexdigest()[:32]

    def ouvrir(self) -> dict:
        with self._v:
            if self.ouverte_le is None:
                self.ouverte_le = self._h()
                self._noter("la salle est ouverte")
            return {"jeton_salle": "s1." + self._sig("qr", "salle"), "ouverte_le": self.ouverte_le}

    def inviter(self) -> dict:
        """AUDIT D1 : la salle s'ouvre à H-30 (vérifications) ; la minute après laquelle, faute de participants, l'écran
        propose la démo scriptée ne part QUE de l'invitation en séance (« Sortez vos téléphones », bouton de la régie)."""
        with self._v:
            if self.ouverte_le is None:
                raise Conflit("la salle n'est pas ouverte")
            self.invitee_le = self._h()
            self._noter("la salle est invitée à scanner")
            return {"invitee": True}

    def _noter(self, texte: str) -> None:
        self.fil.append({"t": round(self._h() - (self.ouverte_le if self.ouverte_le is not None else self._h())), "texte": texte})
        del self.fil[:-40]

    # ------------------------------------------------------------------ participant
    def entrer(self, jeton_salle: str) -> dict:
        with self._v:
            if self.ouverte_le is None or not hmac.compare_digest(jeton_salle or "", "s1." + self._sig("qr", "salle")):
                raise NonAuthentifie("QR de salle invalide ou séance terminée")
            if len(self.participants) >= self.plafond:
                raise Limite(f"la salle est pleine ({self.plafond} participants)")
            nonce = secrets.token_urlsafe(9)
            exp = int(self._h()) + self.duree
            self.participants[nonce] = {"capacite": None, "consenti_le": None, "reponse": None, "statut": None, "exp": exp,
                                        "place": self._place(nonce)}
            return {"passe": f"p1.{nonce}.{exp}.{self._sig('passe', f'{nonce}|{exp}')}", "expire": exp, "role": "invité",
                    "message": EFFACEMENT}

    def _participant(self, passe: str) -> tuple[str, dict]:
        p = (passe or "").split(".")
        if len(p) != 4 or p[0] != "p1" or not p[2].isdigit() or not hmac.compare_digest(p[3], self._sig("passe", f"{p[1]}|{p[2]}")):
            raise NonAuthentifie("passe de salle invalide (ou effacé par la purge)")
        if int(p[2]) < self._h():
            raise NonAuthentifie("passe de salle expiré")
        x = self.participants.get(p[1])
        if x is None:
            raise NonAuthentifie("passe de salle inconnu")
        return p[1], x

    def declarer(self, passe: str, capacite: str, consentement: bool) -> dict:
        with self._v:
            nonce, x = self._participant(passe)
            if capacite not in IDS:
                raise Invalide("capacité inconnue")
            if not consentement:
                raise Invalide("le consentement est nécessaire pour déclarer une capacité")
            if x["capacite"]:
                raise Conflit("capacité déjà déclarée")
            x["capacite"], x["consenti_le"] = capacite, int(self._h())
            return {"recu": self._recu(nonce, x), "message": EFFACEMENT}

    def _recu(self, nonce: str, x: dict) -> dict:
        etat = {"fournit": "valable — votre pièce sert la demande", "reserve": "valable — en réserve", "retire": "consentement retiré"}
        return {"reference": f"salle-{nonce[:8]}", "capacite": dict((c[0], c[1]) for c in CAPACITES)[x["capacite"]],
                "finalite": FINALITE, "donne_le": x["consenti_le"], "etat": etat.get(x["statut"] or "", "valable"),
                "revocable": True, "simule": "simulé en démonstration"}

    def moi(self, passe: str) -> dict:
        with self._v:
            nonce, x = self._participant(passe)
            demande = None
            if self.demande_le and x["capacite"] in DEMANDE["pieces"] and x["reponse"] is None:
                demande = {"titre": DEMANDE["titre"], "titre_de": DEMANDE["titre_de"], "texte": DEMANDE["texte"],
                           "texte_de": DEMANDE["texte_de"], "piece": ROLE[x["capacite"]], "choix": list(CHOIX)}
            return {"capacites": [{"id": c[0], "fr": c[1], "de": c[2]} for c in CAPACITES], "declaree": x["capacite"],
                    "recu": self._recu(nonce, x) if x["capacite"] else None, "demande": demande, "reponse": x["reponse"],
                    "message": EFFACEMENT, "monde": "monde de démonstration"}

    def repondre(self, passe: str, choix: str) -> dict:
        with self._v:
            nonce, x = self._participant(passe)
            if choix not in CHOIX:
                raise Invalide("oui, non ou pas cette fois")
            if not self.demande_le or x["capacite"] not in DEMANDE["pieces"]:
                raise Conflit("aucune demande pour vous en ce moment")
            if x["reponse"] is not None:
                raise Conflit("déjà répondu")
            x["reponse"] = choix
            if choix == "oui":
                piece = x["capacite"]
                if not self.fournisseurs.get(piece):
                    self.fournisseurs[piece], x["statut"] = nonce, "fournit"
                    self._noter(f"{self._role(piece)}pièce fournie")
                    self._fermer_si_complet()
                else:
                    x["statut"] = "reserve"
            return {"reponse": choix, "recu": self._recu(nonce, x)}

    def retirer(self, passe: str) -> dict:
        with self._v:
            nonce, x = self._participant(passe)
            return self._retirer(nonce, x, simule=False)

    def _retirer(self, nonce: str, x: dict, simule: bool) -> dict:
        if x["statut"] not in ("fournit", "reserve"):
            raise Conflit("aucun consentement à retirer pour la demande")
        piece, fournissait = x["capacite"], x["statut"] == "fournit"
        x["statut"] = "retire"
        if fournissait:
            self.fournisseurs[piece] = None
            self.ferme_le = None
            self._noter(f"{self._role(piece)}ce composant n'est plus disponible" if self._role(piece) else "un composant n'est plus disponible")
            relais = next((n for n, y in self.participants.items() if y["capacite"] == piece and y["statut"] == "reserve"), None)
            if relais:
                self.fournisseurs[piece] = relais
                self.participants[relais]["statut"] = "fournit"
                self._noter("recomposition : une autre personne de la salle reprend la pièce")
                self._fermer_si_complet()
            else:
                self._noter("la demande repart vers la salle")
        return {"retire": True, "message": "Consentement retiré. Personne ne sera prévenu que c'est vous.",
                **({"simule": "simulé en démonstration"} if simule else {})}

    def _role(self, piece: str) -> str:
        """« transport : » — seulement si au moins k participants portent cette capacité ; sinon rien (k-anonymat)."""
        n = sum(1 for y in self.participants.values() if y["capacite"] == piece)
        return f"{ROLE[piece]} : " if n >= self.k else ""

    def _fermer_si_complet(self) -> None:
        if all(self.fournisseurs.get(p) for p in DEMANDE["pieces"]) and self.ferme_le is None:
            self.ferme_le = self._h()
            self._noter("l'anneau se ferme : le Club peut le faire")

    # ------------------------------------------------------------------ télécommande (console)
    def lancer(self) -> dict:
        with self._v:
            if self.ouverte_le is None:
                raise Conflit("ouvrez d'abord la salle")
            if self.demande_le is None:
                self.demande_le = self._h()
                self.fournisseurs = {p: None for p in DEMANDE["pieces"]}
                self._noter("demande lancée vers la salle : " + DEMANDE["titre"])
            return self.ecran()

    def declencher_retrait(self) -> dict:
        with self._v:
            cible = next(((n, y) for n, y in self.participants.items() if y["statut"] == "fournit"), None)
            if cible is None:
                raise Conflit("aucune pièce fournie à retirer")
            self._retirer(*cible, simule=True)
            return self.ecran() | {"simule": "retrait déclenché par la télécommande — simulé en démonstration"}

    def afficher(self, vue: str) -> dict:
        """La télécommande choisit ce que montre l'écran géant — côté serveur : la télécommande peut être un téléphone."""
        if vue not in ("salle", "bilan"):
            raise Invalide("vue : salle ou bilan")
        with self._v:
            self.vue = vue
            return {"vue": vue}

    # ------------------------------------------------------------------ écran géant (agrégats seulement)
    def ecran(self) -> dict:
        with self._v:
            ps = list(self.participants.values())
            n = len(ps)
            depuis = round(self._h() - self.ouverte_le) if self.ouverte_le is not None else 0
            par_metier = Counter(y["capacite"] for y in ps if y["capacite"])
            rep = Counter(y["reponse"] for y in ps if y["reponse"])
            return {
                "ouverte": self.ouverte_le is not None, "depuis_s": depuis, "participants": _k(n, self.k), "plafond": self.plafond,
                "capacites": [{"id": c[0], "libelle": c[1], "role": ROLE[c[0]], "n": _k(par_metier.get(c[0], 0), self.k)} for c in CAPACITES],
                "demande": None if not self.demande_le else {
                    "titre": DEMANDE["titre"], "pieces": [{"role": ROLE[p], "fournie": bool(self.fournisseurs.get(p))} for p in DEMANDE["pieces"]],
                    "fermee": self.ferme_le is not None,
                    "secondes_pour_fermer": round(self.ferme_le - self.demande_le) if self.ferme_le else None},
                "reponses": {c: _k(rep.get(c, 0), self.k) for c in CHOIX},
                "bascule": self.invitee_le is not None and self._h() - self.invitee_le >= 60 and n < self.minimum,
                "invitee": self.invitee_le is not None, "minimum": self.minimum,
                "constellation": self._constellation(),
                "fil": list(self.fil[-12:]), "vue": self.vue, "message": EFFACEMENT, "monde": "monde de démonstration",
            }

    def _place(self, nonce: str) -> int:
        """Une PLACE sur la spirale de Vogel : sondage à partir d'un HMAC de la clé de séance — stable, sans lien avec
        l'ordre d'arrivée ni l'identité (la place suivante libre en cas de collision)."""
        prises = {y["place"] for y in self.participants.values() if "place" in y}
        depart = int.from_bytes(hmac.new(self._cle, b"place|" + nonce.encode(), hashlib.sha256).digest()[:4], "big") % self.plafond
        return next(((depart + i) % self.plafond for i in range(self.plafond) if (depart + i) % self.plafond not in prises), depart)

    def _constellation(self) -> list[dict]:
        """CONSTELLATION (écran géant) : un point par participant, à sa place sur la spirale ; un état seulement —
        « fournit » (son oui sert la demande), « reserve » (oui en réserve), ou rien. Un NON ou un « pas cette fois » ne
        se distingue jamais d'un silence ; aucun identifiant. Sous k participants : aucun point."""
        if len(self.participants) < self.k:
            return []
        return sorted(({"s": y["place"], "e": y["statut"] if y["statut"] in ("fournit", "reserve") else ""}
                       for y in self.participants.values()), key=lambda q: q["s"])

    def bilan(self) -> dict:
        """« En cinq minutes, cette salle a rendu possible… » — agrégats, k = 3."""
        e = self.ecran()
        minutes = max(1, round(e["depuis_s"] / 60)) if e["ouverte"] else 0
        duree = "une minute" if minutes <= 1 else f"{minutes} minutes"
        possible = bool(e["demande"] and e["demande"]["fermee"])
        return {"minutes": minutes, "participants": e["participants"], "capacites": [c for c in e["capacites"] if c["n"]],
                "reponses": e["reponses"], "possible": possible,
                "phrase": (f"En {duree}, cette salle a rendu possible : « {DEMANDE['titre']} »." if possible
                           else f"En {duree}, cette salle a déclaré ses capacités ; la demande attend encore une pièce."),
                "message": EFFACEMENT, "monde": "monde de démonstration"}
