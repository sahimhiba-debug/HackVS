"""FRONTIÈRE IA, vérifiée par un ESPION à la place du fournisseur : il enregistre TOUT ce qui quitterait le serveur.

1. Aucune identité réelle du coffre (nom, organisation, courriel, téléphone) n'entre dans le contexte envoyé au
   modèle — pour CHACUNE des tâches de langage appelées par le service, même quand le membre écrit ces noms lui-même.
   Défaut trouvé à l'audit (2026-09-30) : `demander` → `comprendre_demande` envoyait le texte brut, nom réel compris.
2. Une LECTURE (vues, projection, rafraîchissement) et un REJEU (redémarrage sur le même journal) n'appellent jamais
   le modèle : les textes rédigés sont écrits par une commande et journalisés, puis relus.
Données FICTIVES."""
from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.club_pulse import CRITERE_SUGGERE, ClubPulse
from intelligence.erreurs import Introuvable
from intelligence.ia import Intelligence
from intelligence.politique import Spectateur

TAX = charger_taxonomie()
TACHES = {"comprendre_demande", "comprendre_action", "structurer_essai", "capturer_rencontre", "expliquer_opportunite",
          "rediger_sollicitation"}


class Espion:
    nom, modele = "espion", "espion-1"

    def __init__(self):
        self.envois: list[tuple[str, str]] = []

    def completer(self, systeme_txt: str, message: str, schema) -> str:
        self.envois.append((systeme_txt, message))
        return "{}"                                        # sortie invalide : repli ; seul ce qui PART nous intéresse


def _club(espion: Espion) -> ClubPulse:
    return ClubPulse(TAX, Intelligence(TAX, espion, notes_privees_autorisees=True))   # même les notes partent : pire cas


def _identites(c: ClubPulse) -> list[str]:
    per = list(c.coffre._personnes.values())
    orgs = [o.nom.replace("(fictive)", "").replace("(fictif)", "").strip() for o in c.coffre.orgs.values()]
    return [p.nom for p in per] + [p.courriel for p in per] + [p.telephone for p in per if p.telephone] + orgs


def _narrer(c: ClubPulse, oid: str) -> None:
    # compatibilité avec le code d'AVANT la correction (pour prouver que ce test y échouait) : la reformulation se
    # faisait alors à la LECTURE (`en_clair`)
    f = getattr(c, "narrer_decouverte", None)
    (f or c.en_clair)(oid, Spectateur("membre", md.SOPHIE))


def _rediger(c: ClubPulse, eid: str) -> None:
    f = getattr(c, "rediger_invitations", None)                 # avant la correction : rédigé à la lecture de l'invité
    f(eid) if f else c.vues_essai.essai(eid, md.MARKUS)


def _invitation(c: ClubPulse, question: str) -> str:
    c.activer_compte(c.coffre.code_invitation(md.SOPHIE))
    c.onboarding(md.SOPHIE, aide=[{"texte": "tisanes de plantes alpines bio", "concept": "boissons"}],
                 cherche=[{"texte": "Trouver un distributeur pour entrer sur le marché allemand", "concept": "export_allemagne"}], visible=True)
    o = next(x for x in c.scanner()["opportunites"] if x.beneficiaire == md.SOPHIE and md.MARKUS in {r.membre for r in x.roles})
    _narrer(c, o.id)                                            # COMMANDE : la reformulation IA, journalisée
    eid = c.proposer_essai(md.SOPHIE, o.id)
    p = c.banc.protocole(eid).model_copy(update={"critere": CRITERE_SUGGERE, "question": question})
    v = c.banc.modifier_brouillon(md.SOPHIE, eid, 0, p)
    c.banc.proposer(md.SOPHIE, eid, v)
    _rediger(c, eid)                                          # la COMMANDE qui rédige (ce que fait l'API après une écriture)
    return o.id


def test_aucune_identite_du_coffre_n_entre_dans_le_contexte_envoye_au_modele():
    espion = Espion()
    c = _club(espion)
    lea, markus = c.coffre.identite(md.LEA), c.coffre.identite(md.MARKUS)
    org_lea = c.coffre.organisation_de(md.LEA).nom
    # le membre écrit lui-même des noms, une organisation, un courriel : rien de cela ne doit partir
    c.demander(md.SOPHIE, f"Je cherche quelqu'un comme {lea.nom} ({org_lea}) pour traduire nos fiches ; écrire à {lea.courriel}.")
    c.preparer_action(md.SOPHIE, f"Avec {lea.nom}, présenter nos tisanes jeudi après-midi à des acheteurs germanophones.")
    c.preparer_essai(md.SOPHIE, f"{markus.nom} comprend-il notre étiquette en 10 secondes ?")
    c.capturer(md.SOPHIE, f"Rencontré {markus.nom} au salon : il cherche un produit bio pour Munich. Son courriel : {markus.courriel}.")
    _invitation(c, f"Présenter nos tisanes avec l'aide de {lea.nom}")
    taches = {a.tache for a in c.ia.appels if a.fournisseur == "espion"}
    assert TACHES <= taches, TACHES - taches                  # chaque tâche est réellement passée par l'espion
    fuites = [(x, i) for i, (sys_, msg) in enumerate(espion.envois) for x in _identites(c) if x and (x in msg or x in sys_)]
    assert not fuites, fuites


def test_une_lecture_ou_un_rejeu_n_appelle_jamais_le_modele(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "essais.db"))
    espion = Espion()
    c = _club(espion)
    oid = _invitation(c, "Présenter nos tisanes à un distributeur allemand")
    eid = c.banc.essais()[-1]
    avant, empreinte = len(espion.envois), c.banc.m.empreinte()
    message = c.vues_essai.essai(eid, md.MARKUS)["message"]
    assert message["ia"]["fournisseur"] == "espion"          # rédigé par la commande, relu ici

    def tout_lire(club: ClubPulse) -> None:
        for _ in range(3):                                      # rafraîchissements répétés
            for pid in (md.SOPHIE, md.MARKUS):
                club.vues_essai.essai(eid, pid)
                club.vues_essai.actions(pid)
                club.vues_essai.souvenirs(pid)
            club.vues_essai.console()
            club.vues_essai.projection(eid, club.joues)
            club.vues.decouvertes_de(md.SOPHIE)
            try:
                club.en_clair(oid, Spectateur("membre", md.SOPHIE))
            except Introuvable:                                 # la découverte a donné lieu à un essai : plus proposée
                pass

    tout_lire(c)
    assert len(espion.envois) == avant and c.banc.m.empreinte() == empreinte          # lire n'appelle rien, n'écrit rien

    rejeu = Espion()                                            # redémarrage : même journal, nouveau processus logique
    c2 = _club(rejeu)
    c2.activer_compte(c2.coffre.code_invitation(md.SOPHIE))
    assert c2.vues_essai.essai(eid, md.MARKUS)["message"] == message                  # relu du journal, à l'identique
    tout_lire(c2)
    assert rejeu.envois == [] and c2.banc.m.empreinte() == empreinte
