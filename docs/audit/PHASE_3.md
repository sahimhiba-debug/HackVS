# Phase 3 — IA derrière l'adaptateur, QR juré, ouverture : compte rendu de sortie

> Branche `claude/modest-bohr-xvk53n`, de `bd27538` (re-consentement, avant la Phase 3) à ce commit. Chemins relatifs à
> `prototype/`. **F** = fait vérifié par une commande ou un test · **H** = jugement.
> Critère de sortie : **parité IA ON/OFF verte en CI, non vacueuse**. Plus vos reports : mutation réellement déclenchée
> et verte sur GitHub, E2E hermétiques + mode salle, cache → E2E, budget de nœuds, action de l'animation sur l'état
> incertain, sonde Public AI, statuts véridiques, rejeu, canari sur les PROMPTS, injections, QR juré, artefacts.

## 1. Verdict

**Critère de sortie atteint (F)** — `tests/test_parite_ia.py`, dans la suite de la CI :
- le même parcours du registre (réponse par EXTRACT, récit NARRATE, retrait, recomposition, seconde réponse, récit),
  joué IA **allumée** (modèle scripté : pas de réseau en CI) et IA **éteinte**, aboutit au **même état métier** : tous
  les faits du journal hors traces d'appels IA, la projection entière, les reçus (identifiants d'offres ramenés à leur
  rang, car ils dépendent de la position dans le journal) ;
- **non vacueuse** : la vérification ÉCHOUE (« parité vacueuse ») si aucune sortie du modèle n'a été ACCEPTÉE et
  RETENUE ; ici, les attributs des deux membres viennent du modèle. Un méta-test le prouve (modèle dont toutes les
  sorties sont rejetées : états égaux, vérification en échec) ; contre-épreuve à la main : un membre qui tape 16 au
  lieu de 14 casse la parité.

**Ce qui n'est PAS prouvé (F)** : aucun appel réel à Apertus / Public AI. La sonde existe et tourne avec ou sans clé ;
avec votre clé, elle a rendu **UNKNOWN** parce que la politique réseau de cette session refuse `api.publicai.co`
(proxy : 403). Les verdicts réels (json_schema, tools, non-thinking) attendent un environnement qui autorise l'hôte.

## 2. Commits (un sujet chacun ; chaque correctif a un test rouge d'abord)

| Commit | Nature | Rouge sur l'ancien code (pour la bonne raison) / contre-épreuve |
|---|---|---|
| `41d763d` test(e2e) | Chromium ne résout que 127.0.0.1/localhost ; toute requête externe fait échouer le test ; job CI « salle » (espace réseau vide, IA OFF, tous deux PROUVÉS) | sans la règle de résolution, `example.org` se chargeait réellement ; sans la surveillance, la tentative passait inaperçue |
| `f8352d9` test(cache) | l'invalidation vient de l'ÉCRITURE dans le journal (même hors Club Pulse) ; l'E2E exige une lecture de l'Établi APRÈS le retrait | clé de cache sans la longueur du journal → rouge |
| `f81ad37` test(budget) | le monde de démo reste sous le budget : pic mesuré **4 nœuds** / 20 000 | — (mesure) |
| `1e13209` fix(registre) | une capacité dont la recherche est coupée est MONTRÉE « état incertain », jamais retirée de l'Établi | 5 rouges : la capacité **disparaissait** de l'écran (trouvé en écrivant le test « budget atteint ») |
| `4c5accc`, `e3e333b` ci(mutation) | le workflow se déclenche vraiment ; concurrence avec annulation ; non bloquant ; jamais sur la machine de démo | 0 exécution avant (`tags` sans `branches`) |
| `5ec2e4e`, `c0557c2` feat/docs(sonde) | sonde Public AI, avec ou sans clé ; rapport brut | — |
| `6f89b4b` feat(registre) | « Attend une décision » est une FILE : relancer (budget élevé) ou acquitter | 6 rouges (ni actions, ni méthodes, ni réglage, routes 404) |
| `9c731fe` test(capacites) | 6 survivants réels tués (reçus, retrait) | chaque mutation appliquée à la main : les 6 échouent |
| `458edd0` fix(recus) | un reçu nomme la pièce telle que CONSENTIE | rouge : le reçu était réécrit avec un libellé postérieur (trouvé par mutation) |
| `051d455` fix(ia) | un appel IA est un fait OBSERVÉ, jamais « SIMULÉ », et dit ce qui a produit la sortie | rouge : tout appel était journalisé SIMULE, même accepté |
| `9401cb8` feat(ia) | EXTRACT / NORMALIZE / NARRATE, 1 nouvel essai, forme déterministe, rejeu sans modèle, interrupteur | canari : sans le filtre côté prompt, le chemin brut laisse passer noms, courriels, organisations |
| `0cae339` test(ia) | parité ON/OFF non vacueuse ; interrupteur et statuts à l'écran | méta-test de vacuité ; contre-épreuve 14 → 16 |
| `47b632d` feat(jure) | QR juré : expiration, nonce unique, limitation par code et par session | — (fonctionnalité ; 8 tests + E2E) |
| `a03bfa6` test(mutation) | campagne de fin de phase, liste classée | — |
| *(ce commit)* docs + artefacts | vidéo et captures réenregistrées ; DEMO_SCRIPT, PREUVES, REVUE_JURY, TODO-DEMO ; ce compte rendu | — |

