# FINAL AUDIT — Club Pulse, avant le gel (01.10.2026, état : FREEZE CANDIDATE)

> Rédigé pour cinq ingénieurs seniors qui ouvriront chaque fichier. Règle suivie : aucune modification sans preuve ;
> chaque correctif a un test rouge d'abord, une contre-épreuve et son propre commit. Ce qui n'est pas mesuré est dit
> « non mesuré » ; ce qui est faux a été corrigé ou retiré. Registre des affirmations : [CLAIMS.md](CLAIMS.md).
> Constats antérieurs : [SENIOR_ENGINEERING_FINDINGS.md](SENIOR_ENGINEERING_FINDINGS.md) (F01–F40),
> [REVUE_PUBLIQUE.md](REVUE_PUBLIQUE.md) (R-01–R-15).

## 1. Executive summary

Club Pulse est un **registre vivant de ce que le Club peut faire ensemble** : une capacité (« accueillir une délégation
d'acheteurs germanophones ») n'existe que si chaque pièce (salle, minibus, interprète) est déclarée par un membre,
valable à la date et **consentie pour cette finalité**. Une IA peut seulement *proposer* ; un moteur déterministe compose
et invalide ; une personne décide. Démonstration sur un monde **fictif**, un seul processus, un journal SQLite rejouable.

Cette session de durcissement a trouvé et corrigé, chaque fois test rouge d'abord :

- **H2 — déni de service de la démo (HIGH).** Un membre, ou un juré muni d'un QR, pouvait figer l'Établi. Projection,
  avant → après :
  - 200 offres parasites : 27–31 s → 0,8 s ;
  - 100 brouillons parasites : 8,5 s → 0,8 s.

  Cause : chaque recherche relisait tout le journal.
- **H3 — faux vert de la porte de mutation (HIGH).** Démontré sur des données réelles : la porte disait « succès » après
  avoir testé 16 mutants sur 1 327.
- **R-01 — vrais téléphones (HIGH).** Ils ne pouvaient pas joindre `make demo`, et le QR juré encodait `127.0.0.1`.
- **R-02 — mémoire sans borne (MEDIUM).** Les limiteurs de débit ne l'empêchaient pas.
- **R-03 / R-04 / Phase 9 — accessibilité.** Contraste, cibles de 44 px, six champs sans nom accessible.
- **R-05 — CSP absente sur deux pages.**
- **Documentation.** Une règle de scène contradictoire, qui aurait effacé le monde restauré après un plantage. Dix-neuf
  documents historiques non marqués. Quatre claims non prouvés (D) clôturés.

**Aucun CRITICAL** n'a été trouvé (aucune fuite de données, aucun contournement d'autorisation, aucune perte d'état), malgré
un balayage automatique de chaque route et des attaques ciblées.

Ce qui reste OUVERT et doit être dit :

- la qualité d'un vrai modèle (jamais appelé) ;
- de vrais téléphones sur un vrai Wi-Fi (jamais testé) ;
- deux claims de la couverture du pitch (décision de Hiba) ;
- la dette d'architecture (F02, F06, F11) ;
- les survivants de mutation de `essai.py`, NON classés (§ 10).

## 2. Architecture

```
membre ─► TÉLÉPHONE /app (PWA sans framework) ─┐
juré ───► QR → /app?jure=… (passe 15 min) ─────┤
                                               ├─► API /api/pulse/* (FastAPI, adaptateur mince) ─► MOTEUR (intelligence/)
animation ─► CONSOLE /console, ÉTABLI /etabli ─┤      garde : Passage lecteurs/rédacteur           ├─ capacites.py   registre : patrons, composition, Ask, statuts
            (machine locale ou jeton)          │      + UN verrou par monde                        ├─ essai.py       banc d'essai : offres, essais, TRANSITIONS
écran commun /projection, régie /demo/regie ───┘      membre : session signée (HMAC)               ├─ club_pulse.py  façade : sessions, coffre, IA, effacement
                                                      console : en-tête + local/jeton              ├─ ia.py, roles_ia.py  EXTRACT / NORMALIZE / NARRATE → propositions validées
                                                                                                   └─ ÉTAT : plateforme/memoire.py — journal APPEND-ONLY (SQLite),
                                                                                                      rejoué au démarrage ; index dérivés clés sur Memoire.version()
```

- **Source de vérité.** Le journal (`Evt`, identifiant par empreinte de contenu, statut SYNTHETIQUE / DECLARE / JOUE /
  OBSERVE / SIMULE). Tout l'état en mémoire est dérivé et reconstruit par rejeu : `test_redemarrage_kill9.py` tue le
  serveur par SIGKILL et compare.
- **Concurrence.**
  - Chaque requête lit le monde courant pour toute sa durée (`Passage`).
  - Remplacer le monde (réinitialiser) attend la vidange, puis ferme l'ancien journal (F28).
  - Les commandes sont sérialisées par le verrou du monde ; les transactions sont tout-ou-rien (F27).
- **Frontières de confiance.**
  - Internet / salle → `/api/pulse/acces` et `/api/pulse/jure` : seules routes publiques, limitées par code et par
    plafond global.
  - Session membre → `/moi/*`.
  - Machine locale ou jeton → `/console/*` et `/demo/*` (la console incarne chaque membre).
  - Modèle de langage → `intelligence/ia.py` : sortie non fiable, validée par schéma, faits cités, jamais une décision.
- **Ancien prototype co-résident.** 81 routes et 39 modules, **non servis** par défaut (404) ; frontière dite dans
  `docs/ANCIEN_PROTOTYPE.md`.
- **Décisions.** `docs/ADR/README.md`, statut relu contre le code (0004 remplacée). `docs/ARCHITECTURE.md` est
  partiellement périmé (F02).

## 3. Security review

| Contrôle | Résultat | Preuve |
|---|---|---|
| Chaque route servie a une garde (publique / console / membre), énumérée depuis le routeur | ✓ 73 routes API ; seules `/acces` et `/jure` publiques | `test_autorisation_balayage.py` |
| Session absente, mal formée, falsifiée, expiration repoussée, expirée bien signée, autre membre avec la même signature, compte effacé | 401 sur CHAQUE route membre | idem ; contre-épreuve : vérification d'expiration désactivée → rouge |
| Console sans en-tête / depuis une autre machine / avec une session membre | 403 partout | idem ; contre-épreuve : contrôle de localité désactivé → rouge |
| Membre A → ressources de B (offre, note, demande adressée à d'autres, consentement) | 403 / 404 | `test_autorisation_balayage.py::test_un_membre_ne_touche_jamais_les_ressources_d_un_autre` |
| Essai d'un autre : 404 uniforme (pas d'oracle d'existence) | ✓ | F36, `test_essai_inexistant_pour_etranger.py` |
| XSS : aucun `innerHTML` dans `web/pulse/` (constructeur DOM, nœuds texte) ; contenu hostile affiché comme texte | ✓ | E2E `test_contenu_hostile_affiche_comme_du_texte` |
| CSP par empreintes sur CHAQUE page HTML ; `frame-ancestors 'self'`, `object-src 'none'`, `no-referrer`, `nosniff` | ✓ (R-05 : manquait sur `/projection`, `/demo/regie`) | `test_observabilite.py` |
| Corps ≤ 64 Kio ; journaux sans contenu privé ni sortie du modèle | ✓ | `test_observabilite.py`, F33 `test_rejets_sans_contenu.py` |
| Secrets : aucun dans le dépôt ; secret ≥ 32 caractères ; console : jeton comparé en temps constant | ✓ | `make secrets` (CI) ; `intelligence/reglages.py` |
| Image Docker non-root ; dépendances exactes (`constraints.txt`) ; `pip-audit` en CI | ✓ | `Dockerfile`, job CI `dependances` |

**Limites de sécurité, dites et non corrigées** (risque accepté pour une démonstration fictive) :

- **Sessions sans état.** Jeton HMAC `pid.exp.sig` valable 12 h. « Se déconnecter » efface le jeton du téléphone ; le
  serveur ne le révoque pas, sauf effacement du compte (`coffre.actives`).
- **Pas de TLS.** En salle, les téléphones parlent au portable en HTTP : sur un point d'accès OUVERT, les jetons
  circulent en clair. Point d'accès protégé par mot de passe (WPA2) obligatoire (`DEMO_SCRIPT` § 2).
- **Proxy local.** Derrière un mandataire local qui ne transmet pas l'adresse du client, la console croirait toute
  requête locale : définir `HACKVS_CONSOLE_JETON` (`THREAT_MODEL` S3).
- **Oracle d'existence d'offre.** `PATCH /moi/offres/{oid}` répond 403 pour l'offre d'un autre, 404 pour une offre
  inexistante. Les offres sont publiques par nature (découvertes), l'identifiant fait 32 bits : risque négligeable, dit.

## 4. API review

82 routes servies (73 sous `/api/pulse`, 9 pages / ressources) ; 81 routes de l'ancien prototype NON servies (404).

| Famille | Garde | Validation | Limite | Idempotence / doublons |
|---|---|---|---|---|
| `POST /acces` | publique | code 4–12 caractères | 5/min par code + 300/min global (F09, jamais par IP) | réactivation sans effet |
| `POST /jure` | publique | jeton 10–160 caractères | 5/min par passe + 300/min global (R-02) | usage unique (`test_qr_jure.py`) |
| `/moi/*` (≈ 50) | session | Pydantic (longueurs, bornes, `Literal`), 422 sinon | écritures (offres, essais, brouillons, notes) : 30/min/membre, passe juré compris (D2, `test_plafond_ecritures.py`) ; IA : 30/min/membre ; juré : 90 req/min | réponse double → 404 ; consentement idempotent ; retrait double → 404 (`test_autorisation_balayage.py`, `test_concurrence_http.py`) |
| `/console/*`, `/demo/*`, `/etat` | en-tête + local / jeton | Pydantic | — (opérateur) | réinitialiser : rédacteur exclusif (F28) |

Erreurs typées traduites à UN endroit : 401 / 403 / 404 / 409 / 422 / 429. Toute autre exception → 500 JSON portant
l'identifiant de requête, journalisée sans contenu. Le plafond d'écritures répond 429 au même format :
`{"detail": "trop de publications en une minute : attendez un instant avant de publier de nouveau"}`.

## 5. State / concurrency review

| Scénario | Résultat | Preuve |
|---|---|---|
| 4 destinataires répondent « oui » au même instant (vrais fils, barrière) | 1 × 200, 3 × 404 ; une seule réponse au journal | `test_concurrence_http.py` (contre-épreuve sans verrou : rouge 2 fois sur 5 — probabiliste, dit) |
| Double toucher du même téléphone | [200, 404] | idem |
| Retrait pendant une réponse | jamais de 500 ; le retrait s'applique ; reçu exact | idem |
| Réinitialisation pendant une requête | aucune écriture de l'ancien monde dans le nouveau | `test_reinitialisation_atomique.py` (F28) |
| Panne au milieu d'une commande | rien d'écrit, mémoire rebâtie | `test_transaction_memoire.py` (F27) |
| Offre écrite puis annulée, numéro de séquence réutilisé par SQLite | l'index ne la sert jamais | `test_charge_offres.py::test_une_offre_annulee_ne_survit_pas_dans_l_index` (contre-épreuve : sans le compteur de génération → rouge) |
| `kill -9` ; réinitialisation puis `kill -9` | même monde ; l'ancien journal reste clos | `test_redemarrage_kill9.py` (R2) |
| Lecture figée du journal pendant une recherche | une écriture, une annulation ou un vidage force une relecture | `test_charge_offres.py::test_une_ecriture_pendant_une_lecture_figee_est_vue` |

## 6. Frontend review

- **Technique.** PWA sans framework : `web/pulse/*.html`, un `pulse.css`, des `tokens.css`. Aucune requête externe :
  polices auto-hébergées sous SIL OFL ; E2E hermétiques.
- **Robustesse.** Garde contre les réponses périmées ; états chargement / vide / erreur / hors ligne. Hors ligne, le
  téléphone dit « hors ligne : écran figé » au lieu de montrer du périmé (`test_application_face_aux_pannes_reseau`).
- **Service worker.** Il met en cache l'enveloppe, jamais les données. Il n'est PAS actif en HTTP sur le réseau local
  (contexte non sécurisé) : rien n'en dépend (vérifié, R-13).
- **Design system v1.0.** Appliqué en CSS seulement. Écarts assumés et claims des planches clôturés dans
  `DESIGN_SYSTEM.md` § 8. **Non fait** (§ 7.3, demande du HTML) : médaillons sur avatars, en-têtes téléphone rouge et
  slate, extrait de journal du Passeport.

## 7. Accessibility

Mesuré dans Chromium et figé par `test_e2e_pulse.py::test_lisible_et_touchable_au_telephone_et_sur_les_ecrans`. Le test
couvre chaque onglet du téléphone, `/etabli` et `/console`. Il exige :

- un contraste WCAG AA contre le fond effectif ;
- des cibles tactiles ≥ 44 px ;
- un nom accessible pour chaque champ et chaque bouton.

Le balayage a aussi vérifié : `lang="fr"`, un `h1` par page, aucune image sans `alt`, l'ordre au clavier, et l'anneau de
focus visible (2 px) sur chaque élément atteint par Tab. Corrigé pendant le gel : R-03 (trois contrastes des planches
sous AA), R-04 (cibles de 24–36 px), six champs nommés par leur seul placeholder. **Non vérifié** : un vrai lecteur
d'écran (VoiceOver, TalkBack) — seule l'arborescence accessible l'a été.

## 8. Performance

`make perf` (`prototype/scripts/mesurer_perf.py`) : vrai serveur uvicorn, configuration de `make demo`, requêtes
séquentielles depuis la même machine. Mesure du 01.10, 4 processeurs, **sous charge de fond** (campagne de mutation
locale, charge moyenne ≈ 3,2–4,0) : les chiffres sont donc pessimistes.

| Mesure | n | moyenne | médiane | p95 | max |
|---|---|---|---|---|---|
| Démarrage à froid (processus → premier 200) | 5 | 2 146 | 2 108 | 2 653 | 2 653 |
| Établi (registre, en cache) | 50 | 2,3 | 2,0 | 4,4 | 7,7 |
| Console : essais | 50 | 2,6 | 2,3 | 5,4 | 6,0 |
| Écran commun | 50 | 2,3 | 2,2 | 2,6 | 2,7 |
| Téléphone : demandes | 50 | 4,5 | 2,5 | 4,5 | 86,2 |
| Téléphone : mes actions | 50 | 1,9 | 1,9 | 2,1 | 2,8 |
| Téléphone : mes données | 50 | 11,4 | 10,0 | 16,4 | 24,1 |
| Page `/app` (HTML) | 50 | 2,6 | 2,8 | 3,0 | 5,1 |
| Établi après une écriture (recalcul) | 10 | 94,9 | 90,5 | 120,1 | 120,1 |
| Établi après une écriture, sous 100 offres + 100 brouillons parasites | 10 | 1 127 | 1 082 | 1 638 | 1 638 |

Durées en millisecondes. L'Établi relit toutes les 1 s, l'écran commun toutes les 0,7 s ; une lecture en cache coûte
quelques millisecondes.

**Abus mesuré (H2 puis D2).** Avant H2, 200 offres parasites coûtaient 27 à 31 s PAR projection, sous le verrou du
monde : la salle entière attendait. Après H2 : ≈ 1,1 s sous 200 parasites (ligne du tableau). Depuis D2, un membre ne
peut plus écrire que 30 fois par minute : `make perf` fait remplir leur plafond à trois membres (90 parasites) →
recalcul de l'Établi 484 ms en moyenne, 569 ms au p95 (n = 10, même machine) ; la 31e écriture d'un membre reçoit 429.

**Non mesuré** : un vrai téléphone, un vrai Wi-Fi, un modèle de langage, plusieurs heures de fonctionnement continu.

## 9. Test matrix

| Ligne de la matrice | Unitaires / HTTP | Navigateur (E2E) |
|---|---|---|
| Parcours nominal (essai, registre, action collective) | ✓ | ✓ `test_e2e_action.py`, `test_e2e_capacites.py`, `test_e2e_pulse.py` |
| Entrée fausse / manquante | ✓ 422 (Pydantic), règles métier 409 | ✓ |
| Action en double | ✓ `test_autorisation_balayage.py`, `test_concurrence_http.py` | — |
| Action non autorisée | ✓ balayage de chaque route | ✓ QR juré, console |
| Session expirée | ✓ jeton expiré bien signé → 401 | — |
| Panne réseau / hors ligne | — | ✓ `test_application_face_aux_pannes_reseau` |
| Rechargement / redémarrage | ✓ `kill -9` (vrai processus) | ✓ |
| Utilisateurs simultanés | ✓ fils + barrière | ✓ deux téléphones (deux contextes) |
| Réseau lent | **non testé** | **non testé** |
| Mobile (390×844, 412×915) / bureau (1440, 1920) | — | ✓ |
| Adresse réseau réelle / point d'accès | ✓ configuration (`test_demo_salle_telephones.py`) | vérifié à la main dans Chromium par une adresse réseau (R-01) ; **vrais téléphones : non testé** |
| QR code | ✓ URL publique encodée | ✓ usage unique |
| Hermétique / mode salle | — | ✓ toute requête externe échoue le test ; job CI `salle` (espace réseau vide, IA OFF) |

Totaux au 01.10 (clone frais au commit `40fa659`, venv neuf) : **1 268 réussis, 1 ignoré** (le test du modèle sémantique, modèle non
téléchargé), **17/17 E2E** (réseau normal et mode salle), ruff et mypy propres.

## 10. Mutation testing

| Cible | Population | Tués | Survivants | Sans test | Statut |
|---|---|---|---|---|---|
| `intelligence/capacites.py` | 1 327 | 1 229 (dont 0 timeout) | 98, **tous classés équivalents** (`mutants_survivants.txt`) | 0 (non vérifiés 0, suspects 0) | **confirmé par la CI avec la porte durcie** : campagne GitHub [#15](https://github.com/sahimhiba-debug/HackVS/actions/runs/36880815389) au commit `4233cef`, verte, 0 non classé (56 min) ; identique à la campagne locale du 01.10 |
| `intelligence/essai.py` (F37) | 3 528 | partiel : 1 921 au mutant 3 025 | 1 037 au mutant 3 025, **NON classés** | 67 | locale, en cours. Mesurée sur `essai.py` **d'avant H2** (copie figée) : les index ajoutés depuis ne sont pas dans cette population. Aucune classification de masse avant le gel (consigne). Le taux de survivants (≈ 1/3) est élevé et dit tel quel |

**Règle au gel (contre-expertise).** `PREUVES.md` et le deck ne reprennent QUE des chiffres produits par la porte durcie
(campagne GitHub #15 et suivantes, population complète affichée). Les chiffres de `essai.py` ci-dessus restent étiquetés
« avant H2, non classés » et ne vont ni dans PREUVES ni dans le deck.

**Porte de mutation (H3).** Elle ne peut plus être verte sans avoir muté. Elle échoue si mutmut échoue, si la campagne
est vide, si rien n'est tué, si la campagne est interrompue (« not checked »), ou s'il reste un survivant non classé,
un mutant « no tests » ou un mutant « suspicious » (`test_porte_mutation.py`). Démontré : l'ancienne porte disait 0 sur
une campagne où 1 310 mutants sur 1 327 n'avaient pas été vérifiés.

## 11. Claims audit

Voir [CLAIMS.md](CLAIMS.md) : 37 affirmations, chacune classée A / B / C / D. `test_docs_classees.py` vérifie que chaque
test cité existe. Claims **D** (non prouvés) :

- clôturés dans le produit : « chaîne HMAC vérifiée » (FAUX : aucune chaîne HMAC), « 1 198 événements »,
  « MODEL_CALLED · 678 ms », « contrastes validés » (FAUX, corrigé) ;
- **couverture du pitch, décision D1 de Hiba** : reformulés et désormais classe A — « Lire ne capte rien : aucune écriture
  sans geste » (balayage de CHAQUE route de lecture, journal compté) ; « Répondre : trois boutons » (E2E) ; « passe juré
  15 min, sans compte ». La durée de réponse ne sera affichée qu'après le chronométrage du rituel § 9.5 (3 mesures, la
  pire). Report sur la planche Cover : voir CLAIMS.md (modification de l'artefact partagé refusée par les permissions).

## 12. Known limitations

- **IA.** Apertus n'a jamais été appelé depuis cet environnement ; l'évaluation EXTRACT est prête et gelée, mais n'a
  pas tourné. Latence médiane du modèle : **non mesurée**.
- **Utilité.** Aucun membre réel ; toutes les données sont fictives ou synthétiques. Utilité non mesurée.
- **Démonstration.** Un seul processus, état en mémoire dérivé d'un SQLite local ; pas de mise à l'échelle horizontale.
- **Sessions.** Sans état (pas de révocation serveur à la déconnexion) ; pas de TLS en salle (§ 3).
- **Terrain.** Vrais téléphones, vrai Wi-Fi, lecteurs d'écran et réseau lent : non testés.
- **Écritures.** Plafonnées à 30 par minute et par membre, passe juré compris (D2) ; au-delà de ce plafond, le coût
  d'un recalcul reste linéaire dans le nombre total de faits (§ 8).

## 13. Technical debt intentionally left

| Dette | Classe | Pourquoi pas maintenant |
|---|---|---|
| `Banc` (`essai.py`, 1 337 lignes) — F06 | DOCUMENT | refactor massif à la veille du gel = plus de risque que de gain |
| 39 modules et 81 routes de l'ancien prototype co-résidents — F11 | DOCUMENT | non servis (404, testé) ; les retirer touche des tests et des scripts hors du produit |
| `docs/ARCHITECTURE.md` partiellement périmé — F02 | DOCUMENT | bannière posée ; § 2 du présent document tient lieu de carte à jour |
| Charges d'événements non typées (`dict[str, Any]`) — F05 | DOCUMENT | les lecteurs actuels sont testés ; typer = migration du journal |
| `creer_routeur` (219 lignes de déclarations de routes) | IGNORE | style FastAPI ; aucune logique métier (`test_l_api_club_pulse_ne_contient_pas_de_regle_metier`) |
| Survivants de mutation de `essai.py` non classés — F37 | DOCUMENT | consigne : pas de classification de masse avant le gel |
| `docs/captures/` (45 fichiers de l'ancien prototype) | DOCUMENT | servis seulement avec l'ancien prototype ; marqués dans `TODO-DEMO.md` |

## 14. Demo readiness

- **Lancement.**
  - `make demo` : journal fichier, secret stable.
  - Vrais téléphones : `make demo HOTE=0.0.0.0 URL_PUBLIQUE=http://<ip>:8000`.
  - La console reste réservée au portable (testé).
- **Secours.** Le monde revient après `kill -9` (testé) ; mode salle sans Internet (CI) ; vidéo enregistrée.
- **Correction critique de ce jour.** La règle « après un redémarrage, Nouvelle démonstration » aurait EFFACÉ le monde
  restauré. Elle est corrigée dans `DEMO_SCRIPT.md` et `TODO-DEMO.md`.
- **Rituel humain de samedi matin** (`DEMO_SCRIPT` § 9.5) :
  - `kill -9` puis vérification de la reprise ;
  - un **vrai téléphone** et un **vrai scan de QR juré** ;
  - le scénario complet chronométré, en mode salle hors ligne.

  Il reste le seul endroit où le terrain réel est vérifié.

## 15. Reproducibility

Vérifié le 01.10 depuis un **clone frais et un venv neuf** (Python 3.11.15) :

| Commande | Résultat |
|---|---|
| `make setup` | code 0 |
| `make secrets lint typecheck` | code 0 |
| `make test` | 1 268 réussis, 1 ignoré, 4 min 48 s, code 0 |
| image d'exécution : `requirements.txt` seul + `constraints.txt` | le serveur démarre et sert `/etabli`, `/app`, l'API et le QR juré |

Fait aussi :

- **Chiffres.** `make perf` (§ 8), `make mutation`, `make e2e`, `make e2e-salle`.
- **CI.** lint, types, tests, E2E en réseau normal et en mode salle, `pip-audit`, rejeu des benchmarks à l'octet
  (`git diff --exit-code eval/`).
- **Mutation.** Workflow séparé, non bloquant, porte durcie.

Dépendances externes à l'exécution : **aucune** (polices locales, QR produit localement, IA facultative).

## 16. Final risk register

| Risque | Probabilité | Impact | Atténuation | Reste |
|---|---|---|---|---|
| Le Wi-Fi ou les téléphones de la salle ne joignent pas le portable | moyenne | démo des téléphones | point d'accès du portable + `HOTE` / `URL_PUBLIQUE` ; régie à deux cadres sur un écran ; vidéo | vrais téléphones jamais testés : rituel de samedi |
| Plantage du serveur en direct | faible | moyen | `kill -9` + `make demo` restaure tout (testé) ; ne PAS réinitialiser | — |
| Un juré abuse de son passe (écritures en masse) | faible | Établi ralenti | correctif H2 ; plafond D2 : 30 écritures / min / membre (passe juré compris) ; passe de 15 min | ≈ 0,5 s par recalcul si trois membres saturent leur plafond une minute (mesuré § 8) |
| Point d'accès ouvert : jetons lisibles | faible | sessions fictives volées | point d'accès WPA2 | pas de TLS |
| Un relecteur cite un document historique comme actuel | moyenne | crédibilité | bannières + index `docs/README.md` + test | — |
| La planche Cover affiche encore l'ancienne formulation | élevée tant que non reportée | crédibilité | textes exacts dans CLAIMS.md (D1) | **report manuel sur l'artefact Design** (refusé à cette session) |
| Campagne de mutation GitHub rouge au gel | faible | preuve manquante | porte durcie ; run #15 en cours | résultat à relever |
| Mutation `essai.py` : ≈ 1/3 de survivants non classés | certaine | « tests insuffisants » sur le banc d'essai | dit tel quel (F37) | classification après le gel |

## Annexe A — changements de comportement DÉCLARÉS pendant le durcissement

Tout ce qui change ce qu'un utilisateur, un opérateur ou un développeur peut observer — même rarement.

| Changement | Avant | Après | Commit |
|---|---|---|---|
| `OffreVolontaire` est immuable (`frozen=True`) | un code qui modifiait une offre sur place passait en silence | il lève une exception (pydantic `ValidationError`) : l'index des offres partage ses instances. Aucun code du dépôt ne le faisait (recherché) | `107c6cb` |
| Plafond d'écritures (D2) | écritures illimitées | 31e écriture d'un membre dans la minute (offres, essais, brouillons, notes ; passe juré compris) → **429** « trop de publications en une minute… » | `9acaa99` |
| Plafond global sur `POST /jure` | aucun | 301e tentative de la minute → 429 | `e0f6545` |
| CSP sur `/projection` et `/demo/regie` | aucune | la même politique par empreintes que les autres pages | `e37f31e` |
| `make demo HOTE=… URL_PUBLIQUE=…` | serveur toujours sur 127.0.0.1, QR vers 127.0.0.1 | défaut inchangé ; sur demande : écoute réseau et QR vers le portable | `ab9c07a` |
| Contraste, cibles 44 px, `aria-label` | couleurs littérales des planches, boutons de 36 px, champs nommés par leur placeholder | écarts aux planches écrits dans `DESIGN_SYSTEM.md` § 8 ; rien d'autre de visible | `e67b20f`, `22bddf8` |
| Porte de mutation | verte si aucun survivant non classé n'était listé | rouge si mutmut échoue, si la campagne est vide / interrompue, ou s'il reste des mutants « no tests » / « suspicious » | `d374f75` |
| Déconnexion | côté client seulement | **inchangé, risque connu accepté** (contre-expertise) : le jeton n'est pas révoqué côté serveur avant son expiration (12 h), sauf effacement du compte | — |
| Jeton de console (`HACKVS_CONSOLE_JETON`, déploiement joignable du réseau) | la régie envoyait toujours « 1 » (403) ; l'Établi et la projection ouverts par les liens de la console (nouvel onglet `noopener`) restaient en 403 sans rien demander ; la console redemandait le jeton à chaque appel refusé | `web/pulse/jeton-console.js` : chaque écran d'animation demande le jeton aux onglets déjà déverrouillés (canal `BroadcastChannel` de la même origine), sinon à l'animatrice ; au plus deux demandes par chargement de page ; jamais dans l'URL ni en stockage durable ; la garde serveur est inchangée. **Sans jeton configuré (`make demo`) : rien ne change.** Vérifié dans un conteneur de l'image (29/29) | ce commit |

## Annexe B — levée des réserves R2, R3, R4 (contre-expertise des vagues 1–2)

Les trois réserves ont été levées le 01.10 au matin. Elles n'avaient pas été rapportées explicitement : c'est fait ici.
Toutes repassent vertes au commit de ce document.

| Réserve | Demande | Levée | Preuve |
|---|---|---|---|
| R2 | réinitialisation console → `kill -9` → relance : c'est le monde d'APRÈS la réinitialisation qui revient, et l'ancien journal reste clos | test sur un VRAI uvicorn tué par SIGKILL. Discrimine A et B par la transition AUTORISE de l'action de A et par les `DEMO_ETAPE` présents dans le fichier (les identifiants d'essai sont déterministes) | `7a2f1e8` — `test_redemarrage_kill9.py::test_reinitialisation_puis_kill_9_le_monde_rendu_est_celui_d_apres_la_reinitialisation` ; contre-épreuve : `vider` désactivé → rouge |
| R3 | un fait de RÉTABLISSEMENT journalisé quand une capacité redevient couverte | `CAPACITE_RETABLIE {finalite, roles}`, sans acteur ni offre, écrit dans la même transaction que le geste qui rétablit | `f1abce4` — `test_capacites_offre_ne_couvre_plus.py::test_r3_horaire_retabli_un_fait_de_retablissement_anonyme_par_role` et `::test_r3_une_autre_piece_retablit_la_capacite_et_c_est_journalise` |
| R4 | « Tout effacer » annonce AVANT le geste que le journal garde une trace technique | la note et la boîte de confirmation le disent avant le geste ; contre-épreuve : refuser la confirmation n'efface rien | `f58e213` — E2E `test_e2e_pulse.py::test_tout_effacer_annonce_ce_qui_reste_avant_le_geste` |
