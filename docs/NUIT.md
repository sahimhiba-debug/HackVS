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
