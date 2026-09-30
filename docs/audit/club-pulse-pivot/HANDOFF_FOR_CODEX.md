# Passage à Codex — Club Pulse : une action collective qui prend vie

> Auto-évaluation de l'équipe de développement (Claude) : **rien ici n'est une validation indépendante**, ni un avis
> de jury, ni un usage réel. Statut proposé : **TERMINÉ POUR AUDIT**, avec les réserves du § 12.
> Branche `claude/modest-bohr-xvk53n`. Le commit exact est celui qui contient ce fichier ; la vidéo et les captures
> indiquent le commit de code enregistré (`captures/action/demo_action.json` → `commit`). Version précédente de ce
> dossier (banc d'essai « étiquette ») : commit `abc2dc6`.

## 1. Ce qui est démontré — et ce qui ne l'est pas
Proposition montrée **sur un cas**, comme hypothèse : « Club Pulse transforme des contributions dispersées en une action
collective qu'aucun des membres mobilisés ne pouvait réaliser seul avec les offres disponibles. »
- **Montré** (F, testé) : sur des offres fictives déclarées avec horaires, le serveur trouve le créneau où elles se
  recouvrent, recueille l'accord de chacun sur **sa** part et **une** version, recalcule quand une condition change,
  propose des adaptations admissibles ou se déclare bloqué, et suit un résultat concret (fiche transmise → reçue).
- **Vrai par construction** (dit) : « aucun ne pouvait seul » — une personne ne porte pas deux gestes ; chaque offre
  ne couvre qu'une exigence.
- **Non montré** : que des membres réels aient ce besoin, formulent ainsi, préfèrent cela à leur groupe habituel ; que
  l'IA apporte quelque chose (Apertus non exécuté ; la démo tourne en règles simples, affiché).

## 2. Scénario et arbitrages
Sophie (fictive) veut présenter ses tisanes à des acheteurs germanophones jeudi pendant la Foire ; ni stand, ni
allemand, et elle veut laisser une fiche en allemand. Voir `DEMO_SCRIPT.md`.
| Arbitrage | Choix | Pourquoi |
|---|---|---|
| valeur Club ↔ effet jury | un besoin **à plusieurs** borné dans le temps (Foire) plutôt qu'un fil d'opportunités | le Club organise des événements ; un créneau partagé est une contrainte réelle et visible |
| profondeur ↔ temps | recherche **exhaustive bornée** au quart d'heure (fenêtre × durées × gestes × offres) | suffisant, explicable, testable ; aucun solveur |
| IA ↔ contrôle | une seule tâche IA (comprendre le besoin), validée par schéma ; tout le reste déterministe | disponibilités, droits, accords, capacités et transitions ne sont jamais décidés par un modèle |
| effet ↔ honnêteté | écran commun en **rôles**, projection **consentie**, états jamais plus forts que leur preuve | la revue contradictoire a trouvé et fait corriger 3 affichages trop forts (`REVUE_JURY.md`) |

## 3. Lancer, réinitialiser, rejouer
```bash
make setup && make quality-check          # dépendances exactes puis tout (secrets, ruff, mypy, tests, E2E, bancs)
make demo                                 # http://127.0.0.1:8000 : /console, /projection, /app, /demo/regie
```
Réinitialiser : console → « Nouvelle démonstration » (ou `POST /api/pulse/demo/reinitialiser`, en-tête console).
Rejouer le parcours complet dans un vrai navigateur : `cd prototype && python -m pytest -q tests/test_e2e_action.py`.
Réenregistrer la vidéo (exécution réelle, sans montage) : serveur démo sur le port 8767 puis
`python scripts/enregistrer_demo.py --sortie ../docs/audit/club-pulse-pivot/captures/action --commit $(git rev-parse --short HEAD) [--heure 17:15]`.

## 4. Architecture (tranche)
```
web/pulse/app.html (téléphones) · projection.html (écran commun) · console.html · regie.html
        │ HTTP JSON (sessions X-Pulse-Session ; console X-Pulse-Console)
app/essai_api.py ─ app/pulse_api.py        (adaptateurs minces : aucune règle métier ; test d'architecture)
        │
intelligence/club_pulse.py   service : préparer / créer / publier une action, modifier une offre, gestes joués
intelligence/vues_essai.py   qui voit quoi : téléphone du porteur, du contributeur, console, écran commun
intelligence/essai.py        domaine : offres + plages, créneaux, accords versionnés, adaptation, livraison, réception
intelligence/ia.py           comprendre_action (Apertus validé | règles simples), prompts/comprendre_action_v1.md
        │
plateforme/memoire.py        journal SQLite en ajout seul, transactions
```

## 5. Modèle et invariants (points de contrôle)
- **Offre** : auteur, nature, capacité codée (`concept`), conditions, durée max, période, **plages déclarées**. Rien
  n'est supposé : sans plage, une offre n'entre dans aucune action à créneau.
- **Accord** = `ACCORD{version, accepte, portee (empreinte), offres (empreinte matérielle par geste)}`. Il couvre la
  version courante **si et seulement si** la portée de la personne est identique, l'offre couvre encore le geste
  (active, durée, date, **plage**, capacité, **pas déjà engagée sur un créneau qui chevauche**) et ses conditions
  matérielles n'ont pas changé (P1). Chaque geste est vérifié (P2). `Banc.raisons_gestes`, `Banc.couverture`.
- **Moment d'engagement** : `Banc.lancer` revérifie sous le verrou ; refus → réévaluation écrite, lancement refusé.
- **Transitions** : table `TRANSITIONS`. `IMPOSSIBLE` n'est pas terminal : seul un fait nouveau rouvre une
  **adaptation** (jamais un lancement) ; à l'échéance → `EXPIRE`.
- **Paliers** (`VuesEssai.palier`) : manquant → proposé → accepté → transmis → **livrable reçu** → reçu (contribution
  constatée, pas avant le jour du créneau). Silence → `RESULTAT_INCONNU`, jamais un succès.
- **Après l'action** : l'état actuel d'une offre ne requalifie plus un accord engagé (une plage datée qui expire n'est
  pas un désistement).

