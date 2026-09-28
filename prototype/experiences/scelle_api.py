"""Démonstration des intentions scellées (mode démo uniquement, expérience isolée).

HONNÊTETÉ : pour la démonstration, les agents personnels tournent dans ce processus. Dans le produit visé, chaque
agent tourne chez son membre ; le serveur du Club n'est qu'un relais. Ce module garde volontairement séparés :
  - l'état de chaque agent (intentions en clair : jamais renvoyées à un autre membre) ;
  - ce que voit le relais (points aléatoires, pseudonymes) ;
  - ce que chaque membre apprend (compatibilité, puis ce que l'autre accepte de dévoiler).
"""
from __future__ import annotations

import itertools
import secrets
import time
from collections import Counter

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import psi
from .intentions import LIBELLES, Agent, Intention, Relais, compatibilite, engagement, generaliser, ouvrir


class Consentement(BaseModel):
    membre: str


def creer_routeur(profils_effectifs, taxonomie) -> APIRouter:
    r = APIRouter(prefix="/api/experiences/scelle")
    etat: dict = {}

    def scenario() -> None:
        profils = {p.id: p for p in profils_effectifs()}
        annuaire = Counter(s for p in profils.values() if p.type == "membre_club" for s in p.secteurs)
        parents = {c: taxonomie.concepts[c].parent for c in taxonomie.concepts}
        gen = lambda s: generaliser(s, annuaire, parents)  # noqa: E731
        intentions = {  # FICTIF : scénario de démonstration
            "p20": [Intention("ceder", ("menuiserie",), "Valais")],
            "p21": [Intention("reprendre", ("menuiserie", "construction_metallique"), "Valais")],
            "p02": [Intention("lever_fonds", ("logistique",), "Valais")],
            "p23": [Intention("investir", ("logistique", "boissons"), "Valais")],
            "p12": [Intention("chercher_dirigeant", ("fiduciaire",), "Valais")],
        }
        couverture = ["p00", "p01", "p05", "p10", "p13", "p15", "p22", "p26", "p28", "p30"]  # agents sans intention
        agents = {pid: Agent(pid, intentions.get(pid, []), general=gen) for pid in list(intentions) + couverture}
        etat.clear()
        etat.update(agents=agents, profils=profils, gen=gen, relais=Relais(), compat={}, consentements={}, reveles={},
                    tour=False, duree_ms=0)

    def vue_agent(pid: str) -> dict:
        a: Agent = etat["agents"][pid]
        p = etat["profils"][pid]
        comp = [{"match": k, "categorie": v["categorie"], "etape": v["etape"],
                 "pseudonyme_autre": v["pseudos"][1 - v["ids"].index(pid)],
                 "j_ai_consenti": sorted(etat["consentements"].get((k, v["etape"]), set()) & {pid}) != [],
                 "devoile": etat["reveles"].get(k, {}).get(pid)}
                for k, v in etat["compat"].items() if pid in v["ids"]]
        return {"membre": {"id": pid, "nom": p.nom, "entreprise": p.entreprise},
                "intentions": [{"libelle": LIBELLES[i.type], "secteurs": [taxonomie.libelle(s) for s in i.secteurs],
                                "jetons_envoyes": [t.split("|")[1] for t in i.jetons(etat["gen"])[0]]} for i in a.intentions],
                "compatibilites": comp}

    @r.post("/reinitialiser")
    def reinitialiser():
        scenario()
        return {"ok": True}

    @r.post("/tour")
    def tour():
        if not etat:
            scenario()
        agents, relais = etat["agents"], etat["relais"]
        for a in agents.values():
            a.pseudonyme = secrets.token_hex(3)  # pseudonymes renouvelés à chaque tour
        t0 = time.perf_counter()
        for x, y in itertools.combinations(sorted(agents), 2):
            jetons = compatibilite(agents[x], agents[y], relais)
            if jetons:
                cle = f"m{len(etat['compat']) + 1}"
                cat = jetons[0].split("|")[1]
                etat["compat"][cle] = {"ids": [x, y], "pseudos": [agents[x].pseudonyme, agents[y].pseudonyme],
                                       "categorie": "tout secteur (catégorie trop rare pour être nommée)" if cat == "*"
                                       else taxonomie.libelle(cat), "etape": "secteur"}
        etat["tour"], etat["duree_ms"] = True, round((time.perf_counter() - t0) * 1000)
        return club()

    @r.get("/club")
    def club():
        """Tout ce que le serveur du Club voit : des pseudonymes et des points aléatoires."""
        if not etat:
            scenario()
        vus = [j for (_, _, charge) in etat["relais"].vus for j in charge]
        flux = [{"de": de, "vers": vers, "points": charge[:2]} for de, vers, charge in etat["relais"].vus[-12:]]
        return {"tour_effectue": etat["tour"], "agents": len(etat["agents"]), "points_relayes": len(vus),
                "octets": etat["relais"].octets, "duree_ms": etat["duree_ms"], "intentions_lisibles": 0,
                "compatibilites_existantes": len(etat["compat"]) if etat["tour"] else 0, "flux": flux,
                "moteur": psi.MOTEUR}

    @r.post("/attaque")
    def attaque():
        """Le Club curieux essaie TOUS les jetons possibles contre tout ce qu'il a relayé."""
        from .intentions import COMPLEMENTS
        roles = {x for pair in COMPLEMENTS.values() for x in pair}
        dico = {psi.hacher(f"{ro}|{s}|Valais").hex() for ro in roles for s in list(taxonomie.concepts) + ["*"]}
        vus = [j for (_, _, charge) in etat.get("relais", Relais()).vus for j in charge]
        return {"jetons_essayes": len(dico), "points_examines": len(vus), "reussites": sum(1 for j in vus if j in dico)}

    @r.get("/agent/{pid}")
    def agent(pid: str):
        if not etat:
            scenario()
        if pid not in etat["agents"]:
            raise HTTPException(404, "Pas d'agent pour ce membre dans la démonstration.")
        return vue_agent(pid)

    @r.post("/devoiler/{match}")
    def devoiler(match: str, c: Consentement):
        """Révélation progressive et SYMÉTRIQUE : rien n'est dévoilé tant que les deux n'ont pas consenti à l'étape."""
        m = etat.get("compat", {}).get(match)
        if not m or c.membre not in m["ids"]:
            raise HTTPException(403, "Seules les deux personnes concernées peuvent consentir.")
        etape = m["etape"]
        oui = etat["consentements"].setdefault((match, etape), set())
        oui.add(c.membre)
        if oui != set(m["ids"]):
            return {"etape": etape, "statut": "en attente de l'autre membre (rien n'est dévoilé)"}
        rev = etat["reveles"].setdefault(match, {})
        if etape == "secteur":
            for pid in m["ids"]:
                autre = m["ids"][1 - m["ids"].index(pid)]
                its = etat["agents"][autre].intentions
                rev[pid] = {"secteurs_de_l_autre": sorted({taxonomie.libelle(s) for i in its for s in i.secteurs}),
                            "intention_de_l_autre": LIBELLES[its[0].type]}
            m["etape"] = "identite"
            return {"etape": "secteur", "statut": "secteurs dévoilés aux deux, en même temps"}
        # identité : engagement des deux PUIS ouverture (personne ne se dévoile en premier)
        eng = {pid: engagement(pid) for pid in m["ids"]}
        for pid in m["ids"]:
            autre = m["ids"][1 - m["ids"].index(pid)]
            publie, nonce = eng[autre]
            assert ouvrir(publie, autre, nonce)
            p = etat["profils"][autre]
            rev[pid] = rev.get(pid, {}) | {"identite": f"{p.nom} · {p.entreprise} ({p.commune})", "engagement_verifie": True}
        m["etape"] = "introduit"
        return {"etape": "identite", "statut": "identités dévoilées simultanément ; introduction possible"}

    return r
