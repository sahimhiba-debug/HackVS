# Nuit du 3 au 4 octobre 2026 — « Foire 2026 »

Branche `foire-2026`, partie de `claude/modest-bohr-xvk53n` @ `3a6ef4f`.

**Temps disponible.** Départ samedi 03.10 à 13:52 (Zurich). Arrêt des fonctionnalités dimanche 04.10 à **07:30**.
Cela laisse **17 h 38**. Tag `gel-final` posé par Hiba à 08:00.

## Règles de la nuit (rappel)

- **Interrupteurs.** Chaque nouveauté est derrière un interrupteur (`HACKVS_FOIRE`, défaut : allumé en démo).
  - Éteint, le produit se comporte comme hier, à l'octet près.
- **Démo verte à chaque commit.** Le parcours de démo (DEMO_SCRIPT, rituel § 9.5) doit passer : suite complète et E2E
  avant chaque push qui touche le code.
- **Mutation.** Les chemins surveillés par la campagne (`capacites.py`, `essai.py`, `test_capacites*.py`,
  `setup.cfg`…) ne sont **pas touchés** cette nuit.
  - Les nouveautés vivent dans des modules nouveaux : `intelligence/suivi.py`, `intelligence/decouverte.py`, etc.
  - Le déclencheur n'a donc pas besoin d'être coupé.
- **Tests et preuves.**
  - Pour chaque finding : test rouge d'abord, puis commit.
  - Chaque nouveauté visible entre dans `CLAIMS.md` avec sa classe.
  - `PREUVES.md` ne reçoit que des chiffres mesurés.
- **Étiquetage.**
  - Ce qui est simulé (boîte d'envoi, intention d'adhésion) est marqué « simulé en démonstration » à l'écran et dans
    `CLAIMS.md`.
  - Les chiffres affichés sont marqués « monde de démonstration ».
- **Règle de dérapage.** Une P0 qui dépasse son estimation de plus de 90 min est réduite ou abandonnée.

## Plan horaire (estimations)

