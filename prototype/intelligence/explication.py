"""« POURQUOI cette possibilité existe-t-elle ? » — l'explication structurée d'une opportunité.

Une opportunité n'est pas un score. C'est une INFÉRENCE du système, fondée sur des éléments dont chacun porte son statut :
- DÉCLARÉ   : un membre l'a écrit (profil, offre, besoin) — cité mot pour mot ;
- OBSERVÉ   : le journal du Club l'a enregistré (une rencontre, une inscription à un événement) ;
- CONFIRMÉ  : une contribution passée, jugée utile par la personne aidée ET confirmée par la personne qui a contribué
              (une confirmation humaine, pas une vérité objective : c'est dit) ;
- INFÉRÉ    : ce que le système en conclut (l'opportunité elle-même) ;
- INCONNU   : ce que personne n'a dit (la disponibilité, tant qu'aucune offre n'est publiée).

Fonction PURE : elle lit l'opportunité (ses signaux sourcés), les profils pseudonymisés, les disponibilités DÉCLARÉES
et la mémoire DÉJÀ filtrée par les droits de réutilisation. Elle n'écrit rien, ne contacte personne, ne décide rien.
Les noms y sont des pseudonymes (MEMBRE-xxx) : une vue les rend pour UN spectateur, selon la politique.
"""
from __future__ import annotations

from typing import Optional

from app.taxonomy import Taxonomie

from .modele import Opportunite, Reseau

NIVEAUX = ["faible", "moyenne", "elevee"]
POSITIFS = {"positif", "mitige"}


def _item(texte: str, statut: str, qui: Optional[str] = None, le: Optional[str] = None, source: Optional[str] = None) -> dict:
    return {"texte": texte, "statut": statut, "qui": qui, "le": le, "source": source}


def contributeurs(o: Opportunite) -> list[str]:
    return [r.membre for r in o.roles if r.membre != o.beneficiaire and r.role not in ("participant", "demandeur bloqué")]


def souvenirs_pertinents(souvenirs: list[dict], membre: str, concepts: set[str]) -> list[dict]:
    """Mémoire où CE membre a contribué sur au moins une de CES capacités (la mémoire est déjà filtrée par les droits)."""
    return [s for s in souvenirs if membre in s["contributeurs"] and concepts & set(s["concepts"])]


