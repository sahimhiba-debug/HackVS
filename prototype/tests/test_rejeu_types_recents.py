"""Rejeu au redémarrage des types d'événements AJOUTÉS après la Phase 1 (F07) : `APPEL_IA` (avec clé de rejeu),
`PASSE_JURE`, `RECHERCHE_RELANCEE`, `RECHERCHE_ACQUITTEE`, retrait de finalité. Même journal → même état, sans aucun
appel au modèle ; un récit déjà produit est RELU du journal, jamais redemandé. Données FICTIVES.

La clé de rejeu d'un appel IA est un HMAC du secret (`HACKVS_SECRET`) : sans secret fourni, chaque processus en tire un
au hasard et un redémarrage ne retrouve PAS les sorties acceptées (l'état, lui, reste identique). Voir F24."""
from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.demo import Demo
from intelligence.ia import Intelligence
from tests.modele_scripte import ModeleScripte

TAX = charger_taxonomie()
A = "delegation_acheteurs"
SECRET = "un-secret-de-test-assez-long-pour-32-octets!"
RECIT = {"phrases": [{"texte": "État : un consentement ne vaut plus.", "faits": ["F1"]}]}   # l'état final du parcours


def _projection(c):
    return [(i.finalite, i.statut, i.distance, i.recherche_relancee, str(i.acquittee_le)) for i in c.projection_capacites()]


def _vivre(c) -> None:
    ask = next(a for _, a in c.asks_pour(md.PAULINE) if a.startswith(A))
    c.proposer_reponse(md.PAULINE, ask, "Mon minibus a 14 places.")                 # APPEL_IA (EXTRACT)
    c.repondre_ask(md.PAULINE, ask, True, {"places": 14})
    c.retirer_consentement(md.PAULINE, A)                                             # RETRAIT de finalité
    p = c.emettre_pass_jure(md.MARKUS, 15)
    c.utiliser_pass_jure(p["jeton"])                                                  # PASSE_JURE
    c.banc.BUDGET_NOEUDS = 1                                                          # recherche bornée → relance possible
    c.relancer_recherche(A)                                                           # RECHERCHE_RELANCEE
    bornee = [i.finalite for i in c.capacites.projeter() if i.recherche_bornee]
    if bornee:
        c.acquitter_recherche(bornee[0])                                              # RECHERCHE_ACQUITTEE
    c.banc.BUDGET_NOEUDS = c.reglages.budget_noeuds
    c.avancer(1)
    assert c.raconter_capacite(A)[1].issue == "MODEL_CALLED"                          # APPEL_IA (NARRATE), en dernier :
                                                                                      # la clé porte sur les faits du moment


def test_les_types_recents_se_rejouent_a_l_identique_sans_appel_au_modele(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    monkeypatch.setenv("HACKVS_SECRET", SECRET)                                       # configuration servie (F24)
    modele = ModeleScripte(extraire_piece={"attributs": {"places": 14}}, raconter_capacite=RECIT)
    c = Demo(TAX, ia=Intelligence(TAX, modele)).club
    _vivre(c)
    types = {e.type for e in c.journal.evenements()}
    assert {"APPEL_IA", "PASSE_JURE", "RECHERCHE_RELANCEE", "RETRAIT"} <= types, types   # non vacueux : ils y sont
    assert modele.appels("raconter_capacite") == 1

    muet = ModeleScripte()                                                            # aucun rôle scripté : tout appel échouerait
    relu = Demo(TAX, ia=Intelligence(TAX, muet), reprendre=True).club                 # redémarrage sur le même journal
    assert len(relu.journal.evenements()) == len(c.journal.evenements())
    assert relu.empreinte_etat() == c.empreinte_etat()
    assert _projection(relu) == _projection(c)
    assert relu.ia.appels == []                                                       # rejouer ne rappelle jamais le modèle

    recit, appel = relu.raconter_capacite(A)                                          # déjà raconté : RELU, pas redemandé
    assert appel.issue == "CACHE_REPLAY" and recit["phrases"] == RECIT["phrases"]
    assert muet.appels("raconter_capacite") == 0


def test_contre_epreuve_une_relance_change_l_empreinte(tmp_path, monkeypatch):
    """Sans cette contre-épreuve, l'égalité ci-dessus pourrait tenir parce que l'empreinte ignore ces types."""
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    c = Demo(TAX).club
    c.banc.BUDGET_NOEUDS = 1
    avant = c.empreinte_etat()
    c.relancer_recherche(A)
    assert c.empreinte_etat() != avant


def test_sans_secret_fourni_le_redemarrage_ne_rejoue_pas_l_ia_mais_garde_l_etat(tmp_path, monkeypatch):
    """Limite ACTUELLE, constatée et consignée (F24, décision en attente) — pas une propriété voulue. Le statut reste
    véridique : ce n'est jamais présenté comme un rejeu."""
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    monkeypatch.delenv("HACKVS_SECRET", raising=False)
    c = Demo(TAX, ia=Intelligence(TAX, ModeleScripte(extraire_piece={"attributs": {"places": 14}}, raconter_capacite=RECIT))).club
    _vivre(c)
    relu = Demo(TAX, ia=Intelligence(TAX, ModeleScripte()), reprendre=True).club
    assert relu.empreinte_etat() == c.empreinte_etat() and relu.ia.appels == []
    assert relu.raconter_capacite(A)[1].issue != "CACHE_REPLAY"
