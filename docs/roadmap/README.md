# Club Pulse — où on en est, où on va

Prototype présenté à la Foire du Valais 2026, sur un **monde de démonstration** (150 profils fictifs, horloge
simulée). Le Club réel compte **145 entreprises et 173 représentants** ; rien ici n'a encore tourné sur ses données.

| Document | Contenu |
|---|---|
| [ROADMAP.md](ROADMAP.md) | les six prochains mois : cadrage, pilote mesuré, au-delà du Valais romand, « Allumage Foire » |
| [SUIVI_METRIQUES.md](SUIVI_METRIQUES.md) | chaque métrique de l'écran Suivi, les quatre étapes, les règles de confidentialité, ce qu'on ne suit jamais |
| [FINANCEMENT_JURIDIQUE.md](FINANCEMENT_JURIDIQUE.md) | Interreg, Innosuisse, The Ark, NPR ; nLPD, RGPD, consentement prouvé (analyse générale, pas un avis juridique) |
| [BENCHMARK.md](BENCHMARK.md) | BNI, Protopia, nexxt-change, Sardex / WIR, CCI France Suisse, b2match, Lunchclub — et la leçon de chacun |
| [APERTUS_PLAN.md](APERTUS_PLAN.md) | état mesuré (1/26), jeu de test humain figé, entraînement synthétique, LoRA, service en Suisse |

## Tableau d'avancement