def expliquer(o: Opportunite, r: Reseau, tax: Taxonomie, disponibilites: dict[str, list[dict]],
              souvenirs: list[dict]) -> dict:
    par_id = r.par_id()
    nom = lambda pid: par_id[pid].nom if pid in par_id else "un ancien membre"  # noqa: E731
    benef = o.beneficiaire
    contrib = contributeurs(o)
    besoin, capacite, contexte, relation, preuves = [], [], [], [], []
    moment = None
    for s in o.signaux:
        if s.source in ("besoin", "recherche") and s.membre == benef:
            besoin.append(_item(s.extrait, "DÉCLARÉ", s.membre, s.le, "demande publiée" if s.source == "besoin" else "profil : je cherche"))
        elif s.source == "offre":
            capacite.append(_item(s.extrait, "DÉCLARÉ", s.membre, s.le, "profil : je peux aider"))
        elif s.source == "recherche":
            contexte.append(_item(f"{nom(s.membre or '')} cherche : « {s.extrait} » — ce que {nom(benef or '')} produit"
                                  if benef else f"{nom(s.membre or '')} cherche : « {s.extrait} »", "DÉCLARÉ", s.membre, s.le, "profil"))
        elif s.source == "relation":
            relation.append(_item(f"{nom(benef or '')} et {nom(s.membre or '')} : {s.extrait}", "OBSERVÉ", s.membre, s.le, "journal du Club"))
        elif s.source == "evenement":
            moment = _item(s.extrait, "OBSERVÉ", None, s.le, "agenda du Club")
    if benef and contrib and not relation:
        relation.append(_item(f"Aucune rencontre connue entre {nom(benef)} et " + ", ".join(nom(c) for c in contrib)
                              + " : ce serait une introduction, pas une suite.", "OBSERVÉ", None, None, "journal du Club"))
    preuves = besoin + capacite + contexte + relation + ([moment] if moment else [])

    consentement, inconnues, risques = [], [], list(o.risques)
    if benef:
        consentement.append(_item(f"Rien n'est proposé à personne sans l'accord de {nom(benef)}.", "INFÉRÉ", benef))
    for c in contrib:
        p = par_id.get(c)
        if p is not None and p.accepte_introductions and p.disponible:     # lu dans le profil, jamais supposé
            consentement.append(_item(f"{nom(c)} a déclaré accepter les sollicitations : refus possible sans justification, "
                                      "jamais montré à personne.", "DÉCLARÉ", c))
        else:
            consentement.append(_item(f"{nom(c)} n'accepte pas les sollicitations actuellement : rien ne peut lui être proposé.",
                                      "DÉCLARÉ", c))
            risques.append(f"{nom(c)} n'accepte pas les sollicitations : l'opportunité ne peut pas être activée telle quelle")
        dispo = disponibilites.get(c, [])
        if dispo:
            d = dispo[0]
            preuves.append(_item(f"{nom(c)} a publié une offre : « {d['quoi']} »" + (f", {d['duree_max_min']} min au plus" if d.get("duree_max_min") else "")
                                 + f", jusqu'au {d['au']}.", "DÉCLARÉ", c, None, "offre volontaire"))
        else:
            inconnues.append(_item(f"Disponibilité actuelle de {nom(c)} : inconnue (aucune offre publiée) — elle ne sera connue "
                                   "que s'il ou elle accepte une proposition.", "INCONNU", c))
    inconnues += [_item(f"Capacité absente du Club : {m}", "INCONNU") for m in o.manque]

    niveau = NIVEAUX.index(o.confiance)
    effet = None
    # le sujet et la mémoire portent sur ce que les CONTRIBUTEURS apportent (pas sur ce que le bénéficiaire produit)
    concepts = {r_.concept for r_ in o.roles if r_.membre in contrib and r_.concept and not r_.role.startswith("partenaire")} \
        or set(o.capacites)
    for c in contrib:
        mem = souvenirs_pertinents(souvenirs, c, concepts)
        confirmes = [m for m in mem if m["statut"] == "confirmee" and m["qualification"] in POSITIFS]
        contestes = [m for m in mem if m["statut"] == "contestee"]
        negatifs = [m for m in mem if m["qualification"] not in POSITIFS]
        for m in confirmes:
            preuves.append(_item(f"Contribution de {nom(c)} dans le Club : « {m['question']} » — jugée « {m['qualification']} » par la "
                                 f"personne aidée et confirmée par {nom(c)} (le {m['le']} ; portée : {m['limites']}). Une confirmation "
                                 "humaine, pas une garantie.", "CONFIRMÉ", c, m["le"], "mémoire du Club"))
        for m in contestes:
            risques.append(f"une contribution passée de {nom(c)} sur ce sujet est CONTESTÉE ({m['le']})")
        for m in negatifs:
            risques.append(f"un essai passé avec {nom(c)} sur ce sujet a été jugé « {m['qualification']} » ({m['le']} ; portée : {m['limites']})")
        if confirmes and not contestes and not negatifs:
            niveau, effet = min(niveau + 1, 2), f"relevée : contribution confirmée de {nom(c)} dans le Club"
        elif negatifs or contestes:
            niveau, effet = max(niveau - 1, 0), f"abaissée : un essai passé avec {nom(c)} n'a pas aidé ou est contesté"
        elif not mem:
            risques.append(f"aucune contribution de {nom(c)} n'a encore été confirmée dans le Club sur ce sujet")
    sujet = " + ".join(tax.libelle(k) for k in sorted(concepts)) or o.titre
    return {
        "resume": _item(f"Il existe peut-être une coopération : {sujet}" + (f" pour {nom(benef)}" if benef else "")
                        + (" avec " + ", ".join(nom(c) for c in contrib) if contrib else "") + ".", "INFÉRÉ"),
        "besoin": besoin, "capacite": capacite, "contexte": contexte, "relation": relation, "moment": moment,
        "consentement": consentement, "preuves": preuves, "inconnues": inconnues, "risques": risques,
        "confiance": {"niveau": NIVEAUX[niveau], "detection": o.confiance, "raisons": list(o.confiance_raisons), "effet_memoire": effet},
        "contributeurs": contrib, "beneficiaire": benef,
        "question": "Voulez-vous proposer un essai ?" if benef and contrib else None,
    }