| Créneau | Bloc | Contenu | Estimation |
|---|---|---|---|
| 13:52–14:15 | 0 | plan, branche, cartographie du journal | 0:25 |
| 14:15–15:00 | **C** | anonymat à petite échelle : message de retrait, rôle masqué sous k = 3 (couche de vue seulement) | 0:45 |
| 15:00–17:30 | **A** | Suivi : `intelligence/suivi.py` (agrégats depuis le journal, k = 3, périodes), route console, page, canari « aucune donnée personnelle » | 2:30 |
| 17:30–19:00 | **B** | clôture de reçu : machine à 4 étapes explicite, fait `CLOTURE` journalisé, bouton sur le reçu, agrégat dans Suivi | 1:30 |
| 19:00–21:30 | **D** | passe découverte 90 jours : invité, déclaration d'entreprise + reçu, 3 demandes maximum, « Rejoindre le Club » (intention), comptes dans Suivi | 2:30 |
| 21:30–23:00 | **E** | « Le Club cherche » : demandes sans réponse par métier, inviter un contact (passe lié + QR, texte FR/DE) | 1:30 |
| 23:00–00:00 | — | vérification complète : suite, E2E, E2E salle ; scénario de démo du juré d'Annecy | 1:00 |
| 00:00–02:00 | **I + J** | `docs/roadmap/*` (6 fichiers), présentation (script, slides + deck, Q&R, runbook) | 2:00 |
| 02:00–03:30 | **F** | membre à distance : zone, langue, boîte d'envoi simulée, liens signés oui / non / pas cette fois | 1:30 |
| 03:30–04:30 | **G** | `make bilan` | 1:00 |
| 04:30–06:00 | **H** | `ingest_tally.py`, taxonomie YAML, `eval_classification.py` (feuille d'annotation) | 1:30 |
| 06:00–07:30 | **Livraison** | lint, types, suite, E2E (réseau normal et coupé), CLAIMS, PREUVES, tableau d'avancement, `RAPPORT_NUIT.md`, push, CI | 1:30 |

La documentation (I, J) passe avant F, G et H. Si A à E dérapent, F, G et H sont réduits, dans cet ordre inverse.

## Statut (mis à jour toutes les heures)

| Heure | Fait | En cours | Abandonné |
|---|---|---|---|
| 14:15 | plan, branche `foire-2026` | C | — |
| 14:20 | C (`65d507d`), E2E conscient de l'interrupteur (`e778d6e`), A + B (`ff68046`) — suite 1 401 verte, E2E 22/22 allumé, lint/types/secrets propres. **En avance d'environ 3 h sur le plan.** | D | — |
| 14:35 | D passe découverte (`a880d01`), E « Le Club cherche » (`ee8f0d7`) — **toutes les P0 livrées** ; CI verte sur C et A+B, D et E en cours | I + J | — |
| 14:50 | I docs/roadmap (`f33b60a`) ; correctifs trouvés en capturant : demande rouverte (`5d9adb7`), « null » dans Suivi (`bb4bf02`) ; J présentation + deck (`e1c6576`), contrôle AA jour/nuit 0 échec | F → G → H | — |
| 15:05 | F membre à distance (`da23a2a`) — suite verte, E2E 25/25 allumé. **CI : les jobs ne démarrent plus depuis `e1c6576` — refus de GitHub (« recent account payments have failed or your spending limit needs to be increased »), pas un échec du code ; à régler par Hiba dans Billing & plans.** Preuves locales tenues à chaque commit. | G → H | — |
| 15:30 | G `make bilan` (`2d2d6de`), H pipeline Tally (`3ae1d9c`, phrases non arrivées), correctif interrupteur éteint (`7ca7be7`) ; livraison : 1 434 tests, E2E 25/25 allumé, éteint et réseau coupé ; [RAPPORT_NUIT.md](RAPPORT_NUIT.md). **Travail arrêté** : rien d'autre ne sera commité avant le gel. | — | — |

## Vague 2 et 3 (consignes reçues à 15:47 — remplacent les précédentes)

Construction jusqu'à 04:00 au plus tard, audit (90 min max, sous-agent à contexte neuf, branche `audit-nuit`), puis
corrections et livraison avant 07:30. Aucun tag, aucun push sur `main` — **`main` n'existe pas sur le dépôt distant**
(seules `foire-2026` et `claude/modest-bohr-xvk53n` existent) : l'audit prend pour base le point de divergence avec
`claude/modest-bohr-xvk53n`.

| Heure | Lot |
|---|---|
| 15:50 | §2 Tally : ingestion, classification Apertus, feuille d'annotation (`metier_attendu`, `domaine`) |
| 16:15 | §4 P0 mode salle : QR multi-usage, accueil 2 gestes, écran géant, télécommande, bascule scriptée, purge, PUBLIC_BASE_URL |
| 18:30 | §4.7 déploiement (compose, Caddy, .env.example, deploy.sh, purge.sh, DEPLOIEMENT.md) · §4.8 charge 80 téléphones |
| 19:30 | §6 feuille de route révisée · §7 etat.yaml + /feuille-de-route (monde « visite ») |
| 20:30 | §5 présentation v2 (02/03/03b/04/06 v2, 07, deck v2, fiches v2) |
| 22:30 | §8 V6, V2, d, b, a, c, e, f, g, V3, V4, V5 — dans cet ordre, aussi loin que possible |
| ≤ 04:00 | gel des fonctionnalités → audit → corrections → livraison |

### Statut vague 2

| Heure | Fait | En cours | Abandonné |
|---|---|---|---|
| 15:50 | plan | §2 Tally | — |
| 16:15 | §2 Tally (`fad69c2`) ; PUBLIC_BASE_URL (`e19da8d`) ; mode salle (`a0d1e46`) ; rejeu Apertus 1.5 sur les 26 cas : 1/26 inchangé (`1b7902e`) ; constellation (`ff2de2c`) ; déploiement + charge 80 (`d152a55`) — suite 1 454 verte. CI : ne démarre pas (facturation), portes locales seulement | §6 feuille de route, §7 etat.yaml | — |
| 17:20 | Constellation en motion design + 2 passes d'autocritique (`730caac`) ; liste du Club : CSV (`74cbc6b`), seuil « < 3 » en **entreprises distinctes** (`493b977`), 25 métiers, « Ce que votre Club pourrait assembler » 8/9 (`de2d3e4`), 145/173 partout + roadmap Mondiaux/CSCS/pistes « à contacter » ; **pas de VPS** : tunnel (console fermée aux requêtes relayées `97763e7`, QR en direct `ee5dea5`, `--base-url`, DEMO_TUNNEL.md `5ef41c4`) ; deck v2 (`24ba47c`) + textes v2 (`57056b5`). Écart assumé : monde de démo NON re-proportionné (vérités plantées, risque démo). CI : toujours bloquée par la facturation — portes locales seulement | P3 n°1 appel d'outils Apertus | proportions du monde de démo (reporté) |
| 17:55 | P3 n°1 appel d'outils : **1/26, aucun gain**, interrupteur éteint (`a02dbc4`) ; n°2 reçus alignés ISO/IEC TS 27560 (`c285111`) ; n°3 coach SMART (`bb4b43d`) ; n°4 nouveaux liens tissés (`0c6d45a`) ; n°5 interface allemande (`9f83932`) ; n°6 **bloqué** (feuille d'annotation non remplie) ; n°7 conformité (`74cf426`) ; n°8 membre associé, partenaire fictif (`c26967c`) ; n°9 annonces sous chiffre (`adcc5c7`) ; n°10 tableau du secrétariat (`66e6ec0`) ; n°11 pipeline d'affinage, essai 9/10 gardées, non lancé (`6473783`) ; n°12 passe start-up The Ark (`f65a4e9`) ; n°13 bilan CSV (`4ead722`) ; n°14 dossiers de financement (`de64f5c`) ; n°15 piliers (`c14a5f5` + correctif `b167a9b`) ; n°16 réciprocité (`66c8e28`). Portes de livraison en cours (suite, E2E allumé / éteint / réseau coupé) ; CI toujours bloquée par la facturation | audit (sous-agent, branche audit-nuit) | n°6 (pas de vérité terrain) |
| fin | Audit (sous-agent, branche `audit-nuit`, `docs/audit/AUDIT_NUIT.md`) : tous les BLOQUANT et IMPORTANT corrigés, un commit par constat, test rouge d'abord (`test_audit_nuit_defauts.py`, 5/5 verts) ; MINEUR 13, 14, 16, 17, 18 corrigés (`8d83954`), 10, 11, 12, 15, 19, 20, 21 consignés dans RAPPORT_NUIT « Audit ». Portes locales sur `51d406a` : suite 1 572 verte, lint, types, secrets, validateur ; E2E 31/31 ×3 sur `8d83954`. CI : n'a pas tourné (facturation). Aucun tag, rien sur main | — | n°6 (pas de vérité terrain) |

