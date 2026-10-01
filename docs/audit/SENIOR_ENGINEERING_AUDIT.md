# Audit d'ingénierie senior — Club Pulse (Phase 0 : cartographie et audit, lecture seule)

> 2026-10-01, commit `8d4c98a` (branche `claude/modest-bohr-xvk53n`). **Aucune ligne de code modifiée pour ce rapport.**
> Remplace la version du 2026-09-30 (`3faef5f`), dont les constats F01–F24 sont repris et mis à jour (§ 17).
> Chaque constat cite une commande, un fichier, une mesure ou une **expérience reproductible** (scripts jetables hors
> dépôt ; le protocole de chacune est décrit en clair pour être rejoué). Chemins relatifs à `prototype/`.
> **F** = fait vérifié (lu, mesuré ou reproduit) · **H** = jugement · **NV** = non vérifié, dit comme tel.
> `docs/audit/SENIOR_ENGINEERING_FINDINGS.md` n'est pas resynchronisé ici (consigne : ce seul fichier) : il le sera
> avec la première vague de corrections.

---

## 1. Executive summary

**Ce qui tient (F).** Le cœur est sain et plus solide que la moyenne d'un prototype : un seul journal en ajout seul,
un seul compositeur (`Banc._composer`), une projection des capacités recalculée (jamais stockée), une frontière IA
réelle (le modèle ne produit que des propositions validées par le code ; parité ON/OFF non vacueuse en CI), un
périmètre HTTP strict (69/69 routes `/api/pulse` refusent sans identifiant ; aucun IDOR trouvé au balayage), un oracle
en force brute pour le compositeur, une mutation **verte** sur le registre (run GitHub #4 : 1 197 / 1 299 tués,
102 survivants tous classés). Rejouer le journal redonne le même état métier, **0 appel au modèle** (testé, F07).

**Ce qui ne tient pas — trouvé par cet audit, reproduit (F) :**

1. **La CI de la branche est ROUGE, par mes deux derniers commits** (`762db1f`, `8d4c98a`) : le scanner de secrets
   refuse un littéral de test, et le garde « chaque E2E est obligatoire en CI » refuse le nouveau fichier E2E.
   Correctifs d'une ligne chacun, **non appliqués** (consigne). → **F25, P0**.
2. **Un consentement de finalité reste « valable » alors que l'offre consentie ne couvre plus rien.** Pauline déplace
   ses horaires : la capacité passe d'ACTIVE à « il manque une pièce » **sans aucune perte enregistrée**, et son reçu
   dit « valable, révocable ». Le contrefactuel n'est plus explicable ; l'accord d'essai, lui, fait ce contrôle. → **F26**.
3. **L'état en mémoire peut diverger du journal.** Les faits de profil sont appliqués en mémoire *avant* la validation
   de la transaction : une exception ensuite annule le journal mais pas la mémoire. → **F27**.
4. **Une réinitialisation de la console pendant une requête** mélange deux mondes dans le même fichier de journal. → **F28**.
5. **Le lancement par défaut (`make demo`, image Docker) garde le journal en mémoire et tire un secret au hasard** :
   un redémarrage perd le monde, les sessions et le rejeu IA. Les documents disent « le serveur reprend son journal ». → **F29** (+ F24).
6. **Le README — premier fichier lu — se contredit avec le code** : il déclare « NON IMPLÉMENTÉ » ce qui est livré
   (levier, critiques, retrait, Pulse, IA du registre, QR juré, Établi) et renvoie vers `/demo/stage`, qui répond 404. → **F30**.
7. **La provenance IA d'une valeur confirmée est perdue** : le champ `AI_PROPOSED_CONFIRMED` existe mais n'est jamais
   posé ; rien ne relie une offre déclarée à l'appel IA qui l'a proposée. → **F31**.

**Aucun CRITICAL.** Aucune fuite d'identité vers un modèle trouvée ; aucun contournement du consentement trouvé.
Le risque principal n'est pas la sécurité : c'est **l'écart entre ce que le système affirme et ce qu'il garantit dans
les cas limites** (F26, F27, F28, F29) et **l'écart documentation / code** (F30, F02).

---

## 2. Architecture map

### 2.1 Le modèle attendu et le dépôt réel

```text
attendu                         réel (F : graphe d'imports, lecture des points d'entrée)
UI                              web/pulse/*.html (PWA sans framework, aucune règle métier)        ✔
 ↓                               ↓ fetch + en-tête X-Pulse-Session / X-Pulse-Console
API                             app/pulse_api.py · capacites_api.py · essai_api.py (adaptateurs minces) ✔
 ↓                               ↓ au_monde(): UN verrou par monde, erreurs typées → HTTP
Application services            intelligence/club_pulse.py  ClubPulse (façade, 69 méthodes)       ≈ (voir D1, D2)
 ↓                               ↓
Domain model                    essai.Banc (1 247 l.) · capacites.Registre · roles_ia · jure        ≈ (voir D3)
 ↓                               ↓
Event journal                   plateforme/memoire.Memoire (SQLite ajout seul, id = empreinte)      ✔
 ↓                               ↓
Projection                      Registre.projeter (calculée) · Banc.etat/couverture (replis purs)   ✔ (cache : D4)
 ↓
Persistence                     SQLite (fichier SI HACKVS_ESSAIS_DB, sinon mémoire) + coffre hors journal  ✗ (D5)
```

### 2.2 Où le réel diverge (F)

| # | Divergence | Effet |
|---|---|---|
| D1 | La façade `ClubPulse` **porte de l'état** (profils, besoins, préférences, horloge en mémoire, `_appliquer`) au lieu d'être un service sans état au-dessus d'une projection | c'est l'origine de F27 (mémoire appliquée avant validation) |
| D2 | La façade relève aussi de la « Network Intelligence » de l'ancien produit (détection, découvertes, `/moi/demandes`) | deux produits dans un service (F01, F11) |
| D3 | `Banc` cumule journal d'écriture, offres, essais, compositeur, consentement de finalité, horloge (God object, F06) ; le registre **délègue** au banc l'écriture du consentement | un seul compositeur (bien) au prix d'une classe de 1 247 lignes |
| D4 | La projection est mise en cache par `(nombre d'événements, révision des profils, jour, patrons)` — une clé de **comptage**, valide seulement si le journal ne recule jamais | un `ROLLBACK` fait reculer le compte (F27) |
| D5 | « Persistence » dépend d'une variable d'environnement absente de tous les lanceurs | F29 |
| D6 | Le paquet `app` contient des adaptateurs HTTP **et** des bibliothèques de domaine historiques (`models`, `taxonomy`, `matching`) importées par `intelligence` | cycle apparent `app ↔ intelligence` au niveau paquets, gardé par `tests/test_architecture.py` |
| D7 | 39 modules de l'ancien produit chargés par `app.main`, servis derrière drapeau ; ils portent les benchmarks publiés | F11 |

### 2.3 Inventaire (F)

