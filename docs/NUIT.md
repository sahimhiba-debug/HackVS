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