## 3. Ce qui existe maintenant (F)

**Les rôles du modèle (`intelligence/roles_ia.py`, prompts `*_v1.md`)** — il PROPOSE, le code DÉCIDE :
- **EXTRACT** (`POST /moi/asks/{id}/proposition`) : le texte du membre → les attributs de SA pièce ; chaque valeur doit
  figurer dans le texte ; tout autre champ (consentement, statut, membre…) fait rejeter la sortie. Rien n'est déclaré
  ni consenti : le membre confirme par la réponse ordinaire.
- **NORMALIZE** : un concept du vocabulaire + un extrait mot pour mot du texte ; repli : les règles de la taxonomie.
- **NARRATE** (`POST /console/capacites/{id}/recit`) : des faits F1…Fn tirés de la carte en rôles ; chaque phrase cite
  des faits existants, aucun nombre ni état absent des faits cités, aucune personne ; sinon le gabarit des faits.
- **Chaîne commune** (`Intelligence._executer`, tâches rejouables) : (1) un appel ACCEPTÉ déjà journalisé pour la même
  entrée est **rejoué** sans rappeler le modèle, même hors ligne (clé : HMAC du secret du processus — une empreinte
  simple permettait de confirmer une supposition sur un texte court) ; (2) sinon le modèle, et **un** nouvel essai si
  la sortie est rejetée (la raison lui est dite, jamais la sortie d'un autre) ; (3) sinon la forme déterministe.
- **Statuts véridiques** : `MODEL_CALLED` · `CACHE_REPLAY` (avec la trace rejouée) · `FALLBACK_FORM` (avec la raison :
  aucun modèle, panne, sortie rejetée deux fois, IA éteinte). Le journal marque l'appel **OBSERVE**, jamais SIMULE.
- **Interrupteur visible** : Établi, « IA : allumée — modèle « X » » / « aucun modèle configuré — forme déterministe » /
  « éteinte » ; éteinte → forme déterministe partout, jamais un rejeu. Chaque résultat affiche sa phrase de statut.

**Canaris (`tests/test_canaris_prompts.py`)** sur le corpus des PROMPTS réellement envoyés : aucune identité du coffre
— 150 membres qui écrivent chacun leur propre nom, leur organisation, leur courriel, leur téléphone et le nom d'un autre —
par le parcours complet ET par les rôles appelés bruts (le filtre côté prompt suffit seul) ; aucun pseudonyme ;
injections **FR / DE / suisse allemand** : la sortie qui obéit est rejetée, l'état ne bouge pas, le texte voyage comme
DONNÉE JSON ; même une sortie conforme n'est qu'une proposition ; le modèle n'écrit que la trace de son appel.

**QR juré** (`intelligence/jure.py`) : passe `nonce.expiration.personnage.HMAC` pour un personnage FICTIF (Markus,
absent de la scène) ; 15 min ; nonce tiré au hasard et **consommé** à la première activation (rescanné : 409) ; falsifié,
expiré, ou d'un autre processus : 401 ; session qui **meurt avec le passe** ; activation journalisée (`PASSE_JURE`,
attribuable au jury) ; limitation **par code** (5 essais/min) et **par session de juré** (90 requêtes/min), **jamais par
IP** ; QR produit localement (data: URI). Établi « QR juré » ; téléphone avec bandeau permanent, passe retiré de l'adresse.

