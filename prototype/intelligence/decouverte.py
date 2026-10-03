"""PASSE DÉCOUVERTE (Foire 2026 · D) — une entreprise qui n'est pas membre essaie le Club pendant 90 jours.

Le Club remet un passe (lien + QR), soit depuis « le Club cherche » (lié à UNE demande restée sans réponse), soit depuis
un QR générique de stand. Le passe est :
- SIGNÉ (HMAC du secret du processus) — un passe inventé ou d'un autre monde ne vaut rien ;
- À USAGE UNIQUE À L'ÉMISSION — un lien activé une fois ne s'active plus ; il ouvre une session d'INVITÉ ;
- BORNÉ : 90 jours de l'horloge du monde (`HACKVS_DECOUVERTE_JOURS`), au plus 3 demandes répondues ;
- RÉVOCABLE par le Club (la session d'invité meurt aussitôt) ;
- LIMITÉ en débit (routes : par code et global, jamais par adresse IP — comme le QR juré).

L'invité déclare son entreprise (nom LIBRE, métier de la taxonomie, zone) et reçoit un REÇU de consentement : la
finalité est dite, révocable. Le nom n'apparaît sur AUCUN écran du Club — il reste sur le téléphone de l'invité.
Répondre « je peux aider » à une demande est une PROPOSITION transmise au Club : elle ne devient jamais une pièce
consentie d'une capacité (un invité n'est pas membre). « Rejoindre le Club » écrit une INTENTION, rien de plus : la
page « prévu ensuite » dit ce que le Club fera. Le Suivi les compte (jamais appelées « conversions »).

Tout l'état est RECALCULÉ depuis le journal (rien en mémoire) : un redémarrage sur le même journal rend les mêmes passes."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import date, timedelta
from typing import TYPE_CHECKING, Optional

from plateforme.affirmations import Statut

from . import metiers
from .erreurs import Conflit, Invalide, Limite, NonAuthentifie

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

DEMANDES_MAX = 3
FINALITE = ("Passe découverte du Club : déclarer mon entreprise et proposer mon aide sur au plus 3 demandes du Club "
            "pendant {jours} jours. Mon nom d'entreprise n'est affiché sur aucun écran du Club.")
PREVU_ENSUITE = [
    "Le Club a noté votre intention ; rien n'est engagé, ni pour vous ni pour lui.",
    "Un membre de la commission d'admission vous écrit dans les 14 jours (simulé en démonstration : aucun e-mail n'est envoyé).",
    "Vous êtes invité à la prochaine rencontre du Club, comme invité.",
    "Votre passe reste valable jusqu'à son terme ; vous pouvez le rendre à tout moment.",
]


class Decouverte:
    def __init__(self, c: "ClubPulse", jours: int = 90):
        self.c, self.jours = c, jours

    # ------------------------------------------------------------------ jetons
    def _sig(self, usage: str, nonce: str) -> str:
        return hmac.new(self.c.reglages.secret, f"decouverte|{usage}|{nonce}".encode(), hashlib.sha256).hexdigest()[:32]

    def _verifier(self, jeton: str, prefixe: str) -> str:
        parties = (jeton or "").split(".")
        if len(parties) != 3 or parties[0] != prefixe or not hmac.compare_digest(parties[2], self._sig(prefixe, parties[1])):
            raise NonAuthentifie("passe découverte invalide")
        return parties[1]

    @staticmethod
    def nonce(jeton: str) -> str:
        p = (jeton or "").split(".")
        return p[1][:40] if len(p) == 3 else "?"

    # ------------------------------------------------------------------ état (relu du journal)
    def _evs(self, type_: str) -> list:
        return self.c.journal.evenements(type_)

    def passes(self) -> dict[str, dict]:
        res: dict[str, dict] = {}
        for e in self._evs("DECOUVERTE_EMIS"):
            res[e.donnees["nonce"]] = {"nonce": e.donnees["nonce"], "origine": e.donnees["origine"], "demande": e.donnees.get("demande"),
                                       "emis_le": e.le, "jusqu_au": date.fromisoformat(e.donnees["jusqu_au"]),
                                       "active_le": None, "revoque": False, "declaration": None, "reponses": [], "intention": False}
        for type_, f in (("DECOUVERTE_ACTIVE", lambda p, e: p.update(active_le=e.le)),
                         ("DECOUVERTE_REVOQUE", lambda p, e: p.update(revoque=True)),
                         ("DECOUVERTE_DECLARATION", lambda p, e: p.update(declaration=e.donnees | {"le": e.le})),
                         ("DECOUVERTE_REPONSE", lambda p, e: p["reponses"].append(e.donnees | {"le": e.le})),
                         ("DECOUVERTE_INTENTION", lambda p, e: p.update(intention=True))):
            for e in self._evs(type_):
                if e.donnees["nonce"] in res:
                    f(res[e.donnees["nonce"]], e)
        return res

    def _valable(self, p: dict) -> bool:
        return p["active_le"] is not None and not p["revoque"] and self.c.jour <= p["jusqu_au"]

    # ------------------------------------------------------------------ Club (console)
    def emettre(self, origine: str, demande: Optional[str] = None) -> dict:
        """« startup » (P3 n°12, PONT THE ARK — proposé, à valider avec la fondation) : la même porte, deux fois plus
        longue (une jeune entreprise a besoin d'un trimestre de plus pour trouver sa place) ; rien d'autre ne change."""
        if origine not in ("stand", "demande", "startup"):
            raise Invalide("origine : stand, demande ou startup")
        if origine == "demande":
            ouvertes = {i.ask.id: i for i in self.c.projection_capacites() if i.ask is not None}
            if demande not in ouvertes:
                raise Invalide("demande inconnue ou plus ouverte")
        nonce = secrets.token_urlsafe(9)
        jours = self.jours * 2 if origine == "startup" else self.jours
        jusqu = self.c.jour + timedelta(days=jours)
        self.c.banc._ecrire("DECOUVERTE_EMIS", [], Statut.OBSERVE, nonce=nonce, origine=origine, demande=demande,
                            jusqu_au=jusqu.isoformat())
        jeton = f"d1.{nonce}.{self._sig('d1', nonce)}"
        res = {"jeton": jeton, "chemin": f"/decouverte#passe={jeton}", "nonce": nonce, "jusqu_au": jusqu.isoformat(),
               "jours": jours, "origine": origine}
        if origine == "startup":
            res["variante"] = "passe start-up · pont The Ark (proposé, à valider avec la fondation)"
        return res

    def revoquer(self, nonce: str) -> dict:
        p = self.passes().get(nonce)
        if p is None:
            raise NonAuthentifie("passe inconnu")
        if p["revoque"]:
            raise Conflit("passe déjà révoqué")
        self.c.banc._ecrire("DECOUVERTE_REVOQUE", [], Statut.OBSERVE, nonce=nonce)
        return {"nonce": nonce, "revoque": True}

    def liste(self) -> list[dict]:
        """Pour la console : l'état de chaque passe — JAMAIS le nom d'entreprise déclaré (métier et zone seulement)."""
        return [{"nonce": n, "origine": p["origine"], "emis_le": p["emis_le"].isoformat(), "jusqu_au": p["jusqu_au"].isoformat(),
                 "active": p["active_le"] is not None, "revoque": p["revoque"], "reponses": len(p["reponses"]),
                 "intention": p["intention"]} for n, p in self.passes().items()]

    # ------------------------------------------------------------------ invité
    def activer(self, jeton: str) -> dict:
        nonce = self._verifier(jeton, "d1")
        p = self.passes().get(nonce)
        if p is None:
            raise NonAuthentifie("passe découverte inconnu")
        if p["revoque"]:
            raise NonAuthentifie("passe découverte révoqué par le Club")
        if p["active_le"] is not None:
            raise Conflit("ce passe a déjà été utilisé : il est à usage unique")
        if self.c.jour > p["jusqu_au"]:
            raise NonAuthentifie("passe découverte expiré")
        self.c.banc._ecrire("DECOUVERTE_ACTIVE", [], Statut.OBSERVE, nonce=nonce)
        return {"invite": f"i1.{nonce}.{self._sig('i1', nonce)}", "jusqu_au": p["jusqu_au"].isoformat(), "role": "invité"}

    def invite(self, session: str) -> dict:
        nonce = self._verifier(session, "i1")
        p = self.passes().get(nonce)
        if p is None or not self._valable(p):
            raise NonAuthentifie("passe découverte révoqué ou expiré")
        return p

    def declarer(self, session: str, entreprise: str, metier: str, zone: str) -> dict:
        p = self.invite(session)
        entreprise = " ".join((entreprise or "").split())
        if not 2 <= len(entreprise) <= 80:
            raise Invalide("nom d'entreprise : 2 à 80 caractères")
        if metier not in metiers.ids():
            raise Invalide("métier hors taxonomie")
        if zone not in metiers.ZONES:
            raise Invalide("zone inconnue")
        finalite = FINALITE.format(jours=self.jours)
        self.c.banc._ecrire("DECOUVERTE_DECLARATION", [], Statut.OBSERVE, nonce=p["nonce"], entreprise=entreprise,
                            metier=metier, zone=zone, finalite=finalite)
        return {"recu": {"reference": f"decouverte-{p['nonce'][:8]}", "finalite": finalite, "donne_le": self.c.jour.isoformat(),
                         "jusqu_au": p["jusqu_au"].isoformat(), "revocable": True, "fictif": True}}

    def demandes(self, session: str) -> dict:
        """Les demandes ouvertes que l'invité peut voir : la sienne (passe lié) d'abord, au plus 3 à la fois, en rôles."""
        p = self.invite(session)
        repondues = {r["ask"] for r in p["reponses"]}
        ouvertes = [i for i in self.c.projection_capacites() if i.ask is not None and i.ask.id not in repondues]
        ouvertes.sort(key=lambda i: (i.ask.id != p["demande"], i.ask.id))  # type: ignore[union-attr]
        reste = DEMANDES_MAX - len(p["reponses"])
        return {"declaration": p["declaration"] and {k: p["declaration"][k] for k in ("entreprise", "metier", "zone")},
                "reste": reste, "jusqu_au": p["jusqu_au"].isoformat(), "intention": p["intention"],
                "demandes": [{"id": i.ask.id, "texte": i.ask.texte, "titre": self.c.capacites.patron(i.finalite).titre}  # type: ignore[union-attr]
                             for i in ouvertes[:max(0, min(reste, DEMANDES_MAX))]],
                "monde": "monde de démonstration", "fictif": True}

    def repondre(self, session: str, ask: str, aide: bool) -> dict:
        p = self.invite(session)
        if p["declaration"] is None:
            raise Conflit("déclarez d'abord votre entreprise")
        if len(p["reponses"]) >= DEMANDES_MAX:
            raise Limite(f"un passe découverte répond à {DEMANDES_MAX} demandes au plus")
        if ask in {r["ask"] for r in p["reponses"]}:
            raise Conflit("demande déjà répondue")
        if ask not in {i.ask.id for i in self.c.projection_capacites() if i.ask is not None}:
            raise Invalide("demande inconnue ou plus ouverte")
        self.c.banc._ecrire("DECOUVERTE_REPONSE", [], Statut.OBSERVE, nonce=p["nonce"], ask=ask, aide=aide)
        return {"ask": ask, "aide": aide, "note": "Proposition transmise au Club : elle ne remplit pas la capacité à elle seule — "
                                                   "un membre de la commission reprend contact (simulé en démonstration)."}

    def rejoindre(self, session: str) -> dict:
        p = self.invite(session)
        if not p["intention"]:
            self.c.banc._ecrire("DECOUVERTE_INTENTION", [], Statut.OBSERVE, nonce=p["nonce"])
        return {"intention": True, "prevu_ensuite": PREVU_ENSUITE, "simule": "simulé en démonstration"}

    # ------------------------------------------------------------------ Suivi
    def statistiques(self, debut: Optional[date], k: int) -> dict:
        def kk(n: int):
            return f"< {k}" if 0 < n < k else n
        ps = [p for p in self.passes().values() if p["active_le"] is not None and (debut is None or p["active_le"] >= debut)]
        hors = [p for p in ps if p["declaration"] and p["declaration"]["zone"] not in metiers.VALAIS]
        return {"actifs": kk(sum(self._valable(p) for p in ps)),
                "ont_contribue": kk(sum(any(r["aide"] for r in p["reponses"]) for p in ps)),
                "intentions_adhesion": kk(sum(p["intention"] for p in ps)),
                "hors_valais": kk(len(hors)), "emis": len([p for p in self.passes().values()
                                                           if debut is None or p["emis_le"] >= debut])}
