# Passage à Codex — Club Pulse, pivot « banc d'essai partagé »

> Auto-évaluation de l'équipe de développement (Claude) : **rien ici n'est une validation indépendante.**
> Statut proposé : **PRÊT POUR AUDIT EXTERNE**, avec les limites du § 16 (dont : Apertus réel non testé, aucun
> utilisateur réel, état des comptes en mémoire). Branche `claude/modest-bohr-xvk53n`.

## 1. Verdict sur l'état initial
Détail : `ETAT_INITIAL.md`. En bref : fondations solides (journal d'événements transactionnel, sessions signées, coffre,
erreurs typées, frontière IA, protections HTTP, CI), mais un produit **trop large** (scan de tout le réseau, fil
d'opportunités générées, tour de contrôle) et **sans** les objets de la direction demandée : offre volontaire,
protocole versionné, accord lié à une portée et une version, observation contestable, droit de réutilisation.

## 2. Scénario retenu et justification
**Banc d'essai partagé**, scénario **illustratif** (aucune demande réelle d'exposant dans nos documents) : Sophie veut
savoir si sa nouvelle étiquette est comprise en 10 s à 1 m ; Markus a offert 15 minutes de regard neuf ; Pauline un
présentoir éclairé. Retenu parce qu'il se construit sur les primitives existantes, qu'il comporte un objet physique,
un geste réel, une perturbation naturelle (« je n'ai plus que 5 minutes ») et un résultat qui peut être négatif.
Plan B « le bon retour » : non construit (le banc d'essai a tenu).

## 3. Périmètre final
Trois surfaces membre — **Mes actions**, **Proposer un essai / page d'un essai**, **Souvenirs et accords** — et une
**console légère** (essais bloqués, accords manquants, contributions attendues, observations contestées, offres
expirées, annulation manuelle, gestes joués marqués). Mobile d'abord ; ni notifications ni hors ligne (volontairement).

## 4. Retiré du parcours visible (code conservé, non lié)
Fil « Pouls » d'opportunités, scan du réseau et ses phases, tour de contrôle avec indicateurs du réseau, graphe
avant/après, démonstration guidée en 10 étapes, onglets Activations / Événements / Mémoire, onboarding par capacités.
Leurs routes API (`/api/pulse/moi/pouls`, `…/opportunites/*`, `…/activations/*`, `/console` JSON, `/console/scan`) restent
servies, **protégées** (sessions, console) et testées ; elles ne sont plus appelées par l'interface. L'ancien prototype
« Le Fil du Club » (`/`, `/demo/stage`, `/decision`…) reste servi : autres données, autres identités simulées, il ne
partage ni sessions ni données avec la tranche. À retirer si l'audit le juge risqué.

## 5. Architecture finale (courte)
```
web/pulse/app.html, console.html  ──HTTP JSON──►  app/essai_api.py (adaptateur mince, branché sur app/pulse_api.py :
                                                   mêmes sessions, même verrou par monde, mêmes erreurs typées)
                                                        │
                                   intelligence/club_pulse.py (service : état du monde, préparation IA, clock)
                                   intelligence/vues_essai.py (projections par personne : qui voit quoi)
                                   intelligence/essai.py (domaine : offres, protocole, accords, adaptation, observation)
                                   intelligence/ia.py (Intelligence.structurer_essai : Apertus | formulaire)
                                                        │
                                   plateforme/memoire.py (journal SQLite en ajout seul, transactions, rejeu)
```
Monolithe modulaire, stockage existant, aucune nouvelle dépendance. Direction des dépendances vérifiée par
`tests/test_architecture.py`.

## 6. Fichiers importants (pivot)
| Fichier | Rôle |
|---|---|
| `prototype/intelligence/essai.py` | domaine du banc d'essai (nouveau) |
| `prototype/intelligence/vues_essai.py` | vues par personne et console (nouveau) |
| `prototype/app/essai_api.py` | routes HTTP (nouveau) |
| `prototype/intelligence/club_pulse.py` | branchement du banc, `preparer_essai`, `creer_essai`, horloge |
| `prototype/intelligence/ia.py`, `prompts/structurer_essai_v1.md` | tâche IA « structurer un essai » + secours formulaire |
| `prototype/intelligence/demo.py` | offres préparées (fictives) à chaque nouvelle démonstration |
| `prototype/intelligence/reglages.py` | `HACKVS_ESSAIS_DB` |
| `prototype/web/pulse/app.html`, `console.html` | interfaces réécrites sur la tranche |
| `prototype/tests/test_essai*.py`, `test_e2e_pulse.py` | 17 + 16 + 10 tests, 4 de bout en bout |

## 7. Invariants et points de contrôle
Voir `ACCEPTANCE_MATRIX.md` § B (I1–I10). Points de contrôle dans le code : `Banc._transition` (table `TRANSITIONS`),
`Banc.couverture` (un accord couvre-t-il ENCORE ce qui est demandé ?), `Banc.lancer` (moment d'engagement),
`Banc.decider` (version vue, capacité, refus), `Banc.niveau_partage` (réutilisation).

## 8. Accords et changements de version
- Un accord = `ACCORD{essai, version, accepte, empreinte, portee}` ; l'empreinte est celle de la **portée de la personne**
  (`essai.portee`) : pour un contributeur, la question, l'objet, le critère, l'échéance, SES gestes (nature, geste,
  durée, offre) et ce qui sera partagé ; pour le porteur, tout sauf le « pourquoi ».
- Un accord couvre la version courante **si et seulement si** l'empreinte est identique, qu'il n'a pas été retiré et
  que l'offre couvre encore le geste (active, durée, date, capacité). Sinon il est « à redonner » (portée changée) ou
  « perdu » (refus, retrait, offre qui ne couvre plus) — le second déclenche une adaptation.
- Modification cosmétique (le « pourquoi ») : rien n'est redemandé. Critère changé : tous les contributeurs.
  Geste de Markus raccourci : Markus seulement. Remplacement : la nouvelle personne ; l'accord de l'ancienne ne la suit pas.
- Chaque commande porte la version lue par l'humain ; version différente → 409.

## 9. Frontière des données envoyées au modèle
Seule la **formulation du porteur** (qu'il rédige pour la rendre proposable), nettoyée des noms, courriels, téléphones
et organisations connus du coffre (`nettoyer`, défense complémentaire). Jamais : notes privées (traitées localement,
sauf `APERTUS_NOTES_PRIVEES=1`, et jamais dans le banc), offres des autres, identités, accords, observations. Le schéma
de sortie ne contient ni personne, ni accord, ni disponibilité, ni résultat ; toute sortie est validée (natures,
bornes, longueur, identifiants, données personnelles) ou rejetée au profit du formulaire. Tests : SEC
`test_secret_temoin…`, `test_la_formulation_envoyee…`, `test_formulation_hostile…`.

## 10. État exact d'Apertus et du secours
| Élément | État |
|---|---|
| Client Apertus (HTTP compatible OpenAI, délais, 3 essais bornés, disjoncteur, sortie contrainte puis repli sans schéma) | implémenté ; testé contre un **double HTTP** (`tests/test_frontiere_ia.py`) — ce n'est PAS un test du fournisseur réel |
| Test d'intégration réel | **NON EFFECTUÉ** : aucune variable `APERTUS_*` dans l'environnement ; aucun compte créé, aucune dépense |
| Banc `eval/eval_apertus.py` | prêt ; colonne Apertus « NON EXÉCUTÉ » (`eval/resultats_apertus.md`) |
| Secours | « formulaire » : texte recopié, objet reconnu dans une liste courte, aucun geste proposé ; mode affiché sur le brouillon ; jamais « Apertus » sans appel réussi |
Pour l'exécuter : `APERTUS_BASE_URL=… APERTUS_API_KEY=… APERTUS_MODEL=… python -m eval.eval_apertus` (la clé ne doit
apparaître ni dans une commande partagée, ni dans un rapport).

## 11. Authentification et droits (état réel)
- Accès : code d'invitation (HMAC-SHA256, 6 caractères, **réutilisable**, sans expiration — limite) → jeton
  `pid.expiration.HMAC` (12 h), vérifié à temps constant ; un compte retiré est refusé immédiatement ; pas de révocation
  individuelle d'un jeton valide (limite).
- Pas de cookie : jeton en `sessionStorage`, envoyé en en-tête `X-Pulse-Session` ⇒ pas de mutation intersite possible
  côté membre. Console : en-tête `X-Pulse-Console` exigé ; jeton exact si `HACKVS_CONSOLE_JETON`, sinon machine locale seulement.
- Autorisation par objet dans le domaine : un essai n'existe (404) que pour les personnes à qui il a été proposé ;
  rôles porteur / contributeur / participant contrôlés par commande ; offre modifiable par son auteur seul.
- Organisations : un collègue de la même organisation n'est jamais proposé comme contributeur (clé HMAC).
- Rendu : DOM par `createTextNode` ; CSP par empreintes, sans `unsafe-inline`/`unsafe-eval` pour les scripts.
- Abus : 10 essais de code / min / adresse ; 30 préparations IA / min / membre ; corps ≤ 64 Kio.

## 12. Transactions, concurrence, effets externes
Un monde = un `RLock` : chaque requête s'exécute entière dessous ; chaque commande du banc est une transaction SQLite
(tout ou rien : test de panne au milieu d'une publication). Moment d'engagement : `Banc.lancer` (couverture revérifiée
sous le verrou). Double clic : idempotent ; accepter/refuser simultanés : un seul gagne (409) ; retrait pendant le
lancement : jamais « en cours » sans l'accord ; décision après annulation : 409. **Aucun effet externe** (pas de
courriel, pas de notification) : tout reste dans l'application ; aucune transaction n'est ouverte pendant un appel au
modèle ou une attente humaine (la préparation IA n'écrit rien). Un retrait dit ce qui était encore évitable et ce qui
est déjà reçu.

## 13. Tests exécutés et résultats (2026-09-29)
`make quality-check` : secrets ✅, ruff ✅, mypy (72 fichiers) ✅, **486 tests** ✅, **5 de bout en bout** ✅
(dont 4 du banc d'essai), évaluations et registre des affirmations ✅. Mutations : contrôle de version, partage
permissif, durée d'offre ignorée → chacune fait échouer 2 tests. Détail et commandes : `PREUVES.md`.

## 14. Tests non exécutés et raisons
- Apertus réel : aucun identifiant (voir § 10).
- Deux **vrais téléphones** sur un réseau de salle : non disponible ici (deux contextes de navigateur indépendants à la place).
- Tests avec des membres réels, mesures de temps et de corrections humaines : aucun utilisateur.
- Construction de l'image Docker : pas de démon ; remplacé par `tests/test_image.py` (fichiers de l'image, démarrage).
- Charge et plusieurs instances : hors périmètre (un processus).

## 15. Données réelles, synthétiques, simulées
| Catégorie | Contenu |
|---|---|
| Fixtures de régression | `tests/test_essai.py` (monde fixe) |
| Cas inédits de mise à l'épreuve | `tests/test_essai_cas_inedits.py` (autre objet, autres personnes : 10 cas) |
| Données terrain | **aucune** |
| Provider réel | **aucun résultat** |
| Mode de secours | `eval/resultats_apertus.md` (formulaire : objet reconnu 5/5 ; aucun geste proposé) |
| Démonstration | membres, entreprises, offres **fictifs** ; horloge **simulée** quand on l'avance ; gestes de Pauline/Léa **joués** |
| Anciens bancs | `eval/resultats_benchmark_pulse.md` (détection 160/160 situations **plantées par nous**, pièges 0/180) : jeu **auto-construit**, il mesure le respect des règles, pas un besoin ni une pertinence |

## 16. Limitations et risques connus
1. Besoin **non validé** auprès des membres ; scénario illustratif.
2. Apertus réel non testé ; le secours ne comprend pas le texte libre (il ne le prétend pas).
3. Activation des comptes, notes privées et sessions **en mémoire** : un redémarrage garde les essais
   (`HACKVS_ESSAIS_DB`) mais oblige à rouvrir les sessions (testé, dit).
4. Codes d'invitation courts, réutilisables, sans expiration ; pas de révocation de session individuelle.
5. Un processus ; verrou et limiteurs en mémoire.
6. Le porteur **déclare** l'observation ; rien ne la vérifie ; la contestation est la seule contre-mesure.
7. Correspondance offre ↔ geste : même nature + mots communs ; le porteur choisit, mais une offre de même nature
   « peu pertinente » peut être proposée.
8. Pseudonymisation ≠ anonymisation : une offre rare identifie de fait son auteur ; le nom n'est montré qu'après accord.
9. Relecture toutes les 4 s (pas de notification) ; ancien prototype encore servi (§ 4).
10. Pas de page de « mémoire du Club » consultable par tous : seule la liste « réutilisable par le Club » existe.

## 17. Lancement
```bash
make setup                         # dépendances exactes (constraints.txt)
make quality-check                 # tout
make demo                          # http://127.0.0.1:8000/console et /app (données fictives, en mémoire)
```
Variables : voir `docs/ARCHITECTURE.md` § 10 + `HACKVS_ESSAIS_DB` (fichier du journal des essais).

## 18. Reproduire le nominal et les échecs
- Nominal (navigateur, deux contextes) : `cd prototype && HACKVS_E2E_OBLIGATOIRE=1 python -m pytest -q tests/test_e2e_pulse.py -k deux_telephones`
- Refus sans alternative : `… -k refus_sans_alternative` ; pannes réseau : `… -k pannes` ; contenu hostile : `… -k hostile`
- Échecs critiques côté serveur : `python -m pytest -q tests/test_essai_securite.py tests/test_essai_cas_inedits.py`
- À la main : `DEMO_SCRIPT.md`.

## 19. Git
Branche `claude/modest-bohr-xvk53n`. Avant le pivot : `cbb6930`. Pivot : `1e0451e` (tranche), `bfaf151` (attaques),
puis le commit de ce dossier (cas inédits, ordre de l'écran, banc IA étendu, documentation). Tout est commité et poussé
au moment de la remise ; la CI GitHub Actions s'exécute sur chaque poussée (résultat à lire sur GitHub, non recopié ici).

## 20. À attaquer en priorité
1. `Banc.couverture` / `portee` : existe-t-il une modification qui change ce qu'une personne fait SANS changer son empreinte ?
2. `Banc.lancer` sous concurrence réelle (plusieurs processus : non supporté — le dire suffit-il ?).
3. `reservations` : une offre peut-elle être consommée deux fois via retrait puis réacceptation ?
4. Vues : un champ dérivé (historique, raisons, adaptation) révèle-t-il qui a décliné, ou le texte d'une observation à la console ?
5. Anciennes routes Club Pulse encore servies : faut-il les couper dans l'environnement de démonstration ?
6. Formulaire de secours : induit-il le public à croire à une compréhension du texte ?
7. Codes d'invitation réutilisables : acceptable pour une démonstration en salle ?