### État des lieux — message consolidé reçu à 16:40 (remplace les consignes depuis 15:30)

| § | Point | État | Où / commit |
|---|---|---|---|
| 1.2 | « CSCS (Lugano), pas Public AI » partout | ⬜ | à corriger dans CLAIMS, PREUVES, docs, script, Q&R |
| 1.3 | « 1/26 » déjà sur Apertus 1.5 70B, aucune progression revendiquée | ✅ | `1b7902e`, PREUVES |
| 1.4 | Carte : 5 essais sur la même carte avant la scène | ⬜ | à mesurer ; hors scène d'ici là |
| 2 | Tally : CSV, ingestion, classification Apertus, feuille `metier_attendu` / `domaine` | ✅ | `fad69c2` |
| 3 | Contexte réel sourcé dans PREUVES | ⬜ | |
| 4A | Mode salle (QR, passes, deux gestes, télécommande, bascule, purge, PUBLIC_BASE_URL, déploiement, /sante, charge 80) | ✅ | `a0d1e46`, `e19da8d`, `d152a55` |
| 4B | Constellation en motion design (Vogel, tokens, WAAPI, jour/nuit, aria-live, vidéo, PNG, DIRECTION.md) | 🟡 | première version statique `ff2de2c` ; motion design à faire |
| 5 | La carte devient le profil | ✅ (hors scène) | `cfd152e` ; règle 5/5 à mesurer |
| 6 | Présentation v2 (02, 03, 03b, 04, 06 v2, 07, deck v2, fiches v2) | ⬜ | |
| 7 | Feuille de route révisée | 🟡 | `cb9ccb1` ; à ajouter : Mondiaux, risque nommé, conditions d'usage IA, pistes de partenaires |
| 8 | Feuille de route vivante + note swiyu / voix / Mini | ✅ | `cb9ccb1` ; maintenir |
| 9 | Chantiers P3 n° 1 à 16 | ⬜ | dans l'ordre, après le P1 |
| 11 | Audit (sous-agent, branche `audit-nuit`) | ⬜ | ≤ 04:00 |
| 12 | Livraison | ⬜ | ≤ 07:30 |

