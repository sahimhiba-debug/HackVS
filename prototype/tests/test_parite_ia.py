"""PARITÉ IA ON / OFF, NON VACUEUSE (critère de sortie de la Phase 3). Le même parcours du registre — réponse à une
demande (EXTRACT), récit de l'Établi (NARRATE), retrait, recomposition, nouvelle réponse, nouveau récit — joué IA
ALLUMÉE et IA ÉTEINTE aboutit au MÊME état métier. Et la parité doit être gagnée, pas offerte : au moins une sortie
du modèle a été ACCEPTÉE (MODEL_CALLED) et a servi ; si toutes les sorties ON partent en forme déterministe, le test
ÉCHOUE (« parité vacueuse »). Modèle SCRIPTÉ (aucun réseau en CI), données FICTIVES."""
import re

import pytest

from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.demo import Demo
from intelligence.ia import Intelligence
from tests.modele_scripte import ModeleScripte

TAX = charger_taxonomie()
A = "delegation_acheteurs"
REPONSES = {md.PAULINE: "Mon minibus a 14 places, libre vendredi après-midi.", md.MARKUS: "Notre bus a 20 places, sans souci vendredi."}
ECRIT_DANS_LE_FORMULAIRE = {md.PAULINE: {"places": 14}, md.MARKUS: {"places": 20}}   # IA éteinte : le membre tape ses valeurs


def _modele_fidele():
    def extraire(message):
        texte = message.split('"texte": "', 1)[1]
        return {"attributs": {"places": int(re.search(r"\d+", texte).group())}}
    return ModeleScripte(extraire_piece=extraire,
                         raconter_capacite={"phrases": [{"texte": "Voici où en est cette capacité.", "faits": ["F1"]}]})


def jouer(club) -> dict:
    """Le parcours ; renvoie ce que le modèle a apporté (valeurs proposées ET retenues par le membre)."""
    apports = {}
    for pid in (md.PAULINE, md.MARKUS):
        ask = next(a for _, a in club.asks_pour(pid) if a.startswith(A))
        proposition, ext, _ = club.proposer_reponse(pid, ask, REPONSES[pid])
        attributs = proposition["attributs"] or ECRIT_DANS_LE_FORMULAIRE[pid]      # le membre confirme, ou remplit
        if ext.issue == "MODEL_CALLED":
            apports[pid] = attributs
        club.repondre_ask(pid, ask, True, attributs, REPONSES[pid])
        club.raconter_capacite(A)
        if pid == md.PAULINE:
            club.retirer_consentement(pid, A)
    return apports


def etat_metier(club) -> dict:
    """L'état métier, sans les faits de PILOTAGE de l'IA (appels, interrupteur, propositions) ni la PROVENANCE d'une
    réponse (qui DOIT différer : vérifiée à part, `_provenances`) ; ce qui dépend de la position dans le
    journal (identifiants d'offres, suffixe de position d'une référence de reçu) est remplacé par un rang ou retiré —
    tout le reste doit être IDENTIQUE (l'empreinte de la référence comprise)."""
    rangs: dict[str, str] = {}

    def canon(x):
        if isinstance(x, dict):
            return {k: re.sub(r"-\d+$", "", v) if k == "reference" else canon(v) for k, v in x.items()
                    if k not in ("n", "provenance", "trace")}
        if isinstance(x, list):
            return [canon(v) for v in x]
        if isinstance(x, str):
            return re.sub(r"of-[0-9a-f]{8}", lambda m: rangs.setdefault(m.group(), f"offre#{len(rangs) + 1}"), x)
        return x
    evs = [(e.type, e.le.isoformat(), e.acteurs, e.statut.value, canon(e.donnees)) for e in club.journal.evenements()
           if e.type not in ("APPEL_IA", "IA_INTERRUPTEUR", "PROPOSITION_IA")]
    return {"journal": evs, "capacites": canon([i.model_dump(mode="json") for i in club.capacites.projeter()]),
            "recus": {pid: canon(club.capacites.recus(pid)) for pid in (md.PAULINE, md.MARKUS)}, "jour": club.jour.isoformat()}


def verifier_parite(on, off, apports) -> None:
    issues = [a.issue for a in on.ia.appels]
    if "MODEL_CALLED" not in issues or not apports:
        raise AssertionError(f"parité vacueuse : aucune sortie du modèle acceptée ni retenue (issues ON : {issues})")
    assert all(a.issue == "FALLBACK_FORM" for a in off.ia.appels) and off.ia.appels  # OFF : vraiment sans modèle
    assert etat_metier(on) == etat_metier(off)
    # la seule différence permise, et EXIGÉE : la provenance dit la vérité (F31)
    assert _provenances(on) == {pid: "AI_PROPOSED_CONFIRMED" for pid in apports}
    assert set(_provenances(off).values()) == {"SELF_DECLARED"}


def _provenances(club) -> dict:
    return {e.acteurs[0]: e.donnees["provenance"] for e in club.journal.evenements("ASK_REPONSE") if e.donnees["oui"]}


def test_parite_on_off_non_vacueuse():
    on = Demo(TAX, ia=Intelligence(TAX, _modele_fidele())).club
    off = Demo(TAX, ia=Intelligence(TAX, None)).club
    apports = jouer(on)
    jouer(off)
    verifier_parite(on, off, apports)
    assert apports == {md.PAULINE: {"places": 14}, md.MARKUS: {"places": 20}}          # le modèle a servi, deux fois
    etats = {i.finalite: i.statut for i in on.projection_capacites()}
    assert etats[A] == "ACTIVE"                                                        # et le parcours va au bout


def test_parite_on_off_avec_interrupteur():
    """Même monde, même modèle : l'interrupteur éteint suffit à retrouver l'état de l'IA absente."""
    on = Demo(TAX, ia=Intelligence(TAX, _modele_fidele())).club
    eteinte = Demo(TAX, ia=Intelligence(TAX, _modele_fidele())).club
    eteinte.basculer_ia(False)
    apports = jouer(on)
    jouer(eteinte)
    verifier_parite(on, eteinte, apports)


def test_la_parite_vacueuse_est_detectee():
    """Si TOUTES les sorties ON sont rejetées (modèle infidèle), la vérification échoue au lieu de passer à vide."""
    on = Demo(TAX, ia=Intelligence(TAX, ModeleScripte(extraire_piece={"attributs": {"places": 99}},
                                                      raconter_capacite={"phrases": [{"texte": "Tout va bien.", "faits": []}]}))).club
    off = Demo(TAX, ia=Intelligence(TAX, None)).club
    apports = jouer(on)
    jouer(off)
    assert etat_metier(on) == etat_metier(off)                                          # les états sont égaux…
    with pytest.raises(AssertionError, match="parité vacueuse"):                        # …mais rien n'a été prouvé
        verifier_parite(on, off, apports)