| Zone | Contenu | Rôle actuel |
|---|---|---|
| `intelligence/` | 24 modules (essai 1 247 l., club_pulse 784, ia 689, capacites 591, detection 521, vues_essai 506…) | domaine Club Pulse + détection héritée |
| `app/` | 24 modules (main 1 022 l., …) | HTTP Club Pulse + ancien prototype + bibliothèques historiques |
| `plateforme/` | journal, affirmations (`Statut`), optimisation, pipeline | socle ; `pipeline.py` = ancien produit |
| `adaptateurs/` | adaptateur « club » de l'ancien produit | hérité (cycle `cycle ↔ reseau`, F15) |
| `web/pulse/` | app membre, console, établi, projection, régie, sw.js | produit |
| `web/*.html`, `web/js/` | scène, soirée, scellé, présentation… | **ancien prototype** |
| `data/patrons/` | 6 patrons de capacités (fictifs) | configuration versionnée |
| `prompts/` | 9 prompts versionnés (3 du registre, 6 hérités) | IA |
| `eval/`, `experiences/` | évaluations, benchmarks, corpus EXTRACT (gelé, non exécuté) | preuves ; 3 scripts `experiences/mesure_*` atteints de nulle part |
| `scripts/` | 19 scripts (démo, vidéo, mutation, sonde, secrets…) | outillage |
| `tests/` | 87 fichiers, 586 fonctions, 1 203 cas collectés hors E2E ; 15 E2E Chromium | — |
| `competition/` | dossier d'avant le pivot, **en quarantaine** (bannière sur 59 fichiers) | historique |
| `mutants/` | copie de travail de mutmut | non suivi par git (F) |
| CI | `ci.yml` (qualité, E2E, reproductibilité, mode salle), `mutation.yml` | — |

---

## 3. Domain model

Légende des colonnes « trous » : ce qui est **représentable** par le code sans être voulu, ou non testé.

| Concept | Définition (code) | Invariants | États / transitions | Propriétaire | Persisté | Projeté | Tests | Trous |
|---|---|---|---|---|---|---|---|---|
| **Member** | `Profil` (pseudonymisé) + `Personne` du coffre | le moteur ne voit que `MEMBRE-NNN` et une clé d'organisation HMAC | actif / inactif (`coffre.actives`) ; profil versionné par `PROFIL` | `ClubPulse`, `Coffre` | profil : journal ; identité, activation : **hors journal** | `r.profils` (mémoire) | `test_etat_journalise`, canaris | activation et effacement non journalisés (F34, F35) |
| **Claim** | `capacites.Claim` bi-temporelle | jamais supprimée ; `valable(t, vu_au)` | ouverte → remplacée / fermée | `index_claims` (pur) | dérivée de `OFFRE`, `OFFRE_RETIREE`, `PROFIL` | index | `test_capacites_regles` (bornes, pureté) | `provenance` jamais renseignée (F31) |
| **Offer** | `OffreVolontaire` | auteur seul modifie/retire ; capacité ≥ réservations | active / à venir / expirée / retirée (calculé) | `Banc` | `OFFRE` (versions), `OFFRE_RETIREE` | `offres()` | `test_essai*` | `modifier_offre` ne peut remettre un champ à `None` (H, mineur) |
| **Consent (finalité)** | `ACCORD{finalite, emplacement, offre, empreinte, materiel, jusqu_au}` | une pièce retirée l'est pour toujours ; validité **recalculée** (6 motifs) | ∅ → ACCORD → RETRAIT (terminal pour cette pièce) ; re-consentement = nouvelle pièce | `Banc.consentir_finalite` / `raison_consentement` | journal | `consentements_finalite` (dernier fait par (membre, emplacement)) | `test_reconsentement`, `test_capacites_retrait` | **valable même si l'offre ne couvre plus** (F26) ; même type d'événement que l'accord d'essai (F05) |
| **Agreement (essai)** | `ACCORD{essai, version, empreinte, offres}` | lié à la portée EXACTE d'une version ; jamais déduit du silence | réponse / retrait ; nouvelle version ⇒ reconfirmation | `Banc.decider` / `_accord_donne` | journal | `couverture`, `raisons_gestes` | `test_essai*` | — |
| **Capacity** | `Instance` | ACTIVE ⇒ chaque pièce couvre ET est consentie à t | ONE_AWAY · PROPOSED · CONSENTED · ACTIVE · DEGRADED · EXTINCT · None — **dérivés**, aucune transition stockée | `Registre` | non (recalculée) | `projeter()` (cache D4) | oracle 6 000 graines, `test_capacites*` | combinaisons statut/distance non contraintes par le type (ex. `ACTIVE` + `distance=None` constructible) — seul le moteur construit |
| **Support (pièce liée)** | `Instance.liaisons[emplacement] = offre` | une personne ↔ un emplacement ; pas deux engagements qui se chevauchent | liée / manquante / critique | `_composer`, `_critiques` | non | oui | oracle, `test_capacites_hypotheses` | — |
| **Need** | `BESOIN` (ancien produit) ; `NEED` claim (intérêt du profil) | — | publié | `ClubPulse.demander` | journal | `r.besoins` (mémoire) | `test_frontiere_textes` | écrit une **interprétation du modèle** sans confirmation (F01) |
| **Opportunity** | `detection.Opportunite` (ancien produit) | — | calculée | `Detecteur` | non | `scanner()` (cache) | tests hérités | branche sans écran (F08) |
| **Projection** | `projection_capacites()`, `etat_canonique()`, `empreinte_etat()` | même journal ⇒ même empreinte | — | `ClubPulse` | non | — | `test_etat_journalise`, `test_rejeu_types_recents` | cache par comptage (D4) |
| **Outcome** | `OBSERVATION` + états `OBSERVEE` / `RESULTAT_INCONNU` | jamais inféré ; 14 j sans observation ⇒ inconnu | CONTRIBUTION_RECUE → OBSERVEE ; → RESULTAT_INCONNU → OBSERVEE (tardive) | `Banc.observer`, `echeances` | journal | `vues_essai` | `test_essai*` | ACTIVE ≠ EN_COURS ≠ Outcome : distincts (F) |
| **AICall** | `AppelIA` → `APPEL_IA` | `issue` ∈ {MODEL_CALLED, CACHE_REPLAY, FALLBACK_FORM} ; jamais d'appel au rejeu | immuable | `Intelligence._executer` | journal (sans latence) | `ia.etat()` | `test_appels_ia_statuts`, `test_parite_ia` | clé de rejeu liée au secret (F24) ; fragments de sortie dans les erreurs (F33) |
| **QR / jury session** | `PassesJure` (nonce.exp.persona.HMAC) | usage unique ; expire ; session qui meurt avec le passe ; limites par code / session | émis → consommé (409) / expiré (401) | `jure.py` | `PASSE_JURE` à l'activation ; passes en attente : mémoire | — | `test_jure*` (8 + E2E) | horloge murale dans un journal à horloge simulée (F39) |
| **Pulse** | `pulse_diff(avant, après)` par **rejeu** à deux positions | en rôles et titres seulement | apparues / éteintes / recomposées / fragiles / à une pièce | `capacites.pulse_diff`, `ClubPulse.au` | non | console | `test_pulse` | une extinction par F26 apparaît « éteinte » sans cause |
| **Validity** | `Claim.valable`, `raison_consentement`, `offre_couvre`, `EXTINCT` | recalculée à chaque lecture | — | registre / banc | — | — | `test_capacites_regles` | `jusqu_au` = jour de fenêtre : l'expiration du consentement n'est jamais observable avant EXTINCT (H, inoffensif) |
| **Revocation** | `RETRAIT{finalite}` ; `RETRAIT{essai}` | jamais une réécriture ; jamais attribuée publiquement | terminal pour la pièce | `Registre.retirer` | journal | reçus, `perdus` | `test_capacites_retrait`, `test_capacites_regles_phase3` | — |
| **Replay** | `ClubPulse.au(seq)`, `Demo(reprendre=True)` | même journal + même configuration ⇒ même état ; 0 appel IA | — | `ClubPulse` | — | — | `test_pulse`, `test_rejeu_types_recents` | F24, F27, F28 |

