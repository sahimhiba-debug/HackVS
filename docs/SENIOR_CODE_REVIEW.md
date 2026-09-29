# Revue de code contradictoire — Club Pulse

> Cinq relecteurs fictifs, chacun avec son angle d'attaque, ont relu le dépôt **pour le casser**. Gravités :
> **P0** bloque toute démonstration honnête · **P1** défaut réel de sécurité, de confidentialité ou de justesse ·
> **P2** robustesse ou exploitation · **P3** style, dette assumée. Règle : **tout P0 et P1 est corrigé et prouvé par un
> test** (souvent par mutation : le test échoue sur l'ancien code). Les P2/P3 restants sont écrits avec leur raison.
> Commits sur la branche `claude/modest-bohr-xvk53n`.

## Les relecteurs

| | Angle | Question qu'il pose à chaque fichier |
|---|---|---|
| **R1 — Ingénieure backend principale** | justesse, états, concurrence, contrats | « Que se passe-t-il si deux requêtes arrivent en même temps, ou si celle-ci échoue au milieu ? » |
| **R2 — Ingénieur sécurité** | authentification, autorisation, entrées, secrets | « Comment je deviens quelqu'un d'autre, ou j'obtiens ce qui ne m'est pas destiné ? » |
| **R3 — Responsable protection des données** | identités, refus, notes, journaux, IA | « Où cette donnée va-t-elle, et qui peut la relier à une personne ? » |
| **R4 — Ingénieure plateforme IA** | frontière du modèle, pannes, coût, évaluation | « Et si le modèle ment, se tait, ralentit ou coûte ? » |
| **R5 — Ingénieur front + exploitation** | réseau instable, accessibilité, déploiement, reproductibilité | « Et sur un téléphone en 3G, dans un conteneur, sur une machine neuve ? » |

## Constats corrigés

| # | Grav. | Relecteur | Constat | Correctif | Preuve |
|---|---|---|---|---|---|
| 1 | **P0** | R2 | Secret par défaut **public** (`demo-seulement`) : n'importe qui pouvait forger la session de n'importe quel membre et calculer les codes d'invitation | aucun secret par défaut ; `HACKVS_SECRET` ≥ 32 caractères ou secret aléatoire par processus | `test_aucun_secret_par_defaut`, `test_sessions_falsifiees…` · d563def |
| 2 | **P0** | R5 | L'**image Docker plantait au démarrage** (`intelligence/` et `prompts/` non copiés) | Dockerfile complété ; versions exactes | `tests/test_image.py` (reconstitue l'image, échouait avant) · 05991c0 |
| 3 | P1 | R1 | Écritures **partielles** : `lancer` pouvait laisser une activation « en attente » sans sollicitation ; accord écrit alors qu'une sollicitation échouait | chaque commande du moteur est atomique (transaction SQLite) | `test_atomicite.py` · 82b3d51 |
| 4 | P1 | R1 | **TOCTOU** : une requête pouvait lire un monde et écrire dans un autre pendant une réinitialisation | `au_monde` : un monde capturé, un verrou, toute la requête dessous | `test_deux_acceptations_simultanees…`, `test_acceptation_et_annulation…` · d563def |
| 5 | P1 | R1 | « Déjà répondu » renvoyait **403** au lieu de **409** ; code inconnu ≠ 401 | erreurs typées, traduites à UN endroit | `test_intelligence_activation.py`, `test_securite_pulse.py` · 82b3d51 |
| 6 | P1 | R2 | Console pilotable **par un site tiers** (CSRF) | en-tête personnalisé exigé ; jeton exact si configuré | `test_console_exige…` · d563def |
| 7 | P1 | R2 | Sans jeton configuré, la console — qui **distribue la session de chaque membre** — répondait à toute machine du réseau | sans `HACKVS_CONSOLE_JETON`, console limitée à la machine locale | `test_console_sans_jeton_ne_repond_qu_a_cette_machine` · ce lot |
| 8 | P1 | R3 | `GET /api/pulse/etat` **sans authentification** : récit de la démonstration (noms, identifiants d'activation) | route réservée à la console | `test_console_exige…` · ce lot |
| 9 | P1 | R3 | Le graphe d'évolution d'une activation **nommait la personne qui avait décliné** (aux autres participants et à la console) | ne montre que les personnes engagées | `test_qui_a_decline_n_apparait…` (mutation) ; banc : 0 fuite / 754 écrans · 153733d |
| 10 | P1 | R3 | Notes privées **envoyées au fournisseur externe** par défaut | locales par défaut ; `APERTUS_NOTES_PRIVEES=1` pour les envoyer, tracé | `test_note_privee_ne_quitte_pas…` · 684ee51 |
| 11 | P1 | R3 | Identités **dans les textes libres** (présentation, offres) transmises au moteur et au modèle | `Coffre.nettoyer` : courriels, téléphones, URL, noms, mots de l'organisation | `test_injection_dans_un_profil…`, `test_le_moteur_ne_voit_aucune_identite` · d563def |
| 12 | P1 | R3 | Clé d'organisation = **empreinte non salée du nom** : réversible par dictionnaire des entreprises | clé HMAC du secret du coffre (égalité préservée) | `test_cle_d_organisation_non_devinable…` · ce lot |
| 13 | P1 | R3 | `demander` listait des opportunités que le membre **n'a pas le droit de voir** | filtrées par la politique | `test_club_pulse.py` · d563def |
| 14 | P1 | R4 | `except Exception` autour du fournisseur : **un bogue de notre code passait pour une panne d'Apertus** | seul `ErreurFournisseur` est rattrapé | `test_un_bogue_de_notre_code…` · 684ee51 |
| 15 | P1 | R4 | Nouvel essai **non borné**, pas de disjoncteur | 3 tentatives, recul + gigue, disjoncteur 60 s | `test_delai_depasse…`, `test_disjoncteur…` · 684ee51 |
| 16 | P1 | R5 | `route()` appelait l'écran **sans `await`** : panne serveur ou réseau → écran vide, sans message ; réponse lente d'un écran quitté affichée par-dessus | générations, annulation, délai 15 s, écran d'erreur avec référence | bout en bout `test_application_face_aux_pannes_reseau` (mutation) · acd117c |
| 17 | P2 | R1 | Relire une opportunité **devenue activation** → 409 (cause d'un test intermittent) | lecture ≠ action : 200 + lien vers l'activation | `test_double_activation…` (étendu), 6 exécutions consécutives · bff9197 |
| 18 | P2 | R4 | Chaque **lecture** des sollicitations rappelait le modèle et écrivait dans le journal (coût, GET non idempotent) | message rédigé une fois par sollicitation | `test_relire_ses_sollicitations…` (mutation) · 7dbc4db |
| 19 | P2 | R3 | Identifiant d'appel IA = **empreinte du message** : qui lit les journaux pouvait confirmer une supposition sur une note courte | compteur sans lien avec le contenu | `test_identifiant_d_appel_ia…` · ce lot |
| 20 | P2 | R2 | Pas d'en-têtes de sécurité, pas de CSP, corps illimités | CSP par empreintes (sans `unsafe-inline`/`unsafe-eval` pour les scripts), nosniff, no-referrer, 413 à 64 Kio | `test_observabilite.py` · 6aa6f97 |
| 21 | P2 | R5 | Aucune corrélation des journaux, messages d'exception journalisés | identifiant de requête, JSON à champs fermés, type + pile sans message | `test_les_journaux_ne_contiennent…` · 6aa6f97 |
| 22 | P2 | R2 | Jeton de session **dans l'adresse** (console → iframe) | retiré à l'arrivée ; no-referrer | bout en bout · acd117c |
| 23 | P2 | R5 | Dépendances non figées, facultatives mêlées à l'exécution ; CI sans mypy sur `intelligence/` ni bout en bout Club Pulse | `constraints.txt` (environnement vierge testé), fichiers séparés, CI complète, `pip-audit` | `make quality-check` sur clone + environnement neufs : vert en 3 min · 4fe344e |
| 24 | P2 | R5 | Les évaluations **réécrivaient des fichiers publiés** (chronométrages) à chaque exécution | `--verifier` : contrôle sans écriture | CI · 4fe344e |
| 25 | P2 | R1 | Motifs de la mémoire relus **une fois par demande** pendant l'analyse | une lecture par analyse | empreintes identiques 150/1000/5000, −13 % à 5000 · b836f55 |
| 26 | P3 | R5 | Fichier de couverture binaire commité par erreur | retiré, ignoré | .gitignore |

## Constats différés (avec raison)

| # | Grav. | Constat | Pourquoi pas maintenant | Ce qu'il faudrait |
|---|---|---|---|---|
| D1 | P2 | Codes d'invitation de **24 bits**, réutilisables, sans expiration. Avec 10 essais/min/adresse et 150 membres, une adresse a ≈ 13 % de chances par jour de tomber sur *un* membre | démonstration : codes lus dans la console ; le vrai accès passera par le système du Club | codes à usage unique, ≥ 40 bits, expirant ; ou SSO du Club ; limiteur au proxy |
| D2 | P2 | Pas de **révocation** de session (déconnexion côté client, expiration 12 h) | pas d'état serveur voulu pour la démo ; un compte effacé est refusé immédiatement | liste de révocation ou sessions serveur |
| D3 | P2 | Notes, préférences, coffre et sessions **en mémoire** du processus | démonstration rejouable ; aucune donnée réelle | magasins séparés et chiffrés (ADR 0002, 0005) |
| D4 | P2 | **Un seul processus** (verrou en mémoire, SQLite local, limiteur local) | le Club visé compte ~160 représentants | PostgreSQL, unicité `(activation, étape, membre)`, limiteur partagé |
| D5 | P2 | Événements **sans numéro de schéma** | aucun stockage durable de production | champ `v` + « upcasters » |
| D6 | P2 | Analyse **plus que linéaire** au-delà de 1 000 membres (≈ 4,5 s à 5 000) | ≈ 5 ms à 150 membres ; hors du besoin | analyse incrémentale par membre modifié |
| D7 | P3 | Bibliothèques de domaine historiques dans `app/` à côté de HTTP | déplacement mécanique qui casserait le prototype précédent encore servi | paquet `domaine/` ; en attendant, règle vérifiée par `test_architecture.py` |
| D8 | P3 | Front sans typage, deux gros fichiers HTML ; styles en ligne permis par la CSP | aucune chaîne de construction voulue (ADR 0008) | TypeScript + composants |
| D9 | P3 | Une capacité **unique** dans le Club identifie de fait la personne qui l'offre | les capacités sont « découvrables » par choix du membre (portée modifiable) | seuil k sur les capacités affichées aux non-engagés |
| D10 | P3 | Les règles ne comprennent pas « cybersecurity » (anglais) | ne pas corriger sur un cas d'évaluation ; c'est la valeur attendue d'Apertus | mesurer Apertus (`eval/eval_apertus.py`) |
| D11 | P3 | `assert` pour réduire un type dans `activer_compte` | impossible par construction (identifiant issu du coffre) | exception typée |

## Ce que les relecteurs n'ont PAS trouvé à redire (et pourquoi c'est crédible)

- **Moteur de décision** : 25 marches aléatoires × 40 gestes, invariants vérifiés après chaque pas ; replanification
  complète et juste face à un oracle par force brute sur 240 refus ; pièges : 0/180 proposés (références naïves :
  160/180 et 10/180). Données synthétiques : cela prouve le respect des règles, pas la pertinence humaine.
- **Frontière IA** : 19 cas de panne, de sortie corrompue ou malveillante ; la maquette respecte le même contrat que le
  vrai client ; aucune sortie refusée n'est comptée comme succès (le banc Apertus le teste).
- **Reproductibilité** : clone neuf + environnement neuf → `make quality-check` vert ; benchmarks rejoués à l'octet en CI.

## Méthode (pour refaire la revue)

1. Lire chaque module avec la question du relecteur ; écrire le constat AVANT le correctif.
2. Écrire le test qui échoue ; corriger ; vérifier que le test échoue sur l'ancien code (mutation) quand c'est possible.
3. `make quality-check` ; puis rejouer les bancs (`python -m eval.benchmark_pulse`) : deux des P1 ci-dessus (n° 9) et
   un défaut de l'oracle ont été trouvés par le banc, pas par la lecture.
