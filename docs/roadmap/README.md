# Club Pulse — où on en est, où on va

Prototype présenté à la Foire du Valais 2026, sur un **monde de démonstration** (150 profils fictifs, horloge
simulée). Le Club réel compte **une cinquantaine de membres** ; rien ici n'a encore tourné sur ses données.

| Document | Contenu |
|---|---|
| [ROADMAP.md](ROADMAP.md) | les six prochains mois : cadrage, pilote mesuré, au-delà du Valais romand, « Allumage Foire » |
| [SUIVI_METRIQUES.md](SUIVI_METRIQUES.md) | chaque métrique de l'écran Suivi, les quatre étapes, les règles de confidentialité, ce qu'on ne suit jamais |
| [FINANCEMENT_JURIDIQUE.md](FINANCEMENT_JURIDIQUE.md) | Interreg, Innosuisse, The Ark, NPR ; nLPD, RGPD, consentement prouvé (analyse générale, pas un avis juridique) |
| [BENCHMARK.md](BENCHMARK.md) | BNI, Protopia, nexxt-change, Sardex / WIR, CCI France Suisse, b2match, Lunchclub — et la leçon de chacun |
| [APERTUS_PLAN.md](APERTUS_PLAN.md) | état mesuré (1/26), jeu de test humain figé, entraînement synthétique, LoRA, service en Suisse |

## Tableau d'avancement

<!-- etat:debut (généré depuis etat.yaml — ne pas éditer à la main) -->
*État au 03.10.2026, généré depuis [etat.yaml](etat.yaml).* ✅ construit (code + tests) · 🟢 validé sur le terrain (preuve réelle) · ⬜ prévu

| Chantier | Statut | Preuve |
|---|---|---|
| Registre des capacités — pièces déclarées, consenties par finalité, reçu | ✅ Construit | test_capacites_regles.py, test_capacites_oracle.py |
| Retrait anonyme en un geste, rôle masqué sous trois porteurs | ✅ Construit | test_capacites_retrait.py, test_foire_anonymat.py |
| Mode salle « le Club, c'est vous » — QR, constellation, purge | ✅ Construit | test_salle.py, test_e2e_salle.py |
| Suivi des partenariats — agrégats, « < 3 », nominatif sous double accord | ✅ Construit | test_foire_suivi.py |
| Passe découverte 90 jours pour les non-membres | ✅ Construit | test_foire_decouverte.py, test_e2e_foire.py |
| « Le Club cherche » et inviter un contact (FR / DE) | ✅ Construit | test_foire_club_cherche.py |
| Membre à distance et réponse depuis l'e-mail (envoi simulé en démonstration) | ✅ Construit | test_foire_distance.py |
| Bilan de période (make bilan), récit IA vérifié par le code | ✅ Construit | test_foire_bilan.py |
| Prêt à déployer (VPS, HTTPS) et charge de 80 téléphones mesurée en local | ✅ Construit | test_deploiement.py |
| La carte devient le profil — photo de sa carte, Apertus propose, le membre confirme | ✅ Construit | test_carte_profil.py, test_e2e_foire.py |
| Phrases recueillies par le QR de la Foire (21, en agrégats) | 🟢 Validé sur le terrain | 21 réponses réelles du 03.10.2026 ; 20 fr, 1 en ; classées par Apertus seulement (21 validées, 20 abstentions) — PREUVES.md |
| Pilote de 45 jours avec les 50 membres (janvier – mi-février 2027) | ⬜ Prévu | critères à valider avec le Club |
| Analyse d'impact nLPD / RGPD avec un juriste | ⬜ Prévu | — |
| Audit de sécurité externe avant le lancement | ⬜ Prévu | — |
| Premier partenaire français (adhésion croisée) | ⬜ Prévu | aucun partenaire acquis |
| Dépôt Interreg France-Suisse avant le 12 mars 2027 | ⬜ Prévu | — |
| Reçus en attestations vérifiables dans le portefeuille swiyu (e-ID) | ⬜ Prévu | note d'architecture — docs/roadmap/ARCHITECTURE_SWIYU_VOIX_MINI.md |
| Demandes vocales via l'entrée audio d'Apertus 1.5 (expérimentale, à mesurer en français et en dialecte) | ⬜ Prévu | note d'architecture — docs/roadmap/ARCHITECTURE_SWIYU_VOIX_MINI.md |
| Extraction sur le téléphone avec Apertus Mini | ⬜ Prévu | note d'architecture — docs/roadmap/ARCHITECTURE_SWIYU_VOIX_MINI.md |
<!-- etat:fin -->

Page publique, trilingue, avec des liens vers les écrans du monde « visite » : `/feuille-de-route`.