<!-- etat:debut (généré depuis etat.yaml — ne pas éditer à la main) -->
*État au 04.10.2026, généré depuis [etat.yaml](etat.yaml).* ✅ construit (code + tests) · 🟢 validé sur le terrain (preuve réelle) · ⬜ prévu · 🔧 construit sur la branche annee-1, pas dans la démo

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
| Démo servie depuis le Mac du pitch via un tunnel chiffré ; VPS prêt pour la production future ; charge de 80 téléphones mesurée en local | ✅ Construit | test_deploiement.py, test_tunnel.py |
| La carte devient le profil — photo de sa carte, Apertus propose, le membre confirme | ✅ Construit | test_carte_profil.py, test_e2e_foire.py |
| Reçus alignés sur ISO/IEC TS 27560 (export JSON-LD, vocabulaire DPV) — aligné, pas certifié | ✅ Construit | test_recu_27560.py |
| Statut « membre associé » via une organisation partenaire (exemple fictif) | ✅ Construit | test_associe.py |
| Coach SMART d'une demande (quand ? combien ? où ?), identique IA allumée ou éteinte | ✅ Construit | test_coach_smart.py |
| Suivi : nouveaux liens tissés entre entreprises | ✅ Construit | test_liens.py |
| Interface du téléphone en allemand (traduction à relire) | ✅ Construit | test_e2e_foire.py |
| Annonces sous chiffre, relayées jusqu'à l'accord mutuel | ✅ Construit | test_annonces.py |
| Tableau du secrétariat (agrégats) | ✅ Construit | test_tableau_bord.py |
| Escalade vers des membres piliers volontaires | ✅ Construit | test_piliers.py |
| Balance de réciprocité privée | ✅ Construit | test_reciprocite.py |
| Passe start-up — pont The Ark (proposé, à valider) | ✅ Construit | test_passe_startup.py |
| Information FR/DE et modèle de registre (à valider par un juriste) | ✅ Construit | test_deploiement.py |
| Pipeline d'affinage prêt (entraînement non lancé) | ✅ Construit | test_finetune.py |
| Phrases recueillies par le QR de la Foire (21, en agrégats) | 🟢 Validé sur le terrain | 21 réponses réelles du 03.10.2026 ; 20 fr, 1 en ; classées par Apertus seulement (21 validées, 20 abstentions) — PREUVES.md |
| Pilote de 45 jours avec 50 membres volontaires parmi les 173 représentants (janvier – mi-février 2027) | ⬜ Prévu | critères à valider avec le Club |
| Analyse d'impact nLPD / RGPD avec un juriste | ⬜ Prévu | — |
| Audit de sécurité externe avant le lancement | ⬜ Prévu | — |
| Premier partenaire français (adhésion croisée) | ⬜ Prévu | aucun partenaire acquis |
| Dépôt Interreg France-Suisse avant le 12 mars 2027 | ⬜ Prévu | — |
| Reçus en attestations vérifiables dans le portefeuille swiyu (e-ID) | ⬜ Prévu | note d'architecture — docs/roadmap/ARCHITECTURE_SWIYU_VOIX_MINI.md |
| Demandes vocales via l'entrée audio d'Apertus 1.5 (expérimentale, à mesurer en français et en dialecte) | ⬜ Prévu | note d'architecture — docs/roadmap/ARCHITECTURE_SWIYU_VOIX_MINI.md |
| Extraction sur le téléphone avec Apertus Mini | ⬜ Prévu | note d'architecture — docs/roadmap/ARCHITECTURE_SWIYU_VOIX_MINI.md |
| Journal sur stockage interchangeable SQLite / PostgreSQL, migrations réversibles, sauvegarde et restauration vérifiées | 🔧 Construit — branche annee-1, pas dans la démo | test_annee1_stockage.py |
| Exploitation — configuration documentée, disponibilité (/sante/pret), métriques, Docker de production | 🔧 Construit — branche annee-1, pas dans la démo | test_annee1_exploitation.py |
| Comptes et rôles — invitation à usage unique, sessions et appareils, comptes nominatifs, double authentification (TOTP) pour la console, journal d'administration | 🔧 Construit — branche annee-1, pas dans la démo | test_annee1_comptes.py, test_annee1_comptes_api.py |
| Espace membre — mode pause (vacances), préférences langue / région / canaux, mes demandes envoyées, solde privé « reçus / donnés », export de mes données, suppression du compte avec purge réelle du journal | 🔧 Construit — branche annee-1, pas dans la démo | test_annee1_espace_membre.py, test_annee1_espace_membre_api.py |
| Console du secrétariat — comptes (inviter, révoquer), métiers des entreprises à confirmer, critères du pilote gelés d'avance, bilan trimestriel (Markdown, CSV, PDF), « Le Club cherche » relié à une campagne d'invitation | 🔧 Construit — branche annee-1, pas dans la démo | test_annee1_secretariat.py, test_annee1_secretariat_api.py |
| Notifications — e-mail par n'importe quel serveur SMTP, SMS (interface et faux fournisseur), modèles FR/DE, suivi d'envoi sans adresse ni contenu, désinscription par lien signé ; en démo, tout simulé et étiqueté | 🔧 Construit — branche annee-1, pas dans la démo | test_annee1_notifications.py, test_annee1_notifications_api.py |
| Confiance et conformité — reçus 27560 aux termes DPV vérifiés, journal des accès à la console, HSTS en production, registre, analyse d'impact, politiques FR/DE et contrat de sous-traitance (à valider par un juriste), checklist ASVS niveau 2 | 🔧 Construit — branche annee-1, pas dans la démo | test_annee1_confiance.py, test_annee1_dpv.py |
| Suivi du taux d'acceptation de ce que le Club comprend d'une demande (modèle Apertus ou règles en repli), décomptes seulement, dans la console du secrétariat | 🔧 Construit — branche annee-1, pas dans la démo | test_annee1_suivi_ia.py |
| Plusieurs clubs — club partenaire (exemple fictif marqué), adhésion croisée choisie par le membre, membres à distance ; interface FR / DE / EN (à relire par un natif) | 🔧 Construit — branche annee-1, pas dans la démo | test_annee1_multiclub.py |
| Allumage Foire — borne de stand, import des exposants en CSV, passes découverte par lots de 500, adhésions venues du passe confirmées par le secrétariat | 🔧 Construit — branche annee-1, pas dans la démo | test_annee1_foire.py |
| Prototype e-ID — reçus émis comme attestations vérifiables SD-JWT VC (format du profil suisse), émetteur et vérificateur locaux ; prototype, non connecté à swiyu | 🔧 Construit — branche annee-1, pas dans la démo | test_annee1_attestations.py |
| Qualité — accessibilité WCAG 2.2 AA vérifiée par axe-core, application installable, file hors ligne des réponses, charge à 500 et 1 000 membres simulés, budgets de performance (budget des lectures dépassé, dit) | 🔧 Construit — branche annee-1, pas dans la démo | test_annee1_accessibilite.py |
| Cohérence visuelle — pages de l'année 1 alignées sur le Design System, captures avant / après ; refonte plus profonde non faite (décision écrite) | 🔧 Construit — branche annee-1, pas dans la démo | test_annee1_coherence_design.py |
<!-- etat:fin -->

Page publique, trilingue, avec des liens vers les écrans du monde « visite » : `/feuille-de-route`.
