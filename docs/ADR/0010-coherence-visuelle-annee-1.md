# ADR 0010 — Lot 12 : cohérence avec le Design System d'abord, refonte plus profonde à côté seulement

Statut : **accepté pour la branche annee-1**. Date : 2026-10-04.

## Contexte
Le lot 12 de la mission « Année 1 » demande d'abord une passe de cohérence de tous les écrans avec
`docs/design/DESIGN_SYSTEM.md` (captures avant / après), et n'autorise une refonte plus profonde qu'après une note de
décision écrite, construite à côté (interrupteur ou routes séparées), jamais en remplacement tant que la barrière
n'est pas passée.

## Décision
1. **Passe de cohérence, mesurable** : chaque couleur écrite dans une page doit être un jeton du Design System (ou de
   `tokens.css`) ; un test le vérifie pour les pages de l'année 1 (`/espace`, `/secretariat`, `/borne`,
   `/attestation`, `/compte`, `/desinscription`). Captures avant / après dans `docs/annee-1/vitrine/lot12-*.png`.
2. **Écrans de la DÉMO non retouchés** (`/regie`, `/salle/ecran`, `/preflight`, …) : leurs couleurs hors palette
   sont VOULUES (écrans sombres pour un projecteur, régie du pitch). Les changer modifierait la démo, ce que la
   mission interdit sans la barrière.
3. **Pas de refonte plus profonde cette nuit.** Elle demanderait une maquette validée (planches de l'artefact
   Design), des tests visuels et un passage par la barrière : rien de cela n'est possible avant l'arrêt. Si elle est
   décidée plus tard, elle se construira sous des routes séparées (`/v2/...`) derrière un interrupteur, avec les mêmes
   tests d'accessibilité (lot 11) et de budgets.

## Conséquences
+ La cohérence est vérifiée par un test, pas seulement constatée sur des captures.
− La cohérence vérifiée est celle des couleurs (et des feuilles partagées `tokens.css` / `pulse.css`) ; la typographie,
  les rayons et les ombres sont repris des feuilles communes mais ne sont pas contrôlés page par page.
