"""Vue du Club (animation) : ce que la communauté produit, et ce qui lui manque.

Tous les indicateurs sont CALCULÉS en direct à partir du magasin (aucun chiffre saisi à la main).
Agrégats uniquement : aucun nom d'auteur n'est affiché.

L'idée clé : un besoin sans réponse n'est pas un échec du produit, c'est une information pour le Club :
« 3 membres ont cherché un accompagnement ISO 27001 et aucun membre ne le propose » → une entreprise à inviter.
"""
from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from .matching import rechercher
from .models import Profil
from .parser_rules import analyser
from .store import Magasin
from .securite import signaux_profil
from .taxonomy import DATA_DIR, Taxonomie


def _date(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


def charger_historique(mag: Magasin, profils: list[Profil], tax: Taxonomie) -> int:
    """Rejoue un historique FICTIF à travers les vraies règles du magasin, puis le rétrodate."""
    brut = json.loads((DATA_DIR / "historique_demo.json").read_text(encoding="utf-8"))
    par_id = {p.id: p for p in profils}
    maintenant = datetime.now(timezone.utc)
    n = 0
    for h in brut["besoins"]:
        besoin = analyser(h["texte"], tax)
        b = mag.creer_besoin(h["auteur"], besoin, publier=True, anonyme=False)
        debut = maintenant - timedelta(days=h["jours"])
        if h.get("aidant"):
            aidant = par_id[h["aidant"]]
            preuve = rechercher(besoin, par_id[h["auteur"]], [par_id[h["auteur"]], aidant], tax)
            assert preuve.suggestions, f"historique incohérent : {h}"
            r = mag.creer_relation(b.id, aidant.id, h["auteur"], "Je peux vous aider (historique fictif).", True, True)
            mag.transition(r.id, "accepter", h["auteur"])
            mag.transition(r.id, "planifier", aidant.id, date_rencontre=(debut + timedelta(days=3)).date().isoformat())
            mag.transition(r.id, "confirmer_rencontre", aidant.id)
            mag.transition(r.id, "cloturer", h["auteur"], resultat=h["resultat"])
            mag.retrodater("relations", r.id, debut + timedelta(hours=h["delai_h"]))
            if h["statut"] == "resolu":
                mag.action_besoin(b.id, h["auteur"], "cloturer", resolu_par=r.id, note="Historique fictif")
            else:
                mag.action_besoin(b.id, h["auteur"], "cloturer", note="Historique fictif : pas concluant")
        elif h["statut"] == "retire":
            mag.action_besoin(b.id, h["auteur"], "cloturer", note="Historique fictif : aucune réponse")
        mag.retrodater("besoins", b.id, debut, maj_le=debut + timedelta(days=4 if h["statut"] != "publie" else 0))
        n += 1
    return n


def tableau(mag: Magasin, profils: list[Profil], tax: Taxonomie) -> dict:
    besoins = mag.besoins()
    relations = mag.relations()
    par_id = {p.id: p for p in profils}
    stat = Counter(b.statut for b in besoins)
    rel_par_besoin = defaultdict(list)
    for r in relations:
        rel_par_besoin[r.besoin_id].append(r)

    # Délai entre la publication d'un besoin et la première mise en relation.
    delais = []
    for b in besoins:
        rs = rel_par_besoin.get(b.id)
        if rs:
            premiere = min(_date(r.cree_le) for r in rs)
            delais.append((premiere - _date(b.cree_le)).total_seconds() / 3600)

    # Compétences à recruter : besoins pour lesquels AUCUN membre actuel ne correspond (recalculé maintenant).
    manques: dict[str, dict] = {}
    for b in besoins:
        auteur = par_id.get(b.auteur_id)
        if not auteur:
            continue
        res = rechercher(b.besoin, auteur, profils, tax)
        aboutie = any(r.etat in ("acceptee", "rencontre_planifiee", "rencontre_faite", "cloturee") for r in rel_par_besoin.get(b.id, []))
        if res.abstention and not aboutie:
            princ = next((c for c in b.besoin.criteres if c.type in ("expertise", "texte_libre")), None)
            if not princ:
                continue
            cle = princ.libelle if princ.type == "expertise" else f"« {princ.valeur} » (hors catalogue)"
            m = manques.setdefault(cle, {"competence": cle, "demandes": 0, "derniere": b.cree_le,
                                         "pistes": set(), "hors_catalogue": princ.type == "texte_libre"})
            m["demandes"] += 1
            m["derniere"] = max(m["derniere"], b.cree_le)
            m["pistes"] |= {s.profil.entreprise for s in res.pistes_elargies}
    a_recruter = sorted(({**m, "pistes": sorted(m["pistes"])} for m in manques.values()),
                        key=lambda m: (-m["demandes"], m["competence"]))

    # Offres présentes chez les membres mais jamais demandées : une ressource à faire connaître.
    demandes = {c.valeur for b in besoins for c in b.besoin.criteres if c.type == "expertise"}
    offertes = Counter(o.concept for p in profils if p.type == "membre_club" for o in p.offre if o.concept)
    dormantes = sorted(((tax.libelle(c), n) for c, n in offertes.items()
                        if not any(tax.meme_famille(c, d) for d in demandes)), key=lambda x: (-x[1], x[0]))

    resultats = Counter(r.resultat for r in relations if r.resultat)
    clos = stat["resolu"] + stat["retire"]
    return {
        "periode": {"debut": min((b.cree_le for b in besoins), default=None), "fin": max((b.maj_le for b in besoins), default=None)},
        "besoins": {"total": len(besoins), "ouverts": stat["publie"] + stat["en_cours"] + stat["brouillon"],
                    "resolus": stat["resolu"], "clos_sans_suite": stat["retire"],
                    "avec_mise_en_relation": sum(1 for b in besoins if rel_par_besoin.get(b.id))},
        "taux_resolution": {"resolus": stat["resolu"], "clos": clos},
        "relations": {"total": len(relations),
                      "acceptees": sum(1 for r in relations if r.etat in ("acceptee", "rencontre_planifiee", "rencontre_faite", "cloturee")),
                      "declinees_ou_annulees": sum(1 for r in relations if r.etat in ("declinee", "annulee", "retiree")),
                      "resultats": {k: resultats[k] for k in ("utile", "affaire_en_cours", "pas_pertinent")}},
        "delai_premiere_relation_h": {"mediane": round(statistics.median(delais), 1) if delais else None, "n": len(delais)},
        "a_recruter": a_recruter,
        "offres_dormantes": [{"competence": c, "membres": n} for c, n in dormantes[:6]],
        "profils_a_relire": sum(1 for p in profils if signaux_profil(p)),
        "membres": {"total": sum(1 for p in profils if p.type == "membre_club"),
                    "acceptent_introductions": sum(1 for p in profils if p.type == "membre_club" and p.accepte_introductions)},
    }