### 3.1 États impossibles — représentables ou atteints ?

| Exemple demandé | Verdict | Preuve |
|---|---|---|
| consentement sans claim | **empêché** : `consentir_finalite` exige une offre active de l'auteur | F : `essai.py:1168` |
| accord actif avec claim expirée | **empêché** pour l'essai et la finalité (`etat_offre` relu) | F : `raison_consentement`, `raisons_gestes` |
| capacité ACTIVE avec composant révoqué | **empêché** : ACTIVE exige `permis = consentements valables` | F : `_composer` ; oracle |
| **consentement « valable » d'une offre qui ne couvre plus** | **ATTEINT** | F26 (expérience E1) |
| outcome sans agreement | **empêché** : OBSERVATION exige CONTRIBUTION_RECUE ← EN_COURS ← AUTORISE | F : `TRANSITIONS`, `observer` |
| replay qui produit un état différent | **atteint dans deux cas limites** (échec en cours de transaction ; réinitialisation concurrente) | F27, F28 (E3, E4) |
| résultat IA accepté sans provenance | trace `APPEL_IA` toujours écrite ; **mais** la valeur confirmée n'y est pas reliée | F31 |
| capacité hypothétique affichée comme certaine | **non exposée** : `status_if` n'est appelé que par le levier et les tests ; le drapeau `hypothetique` n'est jamais sérialisé — à garder ainsi ou à sérialiser si un jour exposé | F : `grep status_if` |
| `ACCORD` portant à la fois `essai` et `finalite` | représentable (charges `dict[str, Any]`) ; jamais écrit | F05 |

---

## 4. Source-of-truth analysis

| Donnée | Créée | Modifiée | Lue | Persistée | Ailleurs ? |
|---|---|---|---|---|---|
| profil déclaré | `onboarding`, `modifier_profil` → `PROFIL` | idem (nouveau fait) | `profil()`, claims, compositeur (`membre_peut`) | journal | **copie en mémoire `r.profils`**, appliquée avant validation (F27) |
| besoin publié | `demander` → `BESOIN` | — | détection | journal | `r.besoins` (mémoire) |
| préférences de visibilité | `modifier_profil` → `PREFERENCES` | idem | `rendu`, vues | journal | `self.preferences` (mémoire) |
| horloge de démonstration | `avancer` → `HORLOGE` | — | partout (`jour`) | journal | `r.aujourd_hui` (mémoire) |
| offres | `publier_offre`, `repondre` | `modifier_offre`, `retirer_offre` | banc, claims | journal | — (relues du journal à chaque appel : F13) |
| essais, accords, livraisons, observations | `Banc` | nouveaux faits | `vues_essai` | journal | — |
| consentements de finalité | `consentir_finalite` | `RETRAIT` | registre, reçus | journal | — |
| relance / acquittement d'une recherche | `Registre.relancer/acquitter` | — | `instance()` | journal | — |
| appels IA, rédactions | `_tracer_ia`, `REDACTION` | — | rejeu IA, `en_clair` | journal | `ia.appels` (mémoire, avec latences) |
| identités, organisations, contacts | import des adhésions | `supprimer` (jamais appelé, F34) | coffre seulement | **hors journal** (voulu) | — |
| activation des comptes | `/acces` | — | `verifier_session` | **mémoire** (F35) | réinitialisée au redémarrage |
| sessions, passes juré en attente | HMAC du secret | — | dépendances HTTP | **mémoire / jeton** | meurent avec le secret |
| notes privées | `capturer` | `partager` | leur autrice | **mémoire** (voulu, dit dans « Mes données ») | perdues au redémarrage |
| interrupteur IA | console | console | `Intelligence` | **mémoire** | — |
| réglages (budgets, plafonds), patrons | environnement, `data/patrons/` | fichiers | registre | configuration | doit être identique pour rejouer (F17) |
| caches (projection, scan, état observé) | lecture | invalidés par clé de comptage | vues | mémoire | D4 |

**« Si je supprime tous les caches et reconstruis le système depuis le journal, est-ce que j'obtiens exactement le
même monde ? »** — **Oui pour l'état métier, avec cinq exceptions, dont deux non voulues** (F) :

1. *Voulu, documenté* : identités, activations, sessions, passes en attente, notes privées, interrupteur IA ne sont pas
   dans le journal (le monde reconstruit les remet à leur état de départ).
2. *Voulu, à écrire dans le contrat* : même configuration exigée (patrons, budgets, secret) — F17.
3. *Voulu, mais coûteux* : les sorties IA acceptées ne sont rejouées qu'avec le **même secret** (F24).
4. **Non voulu** : après une exception au milieu d'une transaction qui touche un profil, le processus vivant montre un
   état que le journal ne contient pas ; reconstruire redonne le monde *du journal*, différent de celui affiché (F27).
5. **Non voulu** : une écriture d'un monde réinitialisé peut atterrir dans le journal du nouveau monde (F28).

---

## 5. Event / replay analysis

| Propriété | Verdict | Preuve |
|---|---|---|
| **Déterminisme** (même journal + même config ⇒ même état) | PROUVÉ hors F27/F28 | `test_etat_journalise`, `test_pulse` (5 positions), `test_rejeu_types_recents` (types récents, contre-épreuve) |
| **Causalité** (chaque changement ⇐ un événement) | PROUVÉ pour le domaine ; **faux en mémoire** après rollback (F27) | E3 |
| **Rejouabilité** (un fait ancien a la même conséquence) | PARTIEL : les règles de validité sont recalculées avec le code **actuel** — un changement de règle change la lecture d'un vieux journal (voulu : « même version du moteur ») | F17 |
| **Idempotence** | PROUVÉ pour l'accord d'essai (double clic), le consentement de finalité (`consentir` idempotent), le retrait (`test_retrait_idempotence_et_refus`), l'insertion (`INSERT OR IGNORE` par empreinte) ; **non** pour le partage d'une note (F12, ACCEPTÉ) | tests cités |
| **Ordering** | un seul écrivain par monde (verrou) ; `seq` SQLite autoincrémenté ; aucune réordonnance possible dans un processus. Deux processus sur le même fichier : **non supporté** (dit dans le Dockerfile) | F |
| **Horloge** | domaine : **aucune** horloge murale (`grep` : 0 `date.today`/`datetime.now` dans `intelligence/`) ; horloge simulée journalisée (`HORLOGE`). Horloge murale seulement pour sessions, passes, limiteurs et latences (hors état) — mais `PASSE_JURE.jusqu_a` écrit une heure murale dans un journal à dates simulées (F39) | F |
| **Aléa / identifiants** | identifiants = empreintes déterministes (`of-`, `es-` : sha256 de (auteur, texte, position)) ; aléa seulement : secret de processus, nonce de passe, gigue de reprise réseau | F |
| **Projection** après ajout / retrait / expiration / modification / rejeu / redémarrage / reconstruction | testée pour chaque geste ; **trou** : modification des horaires d'une offre consentie (F26) | § 6.2 |

Événements : **31 types**, chaînes libres, charges `dict[str, Any]`, aucun catalogue central (F05). `ACCORD`/`RETRAIT`
portent deux sens distingués par une clé (tous les lecteurs actuels filtrent correctement, F : 24 sites lus).

---

## 6. Capacity engine analysis

### 6.1 `essai.py` est-il le moteur unique ?

