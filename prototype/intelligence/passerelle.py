"""PASSERELLE : une opportunité détectée → un BROUILLON d'essai, quand (et seulement quand) le bénéficiaire le demande.

C'est le seul module qui connaît à la fois la détection (Network Intelligence) et le banc d'essai (Activation Engine).
Il ne décide rien : il prépare un brouillon que le bénéficiaire lit, corrige, puis publie — ou abandonne.
- les personnes nommées par l'opportunité sont invitées (geste SUR INVITATION) : leur disponibilité reste inconnue
  jusqu'à ce qu'elles acceptent ; au plus 4 (un essai reste petit) — combien restent hors de l'essai est gardé ;
- l'échéance suit le « pourquoi maintenant » (un événement proche), sinon 10 jours ;
- le critère d'observation reste VIDE : une suggestion est jointe, le bénéficiaire l'adopte ou écrit le sien ;
- l'origine (opportunité, capacités) est gardée pour la mémoire.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from app.taxonomy import Taxonomie

from .essai import MAX_GESTES, Etape, Protocole
from .explication import contributeurs
from .modele import Opportunite, Reseau

DUREE_ECHANGE_MIN = 60           # un rendez-vous d'échange ; le bénéficiaire l'ajuste avant de publier
ECHEANCE_JOURS = 10
NATURE = {"SUIVI": "une suite possible à une rencontre", "LATENTE": "un intérêt déclaré qui rencontre une capacité déclarée",
          "COMPLEMENTARITE": "un besoin publié et une capacité déclarée", "COMPOSITION": "plusieurs capacités pour un besoin publié",
          "CONVERGENCE": "un besoin partagé par plusieurs membres"}
# le critère n'est JAMAIS écrit à la place du bénéficiaire : une suggestion, qu'il adopte ou remplace explicitement
CRITERE_SUGGERE = "À la fin de l'échange, avez-vous au moins une piste concrète à relancer ?"


def brouillon(o: Opportunite, r: Reseau, tax: Taxonomie, jour: date, duree_min: int = DUREE_ECHANGE_MIN) -> Protocole:
    if not o.beneficiaire:
        raise ValueError("une opportunité sans bénéficiaire ne se transforme pas en essai")
    besoin = next((s.extrait for s in o.signaux if s.membre == o.beneficiaire and s.source in ("besoin", "recherche")), o.titre)
    ev = next((e for e in r.evenements if e.id == o.evenement), None)
    echeance = ev.le if ev and ev.le > jour else jour + timedelta(days=ECHEANCE_JOURS)
    etapes, concepts = [], []
    invites = contributeurs(o)
    for i, pid in enumerate(invites[:MAX_GESTES], start=1):                # un essai reste petit ; le reste est DIT
        role = next(x for x in o.roles if x.membre == pid)
        capa = tax.libelle(role.concept) if role.concept else "votre expérience"
        demande = role.concept if role.concept and not role.role.startswith("partenaire") else None
        if demande:
            concepts.append(demande)
        etapes.append(Etape(id=f"e{i}", nature="competence", geste=f"Échange de {duree_min} min : {capa}"[:200], duree_min=duree_min,
                            contributeur=pid, invitation=True, concept=demande))
    # le « pourquoi » du protocole est un texte HUMAIN, lu par chaque personne invitée : aucune personne n'y est nommée
    # (le raisonnement de la détection, lui, reste dans la découverte, rendu pour son seul spectateur)
    sujet = " + ".join(tax.libelle(c) for c in sorted(set(concepts))) or "votre besoin"
    pourquoi = f"Découvert par Club Pulse ({NATURE.get(o.type, 'une possibilité')}) : {sujet}" + (f", avant « {ev.nom} »" if ev else "") + "."
    return Protocole(question=besoin[:300], objet="", critere="", pourquoi=pourquoi[:300],
                     echeance=echeance, etapes=etapes,
                     origine={"opportunite": o.id, "type": o.type, "concepts": sorted(set(concepts)), "beneficiaire": o.beneficiaire,
                              "evenement": o.evenement, "critere_suggere": CRITERE_SUGGERE,
                              "non_invites": len(invites[MAX_GESTES:])})


def essai_existant(essais: list[tuple[str, Optional[dict], str]], oid: str) -> Optional[str]:
    """Un essai encore vivant issu de la même opportunité (évite de solliciter deux fois pour la même chose)."""
    return next((eid for eid, origine, etat in essais if (origine or {}).get("opportunite") == oid
                 and etat not in ("ANNULE", "EXPIRE", "OBSERVEE")), None)
