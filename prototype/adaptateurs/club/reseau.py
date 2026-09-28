"""Réseau du Club : UNE ligne de temps des relations, un état de relation dérivé, des chemins chauds, une boîte réseau.

Une seule source de vérité par fait :
- le MAGASIN possède le workflow d'introduction (demande → acceptation → rencontre → résultat) et ses permissions ;
- la MÉMOIRE possède les soirées, les suivis, les relances et les recommandations de présentation ;
- ce module PROJETTE le magasin dans la mémoire (événements idempotents, horodatés par le magasin) : le graphe temporel
  voit tout, et rien n'est recopié à la main.

Distinctions tenues : recommandation ≠ introduction ≠ relation ≠ opportunité ≠ résultat. Les états sont des FAITS
opérationnels (qui a fait quoi, quand), jamais une interprétation psychologique.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import networkx as nx

from app.models import Profil
from plateforme.affirmations import Statut
from plateforme.memoire import Evt, Memoire, force, graphe
from plateforme.optimisation import cle

from .cycle import DELAI_RELANCE_JOURS

JOURS_AVANT_STALE = 90          # hypothèse de produit : sans interaction depuis 90 jours, la relation est « à raviver »
PROFIL_ANCIEN_JOURS = 365

# action du magasin → événement de la mémoire
PROJECTION = {
    "proposer": ("INTRO_DEMANDEE", Statut.OBSERVE),
    "accepter": ("INTRO_ACCEPTEE", Statut.OBSERVE),
    "decliner": ("INTRO_DECLINEE", Statut.OBSERVE),
    "retirer": ("INTRO_RETIREE", Statut.OBSERVE),
    "annuler": ("INTRO_ANNULEE", Statut.OBSERVE),
    "annulation_automatique": ("INTRO_ANNULEE", Statut.OBSERVE),
    "confirmer_rencontre": ("RENCONTRE", Statut.DECLARE),   # un membre a déclaré la rencontre
    "cloturer": ("RESULTAT", Statut.DECLARE),
}


def _jour(iso: str) -> date:
    return datetime.fromisoformat(iso).date()


def projeter(m: Memoire, relations_magasin: list, besoins_magasin: Optional[list] = None) -> int:
    """Magasin → mémoire. Idempotent (même contenu = même événement). Retourne le nombre d'événements projetés.
    Besoins : seulement ceux qui ont été PUBLICS et NON anonymes (une relance nommerait l'auteur) ; jamais un brouillon.
    Un besoin qui n'est plus public (clos, dépublié) reçoit un BESOIN_CLOS et cesse de servir de raison."""
    from app.store import STATUTS_PUBLICS
    n = 0
    for b in besoins_magasin or []:
        if b.anonyme:
            continue
        pub = next((e for e in b.historique if e.action in ("creer_et_publier", "publier")), None)
        if pub is None:
            continue
        m.ajouter(Evt(type="BESOIN_PUBLIE", le=_jour(pub.horodatage), acteurs=[b.auteur_id], statut=Statut.OBSERVE,
                      donnees={"besoin_id": b.id, "texte": b.besoin.texte, "besoin": b.besoin.model_dump(), "source": "bourse"}))
        n += 1
        if b.statut not in STATUTS_PUBLICS:
            m.ajouter(Evt(type="BESOIN_CLOS", le=_jour(b.maj_le), acteurs=[b.auteur_id], statut=Statut.OBSERVE,
                          donnees={"besoin_id": b.id, "statut": b.statut}))
            n += 1
    for r in relations_magasin:
        paire = [r.auteur_id, r.aidant_id]
        for ev in r.historique:
            if ev.action not in PROJECTION:
                continue
            typ, st = PROJECTION[ev.action]
            donnees = {"relation_id": r.id, "besoin_id": r.besoin_id, "par": ev.acteur, "source": "introduction"}
            if typ == "RESULTAT":
                donnees["resultat"] = r.resultat
            m.ajouter(Evt(type=typ, le=_jour(ev.horodatage), acteurs=paire, donnees=donnees, statut=st))
            n += 1
    return n


# ------------------------------------------------------------------ état d'une relation (dérivé, factuel)
ORDRE = ["RECOMMANDEE", "INTRO_DEMANDEE", "INTRO_ACCEPTEE", "RENCONTREE", "SUIVI", "OPPORTUNITE", "RESULTAT_UTILE"]
LIBELLES = {
    "AUCUNE": "aucune interaction enregistrée", "RECOMMANDEE": "présentation recommandée (pas encore demandée)",
    "INTRO_DEMANDEE": "introduction demandée", "INTRO_ACCEPTEE": "introduction acceptée, coordonnées partagées",
    "RENCONTREE": "rencontre enregistrée", "SUIVI_EN_ATTENTE": "rencontrée, aucun suivi depuis 10 jours",
    "SUIVI": "suivi enregistré", "OPPORTUNITE": "affaire en cours déclarée", "RESULTAT_UTILE": "déclarée utile",
    "DECLINEE": "introduction déclinée", "SANS_SUITE": "déclarée sans suite", "PAS_MAINTENANT": "relance reportée par le membre",
    "A_RAVIVER": "aucune interaction depuis plus de 90 jours",
}


def etat_relation(m: Memoire, a: str, b: str, maintenant: date) -> dict:
    k = cle(a, b)
    evs = [e for e in m.evenements(jusqu_au=maintenant) if len(e.acteurs) >= 2 and cle(*e.acteurs[:2]) == k]
    atteint, derniere, faits = -1, None, []
    terminal = None
    for e in evs:
        etape = {"OPPORTUNITE_OUVERTE": "RECOMMANDEE", "INTRO_DEMANDEE": "INTRO_DEMANDEE", "INTRO_ACCEPTEE": "INTRO_ACCEPTEE",
                 "RENCONTRE": "RENCONTREE", "RENCONTRE_CONFIRMEE": "RENCONTREE", "SUIVI": "SUIVI"}.get(e.type)
        if e.type == "RESULTAT":
            etape = {"affaire_en_cours": "OPPORTUNITE", "utile": "RESULTAT_UTILE"}.get(e.donnees.get("resultat"))
            if e.donnees.get("resultat") == "pas_pertinent":
                terminal = "SANS_SUITE"
        if e.type == "INTRO_DECLINEE":
            terminal = "DECLINEE"
        if e.type == "RELANCE_REFUSEE":
            terminal = terminal or "PAS_MAINTENANT"
        if etape:
            atteint = max(atteint, ORDRE.index(etape))
        if e.type in ("RENCONTRE", "SUIVI", "INTRO_ACCEPTEE", "RESULTAT", "RENCONTRE_CONFIRMEE"):
            derniere = e.le if derniere is None else max(derniere, e.le)
        faits.append({"le": e.le.isoformat(), "type": e.type, "statut": e.statut.value,
                      **({"evenement": e.donnees["evenement"]} if "evenement" in e.donnees else {}),
                      **({"resultat": e.donnees["resultat"]} if "resultat" in e.donnees else {})})
    etat = ORDRE[atteint] if atteint >= 0 else "AUCUNE"
    if terminal and terminal != "PAS_MAINTENANT":
        etat = terminal
    elif derniere and (maintenant - derniere).days > JOURS_AVANT_STALE:
        etat = "A_RAVIVER"
    elif etat == "RENCONTREE" and derniere and (maintenant - derniere).days >= DELAI_RELANCE_JOURS:
        etat = "PAS_MAINTENANT" if terminal == "PAS_MAINTENANT" else "SUIVI_EN_ATTENTE"
    return {"etat": etat, "libelle": LIBELLES[etat], "derniere_interaction": derniere.isoformat() if derniere else None,
            "force": force(derniere, maintenant) if derniere else None, "faits": faits}


def memoire_relation(m: Memoire, a: str, b: str, maintenant: date) -> dict:
    """Où, quand, pourquoi, et ensuite ? — répond aux questions de mémoire relationnelle à partir des faits."""
    e = etat_relation(m, a, b, maintenant)
    rencontres = [f for f in e["faits"] if f["type"] == "RENCONTRE"]
    return {"ou": rencontres[0].get("evenement", "introduction") if rencontres else None,
            "quand": rencontres[0]["le"] if rencontres else None,
            "ensuite": [f["type"] for f in e["faits"]], "etat": e["etat"], "libelle": e["libelle"],
            "derniere_interaction": e["derniere_interaction"]}


# ------------------------------------------------------------------ chemin chaud et dimensions réseau d'un candidat
def graphe_de_confiance(m: Memoire, maintenant: date) -> nx.Graph:
    """Liens sur lesquels on peut s'appuyer pour une présentation : rencontres et suivis (pas les simples demandes)."""
    g = graphe(m, maintenant)
    for e in m.evenements("INTRO_ACCEPTEE", jusqu_au=maintenant):   # une introduction acceptée est un lien, même sans rencontre
        a, b = e.acteurs[:2]
        if not g.has_edge(a, b):
            g.add_edge(a, b, premiere=e.le, derniere=e.le, nombre=1, types={"INTRO_ACCEPTEE"}, statut=e.statut)
    return g


def chemin_chaud(g: nx.Graph, x: str, c: str, par_id: dict[str, Profil]) -> dict:
    if g.has_edge(x, c):
        return {"distance": 1, "type": "DIRECT", "message": "vous êtes déjà en relation"}
    if x in g and c in g and nx.has_path(g, x, c):
        chemins = sorted(nx.all_shortest_paths(g, x, c))
        if len(chemins[0]) == 3:
            vias = [p[1] for p in chemins if par_id.get(p[1]) and par_id[p[1]].accepte_introductions]
            if vias:  # l'intermédiaire n'est PAS nommé : le lien via–c lui appartient (il sera sollicité d'abord)
                return {"distance": 2, "type": "PRESENTATION", "via": None, "_via_interne": vias[0],
                        "message": "un de vos contacts connaît aussi cette personne : il pourra être sollicité pour vous présenter"}
        return {"distance": len(chemins[0]) - 1, "type": "LOINTAIN", "message": f"relié·e à {len(chemins[0]) - 1} poignées de main"}
    if x in g and c in g:
        tx, tc = len(nx.node_connected_component(g, x)), len(nx.node_connected_component(g, c))
        return {"distance": None, "type": "PONT", "message": f"aucun chemin : cette introduction relierait deux groupes ({tx} et {tc} membres)"}
    return {"distance": None, "type": "NOUVEAU", "message": "aucune relation enregistrée pour l'un de vous deux : premier lien dans le réseau"}


def reciprocite_prouvee(x: Profil, c: Profil, tax, besoins_publies: list) -> Optional[dict]:
    """x peut-il aider c ? Le MÊME moteur, en sens inverse : un besoin public ou une recherche de c, couvert par une
    offre de x citée mot pour mot. (x consulte : son propre refus d'être recommandé ne s'applique pas ici.)"""
    from app.soiree import _aide, _recherches
    x_ici = x.model_copy(update={"accepte_introductions": True})
    aide = _aide(c, x_ici, _recherches(c, besoins_publies, tax), tax)
    if not aide:
        return None
    return {"son_besoin": aide["besoin"], "votre_offre": aide["preuve"], "niveau": aide["niveau"],
            "nature": aide["nature_preuve"]}


def dimensions(m: Memoire, x: Profil, suggestion: dict, par_id: dict[str, Profil], maintenant: date,
               besoin_le: Optional[date] = None, g: Optional[nx.Graph] = None, tax=None,
               besoins_publies: Optional[list] = None) -> dict:
    """Quatre dimensions EXPLIQUÉES (jamais un score de valeur d'une personne) : pertinence, réciprocité, réseau, contexte,
    et ce qui est CONNU / DÉDUIT / INCONNU."""
    g = g if g is not None else graphe_de_confiance(m, maintenant)
    c = par_id[suggestion["profil"]["id"]]
    preuves = suggestion["preuves"]
    connu = [f"{p['critere']} : « {p['extrait']} » ({'déclaré' if p['nature'] == 'declare' else 'déduit'} dans son profil, {p['champ']})"
             for p in preuves if p["nature"] == "declare"]
    deduit = [f"{p['critere']} : « {p['extrait']} » (déduit d'un texte libre)" for p in preuves if p["nature"] != "declare"]
    recip = reciprocite_prouvee(x, c, tax, besoins_publies or []) if tax is not None else None
    chemin = chemin_chaud(g, x.id, c.id, par_id)
    etat = etat_relation(m, x.id, c.id, maintenant)
    deja_demandes = sum(1 for e in m.evenements("INTRO_DEMANDEE", jusqu_au=maintenant) if set(e.acteurs[:2]) == {x.id, c.id})
    inconnu = []
    if etat["etat"] == "AUCUNE":
        inconnu.append("aucune interaction enregistrée entre vous")
    if not recip:
        inconnu.append(f"ce que vous pourriez apporter à {c.nom.split(' ')[0]} : aucune de ses recherches ne correspond à vos offres")
    if not (set(x.creneaux) & set(c.creneaux)):
        inconnu.append("disponibilités communes : non établies")
    if c.maj:
        try:
            age = (maintenant - date.fromisoformat(c.maj[:10])).days
            if age > PROFIL_ANCIEN_JOURS:
                inconnu.append(f"profil non mis à jour depuis {age} jours : l'offre peut avoir changé")
        except ValueError:
            pass
    else:
        inconnu.append("date de mise à jour du profil inconnue")
    pourquoi_maintenant = []
    if besoin_le:
        pourquoi_maintenant.append(f"votre besoin est publié depuis le {besoin_le.isoformat()}")
    if c.disponible:
        pourquoi_maintenant.append("se déclare disponible")
    if chemin["type"] == "PRESENTATION":
        pourquoi_maintenant.append("un contact commun peut faciliter la prise de contact (il sera sollicité d'abord)")
    return {
        "pertinence": {"niveau": suggestion["niveau"], "preuves": len(preuves)},
        "reciprocite": {"etablie": bool(recip), **(recip or {})},
        "reseau": {k: v for k, v in chemin.items() if not k.startswith("_")} | {"deja_demandee": deja_demandes},
        "contexte": {"etat_relation": etat["etat"], "libelle": etat["libelle"]},
        "pourquoi_cette_personne": [p["extrait"] for p in preuves[:2]],
        "pourquoi_maintenant": pourquoi_maintenant,
        "comment_nous_savons": {"connu": connu, "deduit": deduit},
        "inconnu": inconnu,
        "confidentialite": "aucune coordonnée n'est montrée : elles ne sont partagées qu'après acceptation de l'introduction par les deux",
    }


# ------------------------------------------------------------------ boîte réseau (prochains mouvements utiles, pas un fil)
def boite(m: Memoire, moi: Profil, profils: list[Profil], relations_magasin: list, relances: dict, maintenant: date) -> dict:
    par_id = {p.id: p for p in profils}
    a_repondre = [{"relation_id": r.id, "de": par_id[r.initiateur_id()].nom if r.initiateur_id() in par_id else "un membre",
                   "depuis": r.cree_le[:10]} for r in relations_magasin
                  if r.etat == "proposee" and r.destinataire_id() == moi.id]
    en_attente = [{"relation_id": r.id, "vers": par_id[r.destinataire_id()].nom if r.destinataire_id() in par_id else "un membre",
                   "depuis": r.cree_le[:10]} for r in relations_magasin if r.etat == "proposee" and r.initiateur_id() == moi.id]
    rencontres_a_confirmer = [{"relation_id": r.id, "avec": par_id[(r.aidant_id if r.auteur_id == moi.id else r.auteur_id)].nom}
                              for r in relations_magasin if r.etat in ("acceptee", "rencontre_planifiee")
                              and moi.id in (r.auteur_id, r.aidant_id)]
    suivis = [{"type": r["type"], "avec": [n for n in p["noms"] if n != moi.nom][0], "raison": r["message"], "relance_id": r["id"]}
              for p in relances.get("propositions", []) if moi.id in p["paire"] for r in p["raisons"] if r["pour"] == moi.id]
    g = graphe(m, maintenant)
    a_raviver = []
    if moi.id in g:
        for v in sorted(g.neighbors(moi.id)):
            if etat_relation(m, moi.id, v, maintenant)["etat"] == "A_RAVIVER" and v in par_id:
                a_raviver.append({"avec": par_id[v].nom, "derniere": g[moi.id][v]["derniere"].isoformat()})
    presentations = [{"vers": par_id[e.acteurs[1] if e.acteurs[0] == moi.id else e.acteurs[0]].nom, "via": par_id[e.donnees["via"]].nom}
                     for e in m.evenements("OPPORTUNITE_OUVERTE", jusqu_au=maintenant) if moi.id in e.acteurs
                     and all(a in par_id for a in e.acteurs) and e.donnees.get("via") in par_id]
    sections = {"introductions_a_repondre": a_repondre, "mes_demandes_en_attente": en_attente,
                "rencontres_a_confirmer": rencontres_a_confirmer, "suivis_proposes": suivis,
                "presentations_recommandees": presentations, "relations_a_raviver": a_raviver}
    return {"membre": moi.id, "le": maintenant.isoformat(), "total": sum(len(v) for v in sections.values()), **sections,
            "principe": "seulement des actions possibles maintenant, chacune avec sa raison ; aucun fil d'actualité"}


# ------------------------------------------------------------------ simulation avant / après (aucune écriture)
def simuler(g: nx.Graph, ajouts: list[tuple[str, str]], maintenant: date, focus: Optional[list[str]] = None) -> dict:
    """SIMULATION : que devient le réseau si ces liens se créent ? Indicateurs factuels avant/après, calculés sur une
    COPIE du graphe (rien n'est écrit). Ce n'est pas une prédiction du comportement des membres."""
    from plateforme.memoire import indicateurs
    apres = g.copy()
    ponts = []
    for a, b in ajouts:
        relie = not (a in g and b in g and nx.has_path(g, a, b))
        if relie:
            ponts.append([a, b])
        apres.add_edge(a, b, derniere=maintenant, premiere=maintenant, nombre=1, types={"SIMULATION"}, statut=Statut.SIMULE)
    portee = lambda gr, n: len(nx.single_source_shortest_path_length(gr, n, cutoff=2)) - 1 if n in gr else 0  # noqa: E731
    return {"nature": "SIMULATION", "ajouts": [list(p) for p in ajouts], "avant": indicateurs(g, maintenant),
            "apres": indicateurs(apres, maintenant), "nouveaux_ponts": ponts,
            "portee_a_2_sauts": {n: {"avant": portee(g, n), "apres": portee(apres, n)} for n in (focus or [])},
            "hypothese": "chaque lien simulé est supposé accepté par les deux membres ; aucun comportement n'est prédit"}