### Contexte — URL des sources externes (message de l'équipe, 03.10)

- https://latele.ch/articles/martigny-la-foire-du-valais-fera-son-cinema
- https://www.bluewin.ch/fr/infos/suisse/par-ici-la-bobine-la-foire-du-valais-annonce-son-blockbuster-2026-li.3274212
- https://www.regione.vda.it/allegato.aspx?pk=129254
- https://latele.ch/articles/pres-de-250-000-personnes-attendues-a-la-foire-du-valais
- https://www.cransmontana2027.ch/en
- https://www.iamexpat.ch/expat-info/swiss-news/e-id-coming-switzerland-december-1
- https://ecommons.cornell.edu/entities/publication/9c0adbfb-985c-4f7d-aae3-96959822bc4c
- https://archive.harbus.org/2019/rcs-learn-to-give-and-take
- https://digitaleconomy.stanford.edu/publication/a-causal-test-of-the-strength-of-weak-ties
- https://www.iso27001security.com/html/27560 · https://w3id.org/dpv/guides/consent-27560
- https://american-image.com/ten-tips-for-better-trade-show-leads-follow-up/
- https://www.liip.ch/en/blog/apertus-1-5-6-ways-to-try-out-switzerland-s-updated-ai-model
- https://docs.vllm.ai/en/latest/api/vllm/tool_parsers/apertus_tool_parser/

## Mission « Année 1 » (reçue le 03.10 à 22:10, heure de Martigny)

