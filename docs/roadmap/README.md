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

## Tableau d'avancement — état au 03.10.2026, 15:30 (branche `foire-2026`, dernier commit de la nuit ; gel-final le 04.10 à 08:00)

✅ fait et testé · 🟡 en cours / partiel · ⬜ prévu

| Élément | État | Preuve |
|---|---|---|
| Registre des capacités : pièces déclarées, consenties par finalité, reçu, retrait anonyme | ✅ | CLAIMS n° 2, 3, 19 |
| Journal rejouable, mode salle (sans Internet), IA allumée / éteinte à parité | ✅ | CLAIMS n° 5, 7, 15 |
| **Suivi** : agrégats, k = 3, nominatif sous double accord | ✅ | CLAIMS n° 43–46, 48 |
| **Clôture de reçu** : quatre étapes, résultat déclaré | ✅ | CLAIMS n° 47 |
| **Anonymat à petite échelle** : rôle masqué sous 3 porteurs | ✅ | CLAIMS n° 41–42 |
| **Passe découverte** 90 jours (invité non membre) | ✅ | CLAIMS n° 49–53 |
| **« Le Club cherche »** + inviter un contact (FR / DE) | ✅ | CLAIMS n° 54–56 |
| Membre à distance : zone, langue, réponse depuis l'e-mail | ✅ prototype | CLAIMS n° 57–60 — **l'envoi d'e-mails est simulé en démonstration** (boîte de sortie, aucun SMTP) |
| Bilan de période (`make bilan`) | ✅ | CLAIMS n° 61–62 ; récit Apertus vérifié par le code — aucun récit réel généré cette nuit |
| Pipeline Tally → jeu d'évaluation, taxonomie, harnais | 🟡 | pipeline, taxonomie (21 métiers FR / DE) et harnais livrés (CLAIMS n° 63–65) ; mesure Apertus sur les 26 cas ; **les 21 phrases Tally ne sont pas encore arrivées dans le dépôt** ; annotation humaine à faire |
| Pilote avec les membres réels | ⬜ | phase 1 de la [ROADMAP.md](ROADMAP.md) |
| Interface en allemand | 🟡 | écrans d'invité, page de réponse et e-mails FR / DE ; le reste en phase 2 |
| Adhésion croisée avec un partenaire français | ⬜ | phase 2 |
| Conversion d'adhésion réelle | ⬜ | « Rejoindre le Club » enregistre une intention ; la suite est **simulée en démonstration** |