## 6. Corrections d'audit et preuves
| Constat | Correction | Test qui le détecte (échoue sans la correction) |
|---|---|---|
| P1 — conditions matérielles d'une offre changées : l'accord restait | empreinte matérielle dans l'accord ; adaptation ; révision explicite (« accepter_conditions ») + nouvelle confirmation | `test_audit_essai.py::test_p1_*` : 4 des 5 tests P1/P2 échouaient sur l'ancien code ; `test_p1_un_changement_numerique…` garde contre la sur-correction |
| P2 — une personne, plusieurs gestes : un seul vérifié | `raisons_gestes` par geste | `test_p2_chaque_geste_d_une_meme_personne_est_verifie` |
| Revue jury — fiche reçue valait présentation tenue ; retrait ensuite ignoré | `recevoir` ≠ `constater` | `test_une_fiche_recue_ne_vaut_pas_la_presentation…`, `test_creneaux.py::test_livrable_transmis…` |
| Revue jury — une personne engagée deux fois au même moment | `occupations` / `_chevauche` | `test_une_personne_n_est_jamais_engagee_deux_fois…` (mutation vérifiée) |
| Équipe — +30 j : accord engagé affiché « ne couvre plus » | coverage figée après le moment de l'action | `test_trente_jours_plus_tard…` (mutation vérifiée) |
| Revue jury — brouillon et texte d'offre projetés | consentement de la porteuse ; projection en rôles et horaires | `test_rien_n_est_projete_sans_l_accord…` |
| Revue jury — besoins ajoutés par une règle ; banc IA qui récompensait l'invention | livrable/lieu seulement si demandés ; notation exacte | `eval/eval_apertus.py` (score recalculé, § 8) |
| Revue jury — « le seul moment » faux | recouvrement réel transmis ; « seul » seulement s'il l'est | `test_le_creneau_propose_n_est_dit_seul_que_s_il_l_est` |

