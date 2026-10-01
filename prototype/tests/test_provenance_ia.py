"""F31 — une valeur PROPOSÉE par le modèle puis CONFIRMÉE telle quelle par le membre porte sa provenance
(`AI_PROPOSED_CONFIRMED`) et la trace de l'appel IA, dans le journal et au rejeu. Une valeur corrigée par le membre, ou
saisie sans proposition, reste `SELF_DECLARED`. Avant : le champ existait, jamais posé. Données FICTIVES."""
from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.demo import Demo
from intelligence.ia import Intelligence
from tests.modele_scripte import ModeleScripte

TAX = charger_taxonomie()
A = "delegation_acheteurs"


def _club():
    return Demo(TAX, ia=Intelligence(TAX, ModeleScripte(extraire_piece={"attributs": {"places": 14}}))).club


def _ask(c):
    return next(a for _, a in c.asks_pour(md.PAULINE) if a.startswith(A))


def _claim_de_la_reponse(c):
    oid = next(e.donnees["offre"] for e in c.journal.evenements("ASK_REPONSE") if e.donnees["oui"])
    return next(x for x in c.claims() if x.id.startswith(oid))


def test_valeur_proposee_par_le_modele_puis_confirmee(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    c = _club()
    ask = _ask(c)
    prop, appel, _ = c.proposer_reponse(md.PAULINE, ask, "Mon minibus a 14 places.")
    assert prop["attributs"] == {"places": 14} and appel.issue == "MODEL_CALLED"
    c.repondre_ask(md.PAULINE, ask, True, {"places": 14})

    rep = next(e for e in c.journal.evenements("ASK_REPONSE") if e.donnees["oui"])
    assert (rep.donnees["provenance"], rep.donnees["trace"]) == ("AI_PROPOSED_CONFIRMED", appel.trace)
    assert appel.trace in {e.donnees["appel"]["trace"] for e in c.journal.evenements("APPEL_IA")}   # une trace réelle
    assert _claim_de_la_reponse(c).provenance == "AI_PROPOSED_CONFIRMED"
    decl = [d for d in c.vues_capacites.mes_donnees(md.PAULINE)["declarations"] if d["texte"] == _claim_de_la_reponse(c).texte]
    assert decl and decl[0]["provenance"] == "proposé par l'IA à partir de votre texte, confirmé par vous"
    assert _claim_de_la_reponse(Demo(TAX, reprendre=True).club).provenance == "AI_PROPOSED_CONFIRMED"   # au rejeu


def test_valeur_corrigee_par_le_membre_reste_declaree_par_lui(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    c = _club()
    ask = _ask(c)
    c.proposer_reponse(md.PAULINE, ask, "Mon minibus a 14 places.")
    c.repondre_ask(md.PAULINE, ask, True, {"places": 16})
    rep = next(e for e in c.journal.evenements("ASK_REPONSE") if e.donnees["oui"])
    assert (rep.donnees["provenance"], rep.donnees.get("trace")) == ("SELF_DECLARED", None)
    assert _claim_de_la_reponse(c).provenance == "SELF_DECLARED"


def test_sans_proposition_la_valeur_est_declaree_par_le_membre(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    c = _club()
    c.repondre_ask(md.PAULINE, _ask(c), True, {"places": 14})
    assert _claim_de_la_reponse(c).provenance == "SELF_DECLARED"


def test_la_proposition_d_un_autre_membre_ne_compte_pas(tmp_path, monkeypatch):
    """La proposition est liée à QUI l'a demandée et à QUELLE demande : on ne s'approprie pas celle d'un autre."""
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    c = _club()
    ask = _ask(c)
    c.proposer_reponse(md.PAULINE, ask, "Mon minibus a 14 places.")
    proposition = [e for e in c.journal.evenements("PROPOSITION_IA")]
    assert [(e.acteurs, e.donnees["ask"]) for e in proposition] == [([md.PAULINE], ask)]