Arrêt des nouveautés : **dim. 04.10, 14:10** · barrière fermée (arrêt − 8 h) : **dim. 04.10, 06:10**.
Filet : branche `pitch-stable` = `d2eaa30` (tête de `foire-2026` à l'ouverture). Voie produit : branche `annee-1`.

| Heure | Fait | En cours | Abandonné |
|---|---|---|---|
| 22:45 | Section 1 (foire-2026, documents) : version parlée dans le script v2 + 3e « Et après ? » (`9a55ff7`) ; 18 / 15 min + trois répétitions (`9a55ff7`) ; prompteur (`606eeb0`) ; six jurys simulés, 48 questions, top 20, page d'entraînement (`0feb345`) ; visite guidée, 18 captures réelles | lot 1 (annee-1) | — |
| 23:15 | annee-1 : lot 1 fondations (`afb26c5`, `82d0a6a`) ; lot 2 comptes, rôles, TOTP (`962eda6`) ; lot 3 espace membre, pause, export, purge réelle (`153e86d`) — tout « construit, pas dans la démo », interrupteurs éteints par défaut. Audit du lot 1 reçu : 2 BLOQUANTS (sauvegarde illisible avec U+2028 ; PostgreSQL sans reconnexion), 8 IMPORTANTS | correctifs de l'audit du lot 1 (test rouge d'abord) | — |
| 00:15 | annee-1 : correctifs de l'audit du lot 1 (`c6c6f4a` : 2 bloquants, 8 importants) ; lot 4 console du secrétariat (`c6d95a2`) ; audit des lots 2-3 reçu (4 bloquants : purge qui cassait le monde, deux purges le même jour, pause incomplète, second facteur remplaçable) — tous corrigés, test rouge d'abord (`1b309ea`) ; démo vérifiée identique (mêmes empreintes) | lot 5 notifications (domaine vert, routes en cours) | — |
| 01:00 | annee-1 : lot 5 notifications (`d40fa0c`) ; lot 6 confiance et conformité (`c15a2ee` : deux termes DPV inventés trouvés et remplacés sur annee-1, ASVS niveau 2 en auto-évaluation, textes à valider par un juriste) ; audit des lots 4-5 (1 bloquant : envoi SMTP sous le verrou du monde) corrigé, test rouge d'abord (`e2d2eaa`) | lot 7 (IA Apertus) | — |
| 02:25 | annee-1 : lot 7 suivi du taux d'acceptation des propositions Apertus (`93e4ddd`) ; lot 8 plusieurs clubs, club partenaire fictif marqué comme tel, interface EN « à relire par un natif » (`c735f84`) ; lot 9 allumage Foire : borne, import des exposants, passe à grande échelle, entonnoir des adhésions (`2f03ddb`) ; lot 10 attestations SD-JWT VC, « prototype, non connecté à swiyu » (`7d75447`) ; audit des lots 6-8 (1 bloquant : la purge réécrivait les traces de sécurité) corrigé, test rouge d'abord (`9d9213a`). Portes locales : suite complète 1878 réussis, ruff, mypy ; démo identique (mêmes empreintes). Barrière : rien proposé | audit des lots 9-10 ; lot 11 | I5 de l'audit 6-8 (langue choisie dans « Mon espace ») : non fait, raison dans `AUDIT_LOT678.md` |
| 03:22 | annee-1 : lot 11 accessibilité WCAG 2.2 AA par axe-core dans les E2E (2 violations trouvées et corrigées, `c1bd33e`) ; audit des lots 9-10 (1 bloquant : le vérificateur d'attestations acceptait n'importe quel émetteur) corrigé, test rouge d'abord (`2829a9f`) ; lot 11 PWA installable, file hors ligne des réponses, charge à 500 et 1 000 membres simulés, budgets (`07f0033`) ; lot 12 cohérence avec le Design System, captures avant / après (`5b76f14`) ; documents d'affaires en hypothèses (`8bd89c2`). Premier passage de charge : budget des lectures DÉPASSÉ (1,6 s à 1 000 membres) ; cause trouvée (index recalculé à chaque lecture), correctif en cours de validation. Barrière : rien proposé | suite complète + audit des lots 11-12 | refonte visuelle profonde (décision écrite : pas cette nuit, ADR 0010) |
| 04:35 | annee-1 : correctif de charge (index recalculé à chaque lecture ; lectures p95 1,6 s → 79 ms à 1 000 membres, `2ee66c7`) ; audit des lots 11-12 (0 bloquant, 5 importants : file hors ligne qui gardait le jeton de session, réponse perdue à la réouverture, stockage local non dit, charge sans écritures, libellés des kits) tous corrigés, test rouge d'abord (`dfa96ea`) ; avec une écriture par membre, budgets tenus de justesse (lectures 988 ms pour 1 s à 1 000 membres), dit. En cours : deux « non fait » repris (langue de « Mon espace », jeton de borne à échéance et révocable). **Barrière : décision — rien ne passe** (seul candidat utile au pitch : les termes DPV corrigés de l'export des reçus ; le risque de toucher un chemin de la démo dépasse le bénéfice ; noté pour RAPPORT_ANNEE1) | suite complète, puis consolidation | — |