**Ouverture de phase** : E2E hermétiques + mode salle (CI) ; cache invalidé par l'écriture ; budget mesuré et état
« budget atteint » affiché ; file de l'animation (relancer / acquitter, journalisés, rejouables) ; sonde Public AI.

## 4. Qualité (F)

| Contrôle | Résultat |
|---|---|
| `pytest` (hors E2E) | **1 198 passed** (1 128 avant la Phase 3) |
| E2E Chromium hermétiques | **12/12** ; **mode salle** (espace réseau vide, IA OFF) **12/12** en local et en CI (job `salle`) |
| Parité IA ON/OFF | verte, non vacueuse (§ 1) |
| ruff · mypy · secrets | propres · 78 fichiers sans erreur · aucun secret (la clé Public AI n'a été passée que dans l'environnement d'une commande ; 0 occurrence dans le rapport de sonde) |
| `make eval` · `reproduire_sprint` | vert · résultats publiés identiques à l'octet |
| Registre des affirmations du pitch | vérifié |
| Mutation `capacites.py` (locale) | **1 197 / 1 299 tués (92,1 %)**, 102 survivants, **0 non classé** |
| Mutation sur GitHub | déclenchée pour la première fois (runs #1 à #4) ; #1 et #2 annulés à la main (code dépassé, antérieurs à `cancel-in-progress`) ; #3 annulé automatiquement par #4 ; **#4 (ce code) en cours au moment d'écrire** — une campagne complète prend 1 à 2 h sur un exécuteur GitHub |

Campagne de mutation de la Phase 3, pas à pas : 1 238 mutants à l'ouverture, 27 non classés → 16 tués en ajoutant
`test_reconsentement.py` et `test_budget_noeuds.py` à la sélection (ils n'y étaient pas) → 6 tués par des tests écrits
pour eux → 1 corrigé dans le code (le reçu) → 4 équivalents déjà connus (ligne renommée) ; puis, après les actions de
l'animation, 7 nouveaux survivants, tous équivalents et classés (détail dans le commit `a03bfa6`).

## 5. Trouvé en chemin

- **Disparition silencieuse** : budget atteint → la capacité n'avait plus de statut → la vue la filtrait → elle
  disparaissait de l'Établi. C'est exactement ce que le test « budget atteint, affiché » devait attraper.
- **Workflow de mutation jamais exécuté** (0 run) : `push: tags:` sans `branches:`.
- **« SIMULE » sur des appels réels** : chaque appel IA journalisé comme simulé, même quand un modèle avait répondu.
- **Reçu réécrit** : le libellé courant du patron remplaçait celui qui avait été consenti (trouvé par mutation).
- **Deux fichiers de tests hors de la sélection de mutmut** : 16 survivants n'étaient que cela.
- **Hôte Public AI refusé** par la politique réseau de la session (proxy 403) — la sonde le dit (UNKNOWN), sans deviner.

## 6. Non fait / limites

- **Aucun appel réel au modèle** (§ 1). Pour mesurer : autoriser `api.publicai.co` dans les réglages réseau de
  l'environnement, fournir la clé en variable `APERTUS_API_KEY`, puis `make sonde-ia` ; le rapport brut s'écrit dans
  `docs/audit/probe_publicai.md`. La clé partagée dans la conversation doit être révoquée (vous l'avez prévu).
- **Parité en CI avec un modèle SCRIPTÉ** : elle prouve la mécanique (validation, rejeu, repli, égalité d'état), pas
  la qualité d'un vrai modèle. Avec une clé et le réseau, le même test peut être joué contre Apertus.
- **Rejeu entre redémarrages** : la clé de rejeu dépend du secret du processus — fixer `HACKVS_SECRET` pour rejouer
  les enregistrements après un redémarrage.
- **`/api/pulse/acces`** (codes d'invitation des membres) reste limité **par IP** (10/min) : hors du périmètre du QR
  juré ; dans une salle, 10 activations par minute au plus pour tout le public. À revoir si plus de membres scannent.
- **`competition/*`** (dossier de pitch et sa vidéo) décrit le produit d'AVANT le pivot : le réécrire est un choix de
  récit, pas une régénération — `TODO-DEMO.md`, section « reste à faire ». Ne pas le présenter tel quel.
- **Synthèse organisateur agrégée (k ≥ 5, derrière un drapeau)** du cahier B6 : non construite.