## 7. Téléphones, écran commun, confidentialité
- Deux sessions distinctes (codes d'invitation → jeton signé) ; **un clic de console n'est pas un geste de
  téléphone** : la console ne peut jouer que les rôles absents (Pauline, Markus, Nicolas…), jamais Léa (403), et
  chaque geste joué est journalisé avec son rôle et affiché « joué par l'équipe ».
- Écran commun : seulement l'action **que sa porteuse a choisi de montrer** (retirable) ; des rôles, des horaires et
  des états — ni nom, ni texte d'offre, ni note, ni code, ni jeton, ni détail d'un refus (tests paramétrés sur 4
  étapes + balayage `eval/benchmark_pulse.py` des écrans). Version affichée ; « hors ligne : écran figé » si le serveur
  ne répond pas (jamais un état inventé).
- Délais mesurés, geste sur un téléphone → visible sur l'écran commun (lecture toutes les 0,7 s) : test navigateur
  `delais.json` (page de projection seule) ; enregistrement `demo_action.json` (régie à 3 cadres + capture vidéo,
  donc plus lent). Machine de développement, pas un réseau de salle.

## 8. IA
Tâche : `comprendre_action` (texte libre → exigences, fenêtre, ce qui manque). Prompt versionné
`prompts/comprendre_action_v1.md` ; sortie validée par schéma et règles (rôles connus, heures plausibles, fenêtre
cohérente, aucune personne ni disponibilité) ; trace : fournisseur, modèle, tâche, version du prompt, validation.
**Apertus : NON EXÉCUTÉ** — aucune variable `APERTUS_*` ; aucun compte, aucune dépense. Repli **affiché** sur le
téléphone (« Règles simples — aucun modèle utilisé »). Banc : `eval/resultats_apertus.md` (repli seulement ; échecs
attendus : heures explicites variées, texte en allemand, besoins implicites).

## 9. Réel, fictif, joué, simulé, déclaré, non testé
| Catégorie | Ce qui l'est |
|---|---|
| Réel | le code, les tests exécutés, l'enregistrement vidéo (exécution continue, commit à l'image) |
| Fictif | membres, entreprises, offres, horaires, fiche en allemand |
| Joué | accords et disponibilités des rôles absents de la scène, depuis la console — affiché |
| Simulé | l'horloge (date simulée affichée ; +30 jours) |
| Déclaré | l'observation d'un résultat par la porteuse (contestable) ; la part « produit » de la porteuse |
| Non testé | vrais téléphones sur un réseau de salle ; Apertus réel ; tout membre ou juré réel ; plusieurs processus |

## 10. Tests exécutés
Voir `PREUVES.md` (commandes, résultats, date). Principaux : `test_action_collective.py` (parcours par l'API avec
sessions distinctes, perturbation, valeurs du jury, blocage puis réouverture, projection, +30 jours),
`test_creneaux.py`, `test_audit_essai.py`, `test_essai_invariants.py` (marches aléatoires), `test_e2e_action.py`
(deux téléphones + écran commun dans Chromium).

## 11. Équipe de 5 ingénieurs (si le projet continue)
| Rôle | Périmètre | Premier livrable |
|---|---|---|
| Domaine / audit | `essai.py`, invariants, type d'acte par geste (§ 13 n° 1) | compatibilité opérationnelle + tests de propriété |
| IA | `ia.py`, prompts, banc | Apertus réel sur 30 formulations réelles, notation stricte |
| Mobile | `app.html` | notifications, reprise hors ligne, accessibilité |
| Projection / pitch | `projection.html`, `regie.html`, scripts | test des 30 s avec 3 personnes extérieures |
| Intégration / démo / terrain | déploiement salle, validation terrain | protocole ci-dessous |

**Validation terrain courte** (non faite) : à la prochaine Foire, 3 exposants volontaires ; même besoin traité par le
canal habituel du Club et par Club Pulse ; mesurer le temps jusqu'à une équipe confirmée, les erreurs de créneau, les
relances, et ce que chacun a corrigé dans les exigences proposées. Consentement écrit ; aucune donnée publiée sans accord.

## 12. Limites connues
1. Besoin non validé ; aucune donnée d'usage ; aucun jury réel.
2. Apertus réel non testé ; le repli ne comprend ni l'allemand ni les heures inhabituelles.
3. Compatibilité = nature + capacité codée + horaire : un **conseil** export daté serait proposé pour **amener** des acheteurs.
4. Un processus ; verrou, limiteurs et sessions en mémoire ; le journal (accords, consentement de projection) est durable seulement avec `HACKVS_ESSAIS_DB`.
5. Codes d'invitation réutilisables, sans expiration ; pas de révocation individuelle d'un jeton.
6. Effacement : un texte libre saisi par un autre membre peut encore nommer une personne effacée.
7. Horloge de démonstration au jour ; pas de fuseau ; créneaux au quart d'heure.
8. Relecture toutes les 0,7 s (pas de notification poussée).

## 13. À attaquer en priorité
1. `offre_couvre` : une offre compatible par code mais pas par **acte** (conseiller ≠ amener) — trouver un cas démontrable.
2. `occupations` : un accord donné dans un essai `A_ADAPTER` bloque-t-il à tort un autre essai ? (choix : il compte.)
3. `raisons_gestes` après l'action (`passe`) : un retrait **pendant** `EN_COURS` avant le jour du créneau garde-t-il son effet ? (oui, testé ; au-delà ?)
4. `recevoir` / `livrer` : une version corrigée transmise après réception est refusée ; est-ce le bon choix ?
5. Projection : un champ dérivé (cause, pourquoi, alternatives) peut-il encore désigner quelqu'un par une heure rare ?
6. `_action_regles` : quelles formulations produisent encore une exigence non demandée ?
7. Anciennes routes (banc d'essai « étiquette », découvertes) toujours servies : faut-il les couper en démonstration ?