**Oui (F).** Le registre n'a **aucun** algorithme propre : composition, distance 1, pièces critiques, levier, « et si »
et recomposition appellent tous `Banc.solutions` (recherche complète par retour arrière, bornée par un budget de nœuds
dit à l'écran). L'oracle en force brute (`test_capacites_oracle.py`, 6 000 mondes) compare le registre à la définition.

Formule demandée — `Capacity = supports valables + consentements + validité temporelle + provenance + contraintes` :

| Terme | Présent ? |
|---|---|
| supports valables | ✔ `offre_couvre` (nature, concept, attributs ≥ minimums, durée, échéance, plage déclarée, chevauchement, capacité restante, profil) |
| état des consentements | ✔ `consentements` par emplacement ; `perdus` en rôles — **mais incomplet** (F26) |
| validité temporelle | ✔ claims bi-temporelles ; `EXTINCT` ; `jusqu_au` |
| provenance | ✔ statut du fait (SYNTHETIQUE / DECLARE / JOUE) ; ✗ IA confirmée (F31) |
| contraintes | ✔ minimums numériques, fenêtre, une personne ↔ un emplacement |

Le système sait répondre, par capacité : pourquoi elle existe (patron + liaisons), quelles pièces, quels consentements
manquent, quelle pièce est critique (`_critiques`, contrefactuel par le compositeur), quand elle expire, ce qui se passe
si une pièce disparaît (recomposition calculée, jamais appliquée), ACTIVE / PROPOSED / … et les hypothèses
(« disponibilités déclarées, non vérifiées »). **Il ne sait pas dire pourquoi une capacité a perdu sa pièce quand la
pièce existe encore et que son consentement « vaut » (F26).**

**Confusion fait / hypothèse / proposition / capacité active (F)** : les quatre sont typés à part —
`Claim` (fait), `HypotheticalClaim` (jamais écrite, `hyp-` + auteur `HYPOTHESE-n`), sortie IA (`proposition`, jamais
écrite sans confirmation), `Instance.statut` (calculé). Une seule confusion trouvée : la **valeur proposée par l'IA puis
confirmée** devient indiscernable d'une valeur tapée (F31).

### 6.2 Matrice contrefactuelle

| Perturbation | Accord impacté | Capacité impactée | Recomposition | Cause dite | Test |
|---|---|---|---|---|---|
| retrait du consentement de finalité | ACCORD → RETRAIT ; pièce exclue pour toujours | DEGRADED ou ONE_AWAY | calculée (consentir / demander / aucune solution sûre) | « composant plus disponible » (rôle) | `test_capacites_retrait` |
| retrait de l'offre | consentement « offre retirée » | DEGRADED | oui | oui | `test_capacites_regles` (index), `raison_consentement` |
| expiration de l'offre | « offre expirée » | DEGRADED | oui | oui | indirect (oracle) — **pas de test nommé** (H : à ajouter) |
| changement des conditions (texte) | « conditions changées » | DEGRADED | oui | oui | `test_un_changement_de_conditions_invalide_le_consentement_et_degrade` |
| **changement de créneau / d'horaires de l'offre** | **aucun** : consentement « valable » | ACTIVE → **ONE_AWAY**, `perdus` vide | Ask à la catégorie | **aucune** | **aucun — F26 (E1)** |
| compétence retirée / indisponible / non sollicitable (profil) | « le membre ne peut plus » | DEGRADED | oui | oui | `test_adaptation_profil` |
| nouvelle version du patron | « la finalité a changé » | consentements à redonner | — | oui | `test_une_nouvelle_version_du_patron_ne_reprend_aucun_consentement` |
| nouvelle déclaration après retrait | nouvel accord n+1, l'ancien ne ressuscite pas | redevient ACTIVE | — | reçu n+1 | `test_reconsentement` |
| remplacement par une autre pièce | — | ACTIVE avec autres liaisons | « recomposée » au Pulse | oui | `test_recomposition_par_une_piece_qui_existe_deja…` |
| fenêtre passée | — | EXTINCT | — | « la fenêtre est passée » | `test_apres_la_fenetre_l_extinction_est_expliquee` |
| budget de recherche atteint | — | reste affichée, « recherche bornée » | relance / acquittement journalisés | oui | `test_budget_noeuds` ; acquittement trop fragile (F32) |

---

## 7. AI boundary analysis

Chaîne voulue : `TEXT → AI → PROPOSED STRUCTURE → VALIDATOR → DETERMINISTIC ENGINE → STATE`.

| Point d'entrée IA | Sortie | Validation | Repli | Écrit dans l'état ? | Verdict |
|---|---|---|---|---|---|
| `roles_ia.extraire` (EXTRACT) | attributs d'UNE pièce | champs demandés seulement, valeur présente dans le texte, bornes ; 1 nouvel essai | formulaire vide | **non** : proposition ; le membre confirme `repondre` | ✔ (provenance perdue : F31) |
| `roles_ia.normaliser` (NORMALIZE) | concept du catalogue + extrait | vocabulaire fermé, extrait mot pour mot | règles | non | ✔ |
| `roles_ia.raconter` (NARRATE) | phrases liées à des faits `F1…` | identifiants de faits existants, aucun nombre ni nom inventé | gabarit | texte d'affichage seulement (`APPEL_IA`) | ✔ |
| `ia.comprendre_demande` | `Besoin` | vocabulaire fermé, extraits | règles | **OUI : `BESOIN` écrit sans confirmation** puis détection | ✗ **F01** |
| `ia.structurer_essai`, `ia.comprendre_action` | brouillon | schéma, vocabulaire | règles | non (renvoyé au porteur) | ✔ |
| `ia.capturer_rencontre` | capture d'une note | schéma | règles | mémoire privée seulement | ✔ |
| `ia.expliquer`, `ia.rediger_sollicitation` | texte | fidélité aux faits, aucun identifiant inventé, interdits | gabarit | `REDACTION` (texte affiché, `Statut.INFERE`) ; jamais relu par une règle | ✔ |

- **IA OFF → produit fonctionnel** : PROUVÉ (`test_parite_ia.py` : même état métier IA allumée/éteinte, modèle
  scripté, non vacueux ; E2E et mode salle sans fournisseur).
- **IA ON → jamais la décision** : PROUVÉ pour le registre et l'action collective ; **faux sur `/moi/demandes`** (F01).
- **Confidentialité vers le modèle** : deux défenses indépendantes (`_net` à l'entrée du moteur, `proteger` à la sortie
  vers le modèle), canari sur 150 membres, injections FR / DE / suisse allemand sans effet sur l'état (`test_canaris_prompts`).
- **Journaux** : métadonnées seulement **sauf** les messages d'erreur de validation, qui peuvent recopier jusqu'à 200
  caractères produits par le modèle (clés inventées, concept hors vocabulaire) dans les journaux applicatifs et `APPEL_IA` (F33).
- **Statuts véridiques** : « proposé par le modèle X, vérifié par le code » / « rejoué » / « forme déterministe, sans
  IA — raison » ; jamais « simulé » (F : `vues_capacites.ia`).
- **Pourquoi un LLM ?** (question du jury) — réponse que le dépôt peut soutenir : il transforme une phrase libre (FR / DE
  / suisse allemand) en **proposition** de quantité ou de concept, et rédige des textes à partir de faits fermés. Tout
  ce qui décide est déterministe. **Non démontré** : sa qualité — l'évaluation EXTRACT est prête mais n'a jamais tourné
  (API non joignable d'ici, `docs/audit/EXTRACTION_EVAL.md`).

---

## 8. Security findings

Posture : jury hostile. Expériences E5 (sans identifiant) et E6 (IDOR) jouées sur un monde réel en processus.

| Domaine | Constat (F) |
|---|---|
| Authentification | 69/69 routes `/api/pulse` refusent sans identifiant (47 × 401, 22 × 403 console) ; `/acces`, `/jure` seules publiques, limitées. `/docs`, `/openapi.json` hors périmètre (404) sans le drapeau de l'ancien prototype |
| Sessions | HMAC + expiration ; jeton reçu par URL rangé en `sessionStorage` puis **retiré de l'adresse** ; `Referrer-Policy: no-referrer` ; journaux applicatifs : chemin sans requête ; pas de cookie ⇒ pas de CSRF ; pas de fixation possible (jeton émis par le serveur) |
| QR juré | nonce consommé sous verrou (rejeu → 409), expiration, HMAC, limites par code et par session (jamais par IP) — testé |
| IDOR (E6) | membre étranger à un essai : **aucune écriture acceptée** sur 29 routes membre à identifiant ; lectures → 404. **Oracle d'existence** : 12 commandes répondent 403 « réservé au porteur » là où la lecture répond 404 (F36) |
| Consentement | double consentement → idempotent ; ancien consentement réutilisé → impossible (pièce morte pour la finalité) ; confusion de versions → empreinte de portée ; **trou** : F26 |
| Console | en-tête + (jeton \| machine locale) ; confiance « locale » correcte tant que seul 127.0.0.1 est cru pour les en-têtes de proxy (F19) |
| Débit | `/acces` par IP (F09) ; routes membre **non limitées** hors IA (H : acceptable en démo) |
| Effacement | `Coffre.supprimer` n'est appelé **nulle part** ; et le coffre est reconstruit de l'import au démarrage (F34) |
| Données renvoyées | console : aucun identifiant d'offre ni nom dans le registre (vérifié) ; membre : reçus et « Mes données » pour soi seul |
| Dépendances | `pip-audit` en CI ; secrets : scanner en CI (qui a d'ailleurs attrapé F25) |

« Comment contourner le consentement sans casser le système ? » — chemin trouvé : **aucun pour acquérir un accord** ;
F26 est l'inverse (un accord qui *paraît* valoir alors qu'il ne sert plus) : un problème d'honnêteté de l'affichage,
pas d'accès.

---

## 9. Concurrency findings

| Scénario | Comportement (F) |
|---|---|
| deux consentements / deux acceptations / deux réponses à la même Ask | sérialisés par le verrou du monde ; la seconde relit l'état (Ask disparue → 409) — testé (P2.5) |
| double QR | nonce consommé sous verrou → le second 409 — testé |
| écriture pendant lecture / projection pendant modification | impossible dans un processus (toute la requête sous le verrou) |
| **réinitialisation de la console pendant une requête membre** (journal fichier) | l'écriture tardive de l'ancien monde **atterrit dans le journal du nouveau** ; le nouveau monde ne la voit pas en mémoire, la voit après redémarrage — **E4, F28** |
| TOCTOU authentification / exécution | la dépendance `membre()` vérifie la session dans le monde capturé à t1 ; la route s'exécute dans le monde capturé à t2 (fenêtre : une réinitialisation entre les deux) — F28 |
| deux processus / plusieurs workers | **non supporté** (dit dans le Dockerfile) : la mémoire d'un processus ne verrait pas les profils écrits par l'autre |

---

## 10. Test quality

- **Volume** : 586 fonctions de test, 1 203 cas hors E2E (**1 202 verts, 1 rouge : F25**), 15 E2E Chromium hermétiques.
- **Doublures** : aucune `MagicMock` ; 12 `monkeypatch.setattr` ; modèles scriptés (`ModeleScripte`, `Maquette`) pour
  l'IA seulement — la logique métier n'est jamais contournée (F).
- **Assertions faibles** : 5 tests sans `assert` direct ; 4 dans `test_frontiere_textes.py` vérifient seulement
  l'*absence* d'identités (passeraient si le texte était perdu : **F10 confirmé**) ; le 5e délègue à un assistant qui
  affirme (correct).
- **Oracle exhaustif** : force brute contre le registre (6 000 mondes), non-régression du compositeur (4 000).
- **Propriétés** : à graines (pas d'Hypothesis, F21) ; aucune propriété sur la *validité des consentements* sous
  modification d'offre (aurait trouvé F26).
- **Trous nommés** : modification d'horaires d'une offre consentie (F26) ; expiration d'offre consentie (test indirect) ;
  rollback avec état en mémoire (F27) ; réinitialisation concurrente (F28) ; acquittement vs faits hors monde (F32).
- **Garde-fous du dépôt qui ont marché** : le scanner de secrets et `test_ci_couverture_e2e.py` ont attrapé mes deux
  erreurs (F25) — preuve que ces garde-fous ont de la valeur.

## 11. Mutation results

- **GitHub run #4** (`a03bfa6`, 103 min) : **VERT** — 1 299 mutants, **1 197 tués (92,1 %)**, 102 survivants, **0 non
  classé** (`docs/audit/mutants_survivants.txt`). F22 se ferme.
- **Portée (F37)** : `setup.cfg` → `only_mutate=intelligence/capacites.py`. Le compositeur, la validité des
  consentements et les transitions (`essai.py`, 1 247 lignes) **ne sont pas mutés**. Ils sont exercés par les tests du
  registre, mais aucun chiffre ne dit à quel point. Le score publié ne doit pas être lu comme celui du moteur.

## 12. Performance findings (mesurées au commit `43fd20d`, rien d'optimisé)

| Opération (monde de démo, cache froid) | Médiane |
|---|---|
| `projection_capacites` (6 patrons) | 459 ms |
| vue console de l'Établi | 418 ms (≈ 0 ms cache chaud) |
| `asks_pour` | 416 ms |
| `pulse(0)` (deux rejeux) | 495 ms |

Causes (profil) : 918 recherches `_composer`, **1 087 appels `candidats`**, chacun reconstruisant toutes les offres
depuis le journal (`Banc.offres`) ; `reservations()` parcourt tous les essais pour chaque offre testée ; le levier
reprojette tout pour chaque Ask. Quadratique ; **sans effet à l'échelle de la démo** (F13). Aucune optimisation
proposée sans nouvelle mesure.

## 13. Code quality (P0 risque · P1 architecture · P2 dette · P3 cosmétique)

| Prio | Constat |
|---|---|
| P1 | `Banc` 1 247 l. (F06) ; `ClubPulse` porte de l'état (D1) |
| P1 | charges d'événements non typées, `ACCORD`/`RETRAIT` à deux sens (F05) |
| P2 | longues fabriques de routes (`creer_routeur` 186 l., `ajouter_routes` 179 l.) — closures, acceptables ; domaine : `detection._latente` 110 l. (hérité), `vues_essai.essai` 79 l. |
| P2 | `Registre.instance` modifie temporairement `BUDGET_NOEUDS` partagé (sûr seulement sous le verrou) ; garde d'hypothèse par `assert` (supprimée sous `-O`) — F38 |
| P2 | `httpx.Client` créé à chaque appel Apertus, jamais fermé (F38) |
| P2 | 13 `# type: ignore` (F14) |
| P3 | `modifier_offre` ne peut pas remettre un champ à `None` ; `.pyc` orphelins locaux (`activation`) |

Aucune logique métier trouvée dans l'UI ni dans les adaptateurs HTTP (F : lecture des trois fichiers d'API).

## 14. Documentation quality

| Document | État (F) |
|---|---|
| `README.md` | **contradictoire** : tableau « NON IMPLÉMENTÉ » obsolète (8 éléments livrés), « vidéo à régénérer » (fait), `/demo/stage` (404), moitié inférieure = ancien produit — **F30** |
| `docs/ARCHITECTURE.md`, ADR 0004 | produit d'avant le pivot ; module cité supprimé — F02 |
| `docs/` (~20 documents) | périodes mêlées, sans statut — F16 |
| `docs/audit/PHASE_*.md`, `EXTRACTION_EVAL.md` | à jour, reliés aux commits ; honnêtes sur ce qui n'a pas tourné |
| `TODO-DEMO.md` | « le serveur reprend son journal » — vrai seulement avec `HACKVS_ESSAIS_DB` (F29) |
| `competition/` | en quarantaine, bannière (OK) |

`docs/audit/ENGINEERING_READINESS.md` n'existe pas encore (livrable de la vague 6).

## 15. Demo risks (« les 90 premières secondes d'un ingénieur hostile »)

| # | Attaque probable | Ce qui se passe aujourd'hui | Preuve dispo |
|---|---|---|---|
| 1 | Consentement : « retirez-le, et montrez que la capacité tombe » | ✔ tombe, cause en rôle, reçu daté | E2E + tests |
| 2 | Confidentialité : « mettez mon nom dans la phrase » | ✔ retiré avant moteur et avant modèle | canaris |
| 3 | Révocation puis re-consentement | ✔ accord n+1, l'ancien ne ressuscite pas | `test_reconsentement` |
| 4 | Temporalité : « changez l'horaire du minibus » | ✗ **capacité « à une pièce près » sans cause, reçu « valable »** | F26 |
| 5 | Recomposition | ✔ calculée, jamais appliquée | tests |
| 6 | IA OFF | ✔ interrupteur visible, parité | `test_parite_ia` |
| 7 | IA ON | ⚠ aucune mesure réelle d'Apertus (API non joignable) | `EXTRACTION_EVAL.md` |
| 8 | Replay : « redémarrez le serveur » | ✗ **avec `make demo` : le monde est perdu** (journal en mémoire, secret aléatoire) | F29 |
| 9 | Provenance : « cette valeur, qui l'a écrite ? » | ⚠ statut DECLARE/JOUE ; l'aide de l'IA n'est pas traçable | F31 |
| 10 | Contrefactuel : « et si cette pièce disparaît ? » | ✔ pièces critiques calculées | oracle |
| — | « Montrez-moi la CI » | ✗ **rouge** sur la branche | F25 |
| — | « Ouvrez le README » | ✗ contredit l'écran | F30 |

## 16. Technical debt (connue, assumée ou à rembourser)

`Banc` God object (F06) · charges non typées (F05) · 39 modules hérités co-résidents (F11) · coût quadratique (F13) ·
cycle `cycle ↔ reseau` (F15) · `type: ignore` (F14) · mutation limitée au registre (F37) · notes / activations /
interrupteur hors journal (voulu, à documenter) · un seul processus (voulu, documenté).

---

## 17. Findings et corrections recommandées

### 17.1 Nouveaux constats (format complet)

**F25 — CI rouge : deux régressions de mes commits `762db1f` et `8d4c98a`** · Severity **HIGH** · P0
- *Evidence* : runs CI #125, #126 `failure` (job `qualite`) ; reproduit : `python scripts/verifier_secrets.py` → « SECRET
  PROBABLE · tests/test_e2e_serveur.py · trop-c… » ; `pytest tests/test_ci_couverture_e2e.py` → « absents de la CI :
  ['test_e2e_serveur.py'] ».
- *Location* : `tests/test_e2e_serveur.py:21` ; `.github/workflows/ci.yml` et `Makefile` (liste des E2E).
- *Why* : la branche est rouge ; tout ce qui suit ne peut être validé en CI.
- *Scenario* : un jury ouvre l'onglet Actions.
- *Fix* : construire le secret court sans littéral (`"x" * 10`) ; ajouter `test_e2e_serveur.py` à la liste E2E de la CI
  et du `Makefile`. Mutation run #4 : non concerné (vert).
- *Risk* : nul. *Test* : les deux gardes existants, rejoués.

**F26 — Un consentement de finalité reste « valable » quand l'offre consentie ne couvre plus la pièce** · **HIGH** · P0
- *Evidence* : expérience **E1** — Pauline répond à l'Ask (14 places, 13:30–15:00) → ACTIVE ; elle déplace ses horaires
  à 06:00–07:00 (`modifier_offre`) → instance `ONE_AWAY`, `perdus: []`, `consentements.minibus: "pièce manquante"` ;
  son reçu : `('Un minibus de 12 places ou plus', 'valable', revocable=True)`.
- *Location* : `essai.py:1203` `raison_consentement` (vérifie l'empreinte « matérielle » = texte, nature, concept,
  conditions — **pas** les plages ni les attributs) ; comparer `raisons_gestes` (accord d'essai) qui appelle `offre_couvre`.
- *Why* : le contrefactuel n'est plus explicable ; deux mécanismes de consentement « identiques » divergent ; le
  Pulse annonce une extinction sans cause ; le reçu ment par omission.
- *Scenario* : la scène « temporalité » de la démo ; ou un jury qui modifie une offre depuis le téléphone.
- *Fix* : dans `raison_consentement`, ajouter « l'offre ne couvre plus la pièce (horaire / attributs) » via
  `offre_couvre` sur le créneau de la fenêtre du patron — **décision métier à valider** : la pièce devient DEGRADED avec
  cause (« horaire changé ») au lieu d'ONE_AWAY muet. Test rouge d'abord (E1 en test).
- *Risk* : moyen (touche la validité ; à passer à l'oracle et à la mutation).

**F27 — L'état en mémoire est appliqué avant la validation de la transaction** · **MEDIUM** · P1
- *Evidence* : expérience **E3** — `modifier_profil(LEA, disponible=False)` avec une panne injectée dans
  `revoir_membre` : journal 16 → 16 (annulé), profil **en mémoire** `disponible=False`, empreinte ≠ empreinte d'avant.
- *Location* : `club_pulse.py:152` `_enregistrer` (écrit puis `_appliquer` immédiat) dans `transaction()` ;
  `memoire.py:transaction` (le rollback vide le cache du journal, pas l'état de la façade) ; clé de cache par comptage (D4).
- *Why* : « le journal est la source de vérité » devient faux après toute 500 au milieu d'une commande de profil.
- *Scenario* : un bogue futur dans `revoir_membre` ; l'écran montre un état que le redémarrage effacera.
- *Fix* : appliquer en mémoire **après** validation (file d'application vidée au commit), ou reconstruire l'état de la
  façade sur rollback (`_restaurer`). Test rouge : E3.
- *Risk* : faible à moyen.

**F28 — Réinitialisation concurrente : deux mondes dans un journal ; TOCTOU authentification / exécution** · **MEDIUM** · P1
- *Evidence* : expérience **E4** (journal fichier) — monde A, puis réinitialisation (monde B, même fichier vidé), puis
  écriture tardive de A : le journal de B passe de 16 à 17 événements (`PROFIL ['d01']`), B en mémoire ne le voit pas,
  un redémarrage le voit. Lecture : `pulse_api.py` — `membre()` et la route capturent `etat["demo"]` **séparément**.
- *Location* : `app/pulse_api.py` (`au_monde`, `membre`, `reinitialiser`, `aller`) ; `ClubPulse(neuf=True)` → `vider()`.
- *Why* : déterminisme du rejeu et cloisonnement des mondes, seulement avec `HACKVS_ESSAIS_DB` et une réinitialisation
  pendant une requête.
- *Fix* : capturer le monde une seule fois par requête (dépendance qui rend `(club, pid)`) ; prendre `remplacement`
  en lecture partagée pendant les requêtes, ou donner à chaque monde un journal neuf (fichier versionné) plutôt que
  `vider()` le même. Test : E4 en test.
- *Risk* : faible.

**F29 — Le lancement par défaut ne persiste rien** · **MEDIUM** · P1 (fusionne l'aspect démo de F24)
- *Evidence* : `Makefile:59` (`make demo`) et `Dockerfile` ne posent ni `HACKVS_ESSAIS_DB` ni `HACKVS_SECRET` ;
  `reglages.py:22` défaut `:memory:` ; `TODO-DEMO.md` : « le serveur reprend son journal ».
- *Why* : un redémarrage en salle perd le monde, les sessions, le rejeu IA.
- *Fix* : `make demo` pose un fichier de journal local et lit un secret stable hors dépôt (fichier ignoré par git) ;
  documenter. *Test* : `test_e2e_serveur` + un test de redémarrage du serveur réel.
- *Risk* : faible (configuration).

**F30 — Le README contredit le code** · **HIGH** (crédibilité) · P1
- *Evidence* : `README.md:15-23` (« NON IMPLÉMENTÉ » : levier, composants critiques, plafond d'Ask, retrait de finalité,
  Pulse, IA dans le registre, parité, QR juré, Établi, Passeport — tous présents et testés) ; « Voir en 3 minutes :
  `/demo/stage` » → 404 en configuration produit ; « vidéo à régénérer » (fait en Phase 3).
- *Fix* : réécrire l'en-tête sur l'état réel, sans marketing ; déplacer la partie « ancien prototype » vers un document
  historique. *Test* : vérification des liens et des routes citées (script existant de validation des affirmations, à étendre).
- *Risk* : nul.

**F31 — La provenance « proposé par l'IA, confirmé par le membre » n'est jamais enregistrée** · **MEDIUM** · P1
- *Evidence* : `capacites.py:133` `provenance: Literal["SELF_DECLARED", "AI_PROPOSED_CONFIRMED"]` — aucun site ne pose
  `AI_PROPOSED_CONFIRMED` (`grep`) ; `repondre` ne reçoit pas la trace de l'appel EXTRACT.
- *Why* : on ne peut pas dire au jury quelles valeurs ont été suggérées par le modèle ; la parité ON/OFF ne le
  montrerait pas non plus.
- *Fix* : la réponse confirmée porte la `trace` de la proposition (si les valeurs sont identiques à la proposition) ;
  `ASK_REPONSE` et la claim l'enregistrent. Test : réponse confirmée après EXTRACT → claim `AI_PROPOSED_CONFIRMED`.
- *Risk* : faible.

**F32 — Un acquittement tombe sur des faits qui ne changent pas le monde** · LOW · P2
- *Evidence* : expérience **E2** — acquitter la recherche bornée de `delegation_acheteurs`, puis activer un passe juré :
  `acquittee_le` → `None` (l'élément revient dans la file de l'animation).
- *Location* : `capacites.py:352` `_acquittee` (tout type autre que RELANCE/ACQUIT invalide).
- *Fix* : liste blanche des types qui changent le monde (ou ignorer `APPEL_IA`, `PASSE_JURE`, `REDACTION`, `ASK_REPONSE` non). Test : E2.

**F33 — Des fragments produits par le modèle atteignent les journaux via les messages de rejet** · LOW · P2
- *Evidence* : `roles_ia.py:32,77` (`champs non demandés : {clés du modèle}`, `concept hors vocabulaire : …[:40]`) →
  `AppelIA.erreur` → journal applicatif et `APPEL_IA` ; commentaire `ia.py:_tracer` « métadonnées seulement ».
- *Why* : l'entrée est déjà protégée (pas d'identité), mais la promesse écrite est plus forte que le code.
- *Fix* : messages de rejet sans contenu (catégorie seulement). Test : sortie piégée → aucun fragment dans les journaux.

**F34 — Le droit à l'effacement n'est pas atteignable et ne serait pas durable** · LOW · P2
- *Evidence* : `Coffre.supprimer` sans appelant (`grep`) ; le coffre est reconstruit depuis l'import à chaque démarrage.
- *Fix* : soit l'exposer (console) avec un fait d'effacement journalisé, soit retirer la promesse « droit à
  l'effacement » des docstrings. **Décision.**

**F35 — Activations de comptes hors journal** · INFO — au redémarrage, tous les comptes sauf Sophie redeviennent actifs. Voulu en démo ; à écrire dans le contrat.

**F36 — Oracle d'existence d'un essai (404 en lecture, 403 sur 12 commandes)** · LOW · P2
- *Evidence* : expérience **E6** (membre `s04` étranger à `es-a8c33313`). Identifiant dérivé de (porteur, question, position).
- *Fix* : vérifier « concerné ? » avant « porteur ? » dans le banc (404 uniforme). Test : balayage E6 en test (F08-a).

**F37 — La mutation ne couvre que `capacites.py`** · MEDIUM · P2
- *Evidence* : `setup.cfg:5` `only_mutate=intelligence/capacites.py`.
- *Fix* : campagne ciblée sur `raison_consentement`, `offre_couvre`, `_composer`, `_transition` (en CI de nuit) ;
  publier le score par fichier. *Risk* : temps de CI.

**F38 — Hygiène** · LOW · P2 — `BUDGET_NOEUDS` muté temporairement (`capacites.py:331`) ; garde par `assert`
(`capacites.py:406`) ; `httpx.Client` jamais fermé (`ia.py:137`).

**F39 — Deux horloges dans un journal** · INFO — `PASSE_JURE.jusqu_a` (heure murale, epoch) dans un fait daté de
l'horloge simulée. Sans effet sur le rejeu (les passes ne sont pas rejoués) ; à dire dans l'architecture.

**F40 — Un brouillon d'essai n'expire jamais** · INFO — `echeances()` ne traite pas `BROUILLON` ; `TRANSITIONS` n'a pas
`BROUILLON → EXPIRE`. Voulu ? À décider et dire.

### 17.2 Constats antérieurs — état au 2026-10-01

| ID | Gravité | Sujet | État |
|---|---|---|---|
| F01 | HIGH | `/moi/demandes` écrit une interprétation du modèle sans confirmation | **DÉCISION** (fermer la route ou exiger la confirmation) |
| F02 | HIGH | `docs/ARCHITECTURE.md` et ADR 0004 périmés | OUVERT |
| F03 | MEDIUM | sonde E2E | FERMÉ (`762db1f`) — mais a introduit F25 |
| F04 | MEDIUM | test flaky (signature forgée) | FERMÉ (`a652690`) |
| F05 | MEDIUM | `ACCORD`/`RETRAIT` à deux sens, charges non typées | OUVERT |
| F06 | MEDIUM | `Banc` God object | ACCEPTÉ (reporté) |
| F07 | MEDIUM | rejeu des types récents non gardé | FERMÉ (`8d4c98a`) |
| F08 | MEDIUM | routes sans écran ; balayage IDOR | balayage fait ici (E6 : aucun IDOR) ; à figer en test ; classement DELETE/KEEP/DEPRECATE : **DÉCISION** |
| F09 | MEDIUM | `/acces` limité par IP | **DÉCISION** |
| F10 | MEDIUM | 4 tests d'absence seulement | OUVERT (confirmé) |
| F11 | MEDIUM | 39 modules hérités | OUVERT (frontière à documenter) |
| F12–F15, F18 | LOW | idempotence du partage de note, coût de `candidats`, `type: ignore`, cycle hérité, `date.today()` hérité | ACCEPTÉ |
| F16 | LOW | `docs/` sans statut historique | OUVERT |
| F17 | LOW | configuration hors journal | OUVERT (contrat à écrire) |
| F19–F21 | INFO | console locale ; démo seulement ; Hypothesis | OUVERT (à documenter / évaluer) |
| F22 | INFO | campagne de mutation GitHub | **FERMÉ** : run #4 vert |
| F23 | MEDIUM | E2E hors configuration produit ; `/demo/stage` dans le périmètre | tests : fait ; périmètre : **DÉCISION** |
| F24 | MEDIUM | clé de rejeu IA liée au secret | **DÉCISION** (recommandé : secret stable, voir F29) |

### 17.3 Ordre recommandé (vagues)

1. **Vague 2 — P0 correction** : F25 (rendre la CI verte, 2 lignes) ; F26 (test rouge E1, puis règle de validité — *décision
   métier signalée*) ; F27 (test rouge E3, application après validation).
2. **Vague 3 — P1 architecture / domaine** : F28, F29, F31, F01 (après décision), F36 + balayage IDOR en test (F08-a), F05-a.
3. **Vague 4 — tests et propriétés** : F10 ; propriété « tout changement d'offre consentie produit une cause » ; F32 ; F37.
4. **Vague 5 — performance / observabilité** : rien sans nouvelle mesure ; F33, F38.
5. **Vague 6 — documentation** : F30, F02, F16, F17, contrat des horloges (F39), `ENGINEERING_READINESS.md`.
6. **Vague 7 — revue hostile simulée** (§ 15 rejoué).

---

## 18. DO NOT CHANGE

Ces propriétés sont prouvées et constituent la colonne vertébrale ; toute correction doit les laisser intactes (tests cités).

1. **Un seul compositeur** (`Banc.solutions` / `_composer`) — ne pas créer de second moteur pour le registre (`test_capacites_oracle`).
2. **Journal en ajout seul**, identifiant = empreinte du contenu, compteur `n` dans chaque fait (`memoire.py`, `_ecrire`).
3. **La capacité est une projection, jamais stockée** (`test_la_capacite_est_une_projection_jamais_stockee`).
4. **Un retrait de finalité est définitif pour la pièce** ; re-consentement = nouvelle déclaration (`test_reconsentement`).
5. **Le modèle ne produit que des propositions** ; validation par le code, 1 nouvel essai, forme déterministe dite
   (`test_roles_ia`, `test_canaris_prompts`) ; **parité IA ON/OFF** (`test_parite_ia`).
6. **Aucune identité vers un modèle ni dans le journal** : `_net` + `proteger`, deux défenses indépendantes (canari).
7. **Aucun appel au modèle pendant une lecture ou un rejeu** (`test_pulse`, `test_rejeu_types_recents`).
8. **Statuts IA véridiques** (MODEL_CALLED / CACHE_REPLAY / FALLBACK_FORM) et provenance SYNTHETIQUE / DECLARE / JOUE.
9. **ACTIVE ≠ EN_COURS ≠ Outcome** ; aucun succès ni accord déduit du silence (`TRANSITIONS`, `echeances`).
10. **QR juré** : nonce unique, expiration, limites par code et par session, jamais par IP.
11. **Un verrou par monde, requête entière dessous** ; erreurs typées traduites en un seul endroit.
12. **Périmètre** : seul Club Pulse servi par défaut ; l'ancien prototype derrière drapeau + machine locale / jeton.
13. **Horloge du domaine = paramètre journalisé**, jamais `date.today()`.
14. **Budget de nœuds dit à l'écran** (« recherche bornée ») plutôt qu'un « impossible » silencieux.
15. Les garde-fous du dépôt : scanner de secrets, `test_ci_couverture_e2e`, `test_architecture` — ils ont attrapé F25.

---

## Annexe A — Expériences reproductibles (lecture seule, monde de démonstration, `HACKVS_ESSAIS_DB=:memory:` sauf E4)

| Id | Protocole | Résultat |
|---|---|---|
| E1 | `Demo(TAX).club` ; `repondre_ask(PAULINE, ask delegation_acheteurs, oui, {places: 14})` ; `modifier_offre(PAULINE, offre liée « minibus », plages 09.10 06:00–07:00)` ; lire l'instance et `capacites.recus(PAULINE)` | ACTIVE → ONE_AWAY, `perdus=[]` ; reçu « valable », révocable |
| E2 | `BUDGET_NOEUDS=1` ; `acquitter_recherche(delegation_acheteurs)` ; `emettre_pass_jure` + `utiliser_pass_jure` ; relire | `acquittee_le` : 2026-10-06 → `None` |
| E3 | remplacer `banc.revoir_membre` par une fonction qui lève ; `modifier_profil(LEA, disponible=False)` | journal 16 → 16 ; profil en mémoire `disponible=False` ; empreinte changée |
| E4 | `HACKVS_ESSAIS_DB=<fichier>` ; `A = Demo(reprendre=True)` ; `B = Demo()` ; `A.modifier_profil(LEA, disponible=False)` | journal de B : 16 → 17 (`PROFIL`) ; B en mémoire : `True` ; après redémarrage : `False` |
| E5 | toutes les routes de `creer_routeur`, sans en-tête | 47 × 401, 22 × 403, `/acces` et `/jure` 422 (corps vide) |
| E6 | `demo/aller/4` ; membre `s04` (GET essai → 404) appelle les 29 routes membre à identifiant avec de vrais identifiants | aucune écriture acceptée ; 12 × 403 « réservé au porteur » (oracle) |
| E7 | `pytest --ignore-glob='tests/test_e2e_*'` | 1 202 verts, 1 rouge (`test_ci_couverture_e2e`, F25) ; `scripts/verifier_secrets.py` → 1 secret probable (F25) |

## Annexe B — Scorecard interne (pas un argument)

| Catégorie | Verdict | Pourquoi |
|---|---|---|
| Architecture | PARTIALLY PROVEN | dépendances testées, un seul compositeur ; façade à état (D1), God object, héritage co-résident |
| Correctness | PARTIALLY PROVEN | oracle + mutation du registre ; F26 atteint |
| Security | PARTIALLY PROVEN | périmètre et IDOR vérifiés ; oracle d'existence, `/acces` par IP |
| Privacy | PROVEN (vers le modèle) / PARTIALLY (journaux, effacement) | canaris ; F33, F34 |
| Determinism | PARTIALLY PROVEN | prouvé hors F27 / F28 |
| Replay | PARTIALLY PROVEN | types récents gardés ; config et secret requis (F17, F24) ; défaut en mémoire (F29) |
| AI boundary | PARTIALLY PROVEN | registre : prouvé ; `/moi/demandes` : non (F01) ; provenance (F31) |
| Test quality | PARTIALLY PROVEN | oracle, contre-épreuves ; 4 tests d'absence, trous nommés § 10 |
| Maintainability | PARTIALLY PROVEN | `Banc` 1 247 l., charges non typées |
| Observability | PARTIALLY PROVEN | journaux structurés, métadonnées ; F33 |
| Performance | PARTIALLY PROVEN | mesurée, suffisante à l'échelle démo, quadratique |
| Demo reliability | **BROKEN** (aujourd'hui) | CI rouge (F25), redémarrage = monde perdu par défaut (F29), README contradictoire (F30) |
