# Évaluation de la plateforme de décision

Données FICTIVES (club de démonstration, club synthétique). Aucun LLM. Attendus fixés avant exécution.

**20/20 scénarios conformes.**

| # | Scénario | Résultat | ms | Détail |
|---|---|---|---|---|
| S01 | nominal : couverture, 3 tours | OK | 1538 | PROPOSER_A_L_HUMAIN |
| S02 | objectif diversité seul | OK | 2042 | [{'nom': 'diversite', 'sens': 'maximiser', 'poids': 1.0}] |
| S03 | demande vague → abstention | OK | 1 | S_ABSTENIR |
| S04 | lever le consentement → escalade | OK | 1 | ESCALADER_A_L_HUMAIN |
| S05 | injection dans l'intention → escalade | OK | 1 | ESCALADER_A_L_HUMAIN |
| S06 | paramètre hors bornes (9 tours) → escalade | OK | 1 | spécification refusée par la politique : tours=9 hors de [1, 6] |
| S07 | terme du domaine incompris → escalade | OK | 1 | vous mentionnez langue : je n'ai pas compris ce que vous voulez en faire |
| S08 | un seul participant → abstention | OK | 111 | S_ABSTENIR |
| S09 | aucun participant → abstention | OK | 2 | S_ABSTENIR |
| S10 | rejeu identique (démo) | OK | 2830 | d953de054437 |
| S11 | rejeu identique (synthétique, 150 membres) | OK | 11688 | 91 rencontres |
| S12 | branche levant le consentement refusée | OK | 1457 | branche refusée par la politique : contraintes imposées par la politique, non re |
| S13 | contre-factuel sans langue | OK | 2303 | {'rencontres_ajoutees': 2, 'rencontres_retirees': 2} |
| S14 | stress : 3 nœuds structurels retirés, réparation | OK | 4339 | orphelins 6, re-servis 3 |
| S15 | stress aléatoire reproductible (graine) | OK | 2893 | ['p12', 'p24', 'p29'] |
| S16 | preuves vérifiées exigées → blocage | OK | 2694 | BLOQUER |
| S17 | affirmations périmées → blocage | OK | 1066 | BLOQUER |
| S18 | déjà en relation → paire exclue | OK | 2717 | p00–p02 exclue |
| S19 | certificat dérivé des enregistrements | OK | 1257 | PROPOSER_A_L_HUMAIN |
| S20 | honnêteté sur données fictives | OK | 1138 | ['concentration', 'donnees_fictives', 'non_servis', 'preuves_non_verifiees'] |
