# Rapport de la mission « Année 1 » (nuit du 3 au 4 octobre 2026)

> **Copie pour la voie pitch.** L'original, ses liens et les documents qu'il cite sont sur la branche `annee-1`
> (`docs/annee-1/RAPPORT_ANNEE1.md`). Aucun de ces documents n'est dans `foire-2026`.

> **Construit n'est pas validé.** Tout ce qui suit est « Construit — branche `annee-1`, pas dans la démo », sauf
> mention contraire. Aucun membre réel, aucun résultat de pilote, aucun partenaire acquis. Monde de démonstration
> FICTIF. CI : n'a pas tourné (facturation) — toutes les portes ci-dessous sont LOCALES.

Mission reçue le 03.10 à 22:10 (Martigny). Arrêt des nouveautés : 04.10 à 14:10. Barrière fermée à 06:10.
Branches : `foire-2026` (voie pitch, filet `pitch-stable` = `d2eaa30`), `annee-1` (voie produit).

## 1. Fait, par lot (branche `annee-1`)

| Lot | Fait | Vitrine | Audit |
|---|---|---|---|
| 1 · Fondations | journal SQLite / PostgreSQL interchangeable, migrations réversibles, sauvegarde vérifiée (format v2), `/sante/pret`, `/metriques`, Docker de production (**image non construite cette nuit**), configuration documentée | [lot1] (branche annee-1 : `docs/annee-1/vitrine/lot1.md`) | [AUDIT_LOT1] (branche annee-1 : `docs/annee-1/AUDIT_LOT1.md`) : 2 bloquants, 8 importants corrigés |
| 2 · Comptes et rôles | invitation à usage unique, sessions et appareils, TOTP, élévation de session pour la console, dernier administrateur protégé, journal des accès | [lot2] (branche annee-1 : `docs/annee-1/vitrine/lot2.md`) | [AUDIT_LOT23] (branche annee-1 : `docs/annee-1/AUDIT_LOT23.md`) |
| 3 · Espace membre | pause, préférences (langue, canaux), mes demandes, export, purge réelle vérifiée par rejeu | [lot3] (branche annee-1 : `docs/annee-1/vitrine/lot3.md`) | [AUDIT_LOT23] (branche annee-1 : `docs/annee-1/AUDIT_LOT23.md`) : 4 bloquants corrigés sur les lots 2-3 (purge qui cassait le monde, deux purges le même jour, pause incomplète, second facteur remplaçable) |
| 4 · Console du secrétariat | critères du pilote gelés par empreinte, métiers à confirmer, campagnes bornées, bilan trimestriel MD / CSV / PDF | [lot4] (branche annee-1 : `docs/annee-1/vitrine/lot4.md`) | [AUDIT_LOT45] (branche annee-1 : `docs/annee-1/AUDIT_LOT45.md`) |
| 5 · Notifications | SMTP générique (simulé sans serveur), SMS par interface (faux fournisseur), modèles FR / DE, désinscription signée, déduplication par jour | [lot5] (branche annee-1 : `docs/annee-1/vitrine/lot5.md`) | [AUDIT_LOT45] (branche annee-1 : `docs/annee-1/AUDIT_LOT45.md`) : 1 bloquant corrigé (envoi sous le verrou) |
| 6 · Confiance et conformité | termes DPV vérifiés contre la liste officielle (deux termes inventés remplacés), registre, AIPD, politiques FR / DE, CGU, sous-traitance (projets **à valider par un juriste**), ASVS niveau 2 en auto-évaluation, HSTS | [lot6] (branche annee-1 : `docs/annee-1/vitrine/lot6.md`) | [AUDIT_LOT678] (branche annee-1 : `docs/annee-1/AUDIT_LOT678.md`) |
| 7 · IA Apertus | suivi du taux d'acceptation des propositions (Apertus 1.5, servi par le CSCS), « < 3 » compté par entreprise | [lot7] (branche annee-1 : `docs/annee-1/vitrine/lot7.md`) | [AUDIT_LOT678] (branche annee-1 : `docs/annee-1/AUDIT_LOT678.md`) |
| 8 · Plusieurs clubs | club partenaire EXEMPLE FICTIF seulement, adhésion croisée, membres à distance, interface EN **à relire par un natif** | [lot8] (branche annee-1 : `docs/annee-1/vitrine/lot8.md`) | [AUDIT_LOT678] (branche annee-1 : `docs/annee-1/AUDIT_LOT678.md`) : 1 bloquant corrigé (la purge du lot 3 réécrivait le journal des accès du lot 2) |
| 9 · Allumage Foire | borne de stand (jeton à échéance, révocable), import des exposants, passes par lots de 500, entonnoir jusqu'aux adhésions CONFIRMÉES | [lot9] (branche annee-1 : `docs/annee-1/vitrine/lot9.md`) | [AUDIT_LOT910] (branche annee-1 : `docs/annee-1/AUDIT_LOT910.md`) |
| 10 · Prototype e-ID | attestations SD-JWT VC des reçus, émetteur et vérificateur locaux — **prototype, non connecté à swiyu** | [lot10] (branche annee-1 : `docs/annee-1/vitrine/lot10.md`) | [AUDIT_LOT910] (branche annee-1 : `docs/annee-1/AUDIT_LOT910.md`) : 1 bloquant corrigé (n'importe quel émetteur accepté) |
| 11 · Qualité | WCAG 2.2 AA par axe-core dans les E2E (2 violations corrigées), PWA installable, file hors ligne des réponses, charge à 500 et 1 000 membres simulés, budgets | [lot11] (branche annee-1 : `docs/annee-1/vitrine/lot11.md`) | [AUDIT_LOT1112] (branche annee-1 : `docs/annee-1/AUDIT_LOT1112.md`) |
| 12 · Cohérence visuelle | pages de l'année 1 sur les jetons du Design System, captures avant / après ; refonte profonde NON faite (ADR 0010) | [lot12] (branche annee-1 : `docs/annee-1/vitrine/lot12.md`) | [AUDIT_LOT1112] (branche annee-1 : `docs/annee-1/AUDIT_LOT1112.md`) |
| En continu | modèle économique et prix (hypothèses), budget du pilote, pré-proposition Interreg, note Innosuisse, trois pages partenaires « à contacter », kits d'accueil FR / DE, guide du secrétariat | [affaires/] (branche annee-1 : `docs/annee-1/affaires/README.md`) | [AUDIT_LOT1112] (branche annee-1 : `docs/annee-1/AUDIT_LOT1112.md`) |

Chaque lot : interrupteur éteint par défaut, test rouge d'abord, CLAIMS et `etat.yaml` à jour. Démo vérifiée identique
(66 faits, mêmes empreintes du journal et de l'état, 17 découvertes : script `r14`, relancé à la consolidation, section 6)
— trace écrite dans les audits 2-3, 6-8 et 9-10 ; pour les autres lots, vérification faite pendant la nuit mais non
conservée en fichier. **Exceptions voulues, sur `annee-1` seulement** : l'export JSON-LD des reçus (termes DPV
corrigés) et le contraste des fenêtres de `/projection`. Six audits par sous-agents à
contexte neuf, plus un audit final ([AUDIT_FINAL] (branche annee-1 : `docs/annee-1/AUDIT_FINAL.md`), 0 bloquant, 3 importants corrigés) :
**9 bloquants trouvés, tous corrigés**, test rouge d'abord.

## 2. Pas fait (et pourquoi)

- **Refonte visuelle profonde** (lot 12) : décision écrite de ne pas la faire cette nuit (ADR 0010).
- **e-ID réel** : `did:tdw` inscrit au registre de base, liste de statut, OID4VCI / OID4VP, liaison d'appareil.
- **Voix, Apertus Mini** (lot 7) : non fait.
- **Exploitation (lot 1)** : image Docker jamais construite ; PostgreSQL encore en superutilisateur (rôle applicatif
  dédié et secret Docker à faire) ; pas de sauvegarde planifiée dans le compose ; rétention des sauvegardes à fixer ;
  pas de superviseur qui relance un service « unhealthy ».
- **Traçabilité** : la console de DÉMONSTRATION (jeton partagé) n'est pas tracée dans le journal des accès ; chaque
  consultation tracée écrit un fait (journal qui grossit) et la rétention de 12 mois n'est pas appliquée.
- Mineurs consignés dans les audits : `/metriques` sans jeton dédié ; pas de blocage après des codes TOTP faux ;
  désabonnement « en un clic » (RFC 8058) ; PDF du bilan sans limite de concurrence ; nombre exact de désinscriptions ;
  empreintes leurres SD-JWT ; résultats « incomplete » d'axe ; budgets de pages connectés ; petits écarts interrupteur
  éteint (file hors ligne) ; formules de tableur dans `bilan.py` (antérieur) ; divers du lot 1 (M8).
- **Langue « Mon espace »** et **jeton de borne révocable** : d'abord « non faits », repris et faits avant l'arrêt.

## 3. Ce qui a passé la barrière

**Rien.** (Sur `foire-2026` depuis `d2eaa30` : uniquement des documents, plus un outil autonome de captures pour la
visite guidée, `prototype/scripts/capturer_visite.py`, que l'application n'importe pas et que les tests ne collectent
pas.) Décision prise avant 06:10 : le seul candidat utile au pitch était la correction des termes DPV dans l'export
des reçus. Le passer aurait touché un chemin de la démo à quelques heures du pitch ; le bénéfice (un juré qui ouvrirait
le JSON-LD d'un reçu) ne valait pas le risque. Aucune ligne de la voie produit n'est entrée dans `foire-2026`.

## 4. Risques pour le pitch (sur `foire-2026`, tel quel)

1. **Termes DPV de l'export des reçus** : la démo emploie encore deux termes qui n'existent pas dans DPV 2.1
   (corrigés seulement sur `annee-1`, voir [vitrine/lot6] (branche annee-1 : `docs/annee-1/vitrine/lot6.md`)). Ne pas montrer le JSON-LD d'un reçu ; si un
   juré le demande : « corrigé sur la branche produit cette nuit, vérifié contre la liste officielle ».
2. **Passe découverte : retrait puis déclaration** (`decouverte.passes`) : sur `foire-2026`, l'ordre d'application
   PEUT faire réapparaître la déclaration d'un invité qui a retiré son consentement. Corrigé sur `annee-1`. Aucun bouton
   de retrait n'existe dans la page du passe : déclenchable seulement par l'API (`POST /decouverte/retirer`) ; la démo
   n'en contient aucun.
3. Contraste des fenêtres de l'écran `/projection` (4,36:1, sous le seuil AA) : corrigé sur `annee-1` seulement.
4. **Un test E2E intermittent sur le code de la démo** : `test_e2e_pulse.py::test_banc_d_essai_deux_telephones_perturbation_et_resultat_negatif`
   a échoué UNE fois (configuration `HACKVS_FOIRE=0`, sur `foire-2026`) : le bouton « Mettre à jour mon offre » était
   redessiné au moment du clic. Relance de la configuration : 34/34 ; le test seul : 10/10 ; il a passé dans tous les
   autres passages de la nuit (≈ 1 échec sur 20). **Cause non établie, rien corrigé** (barrière fermée ; le code de
   la démo est celui de `pitch-stable`). En direct : si ce bouton ne réagit pas, attendre une seconde et recliquer.

## 5. Ce que Hiba doit vérifier

- Les portes de la fin (section 6) sur SA machine : `make quality-check`, le lanceur sous le bash 3.2 de macOS, le
  runbook v2 avec de vrais téléphones.
- Les documents d'affaires : chaque fait externe est daté et marqué « à confirmer » ; **aucun partenaire n'a été
  contacté**.
- Les textes juridiques (lot 6) : à faire valider par un juriste avant tout pilote.
- Les traductions allemandes et anglaises : à faire relire par des natifs.

## 6. Portes de la fin (locales ; CI n'a pas tourné)

| Porte | `annee-1` (après l'audit final) | `foire-2026` |
|---|---|---|
| Suite complète (PostgreSQL de test compris sur `annee-1`) | **1 952 réussis, 1 ignoré** | **1 668 réussis, 1 ignoré** |
| E2E, `HACKVS_FOIRE=1` / `HACKVS_FOIRE=0` / mode salle (réseau local seul) | **34 / 34 ×3** | 34/34 · **33/34 puis 34/34 à la relance** · 34/34 (voir risque 4) |
| Lanceur et portabilité sous un vrai bash 3.2.57 (`JOUR_J_BASH`) | **29 / 29** | **29 / 29** |
| Lint, types, recherche de secrets (`make lint typecheck secrets`) | **vert** | **vert** |
| Démo identique (66 faits, empreintes `51c08b3654e992e1` / `9dc2cd617dfe3d7b`, 17 découvertes) | **oui** | — (aucun code changé) |
| Audit final par sous-agent | 0 bloquant ; 3 importants **corrigés** ([AUDIT_FINAL] (branche annee-1 : `docs/annee-1/AUDIT_FINAL.md`)) | même audit (intégrité de la branche vérifiée) |

## 7. À faire par Hiba, après le pitch

- **Fusionner `foire-2026` dans `main`** et **poser le tag** (aucun tag n'a été posé cette nuit — les tags existants `gel-demo` et `technical-freeze-v1` datent des 29.09 et 02.10 —, rien n'a été poussé sur `main`).
  Attention : il n'existe pas de branche `main` sur le dépôt distant (branches : `foire-2026`, `pitch-stable`,
  `annee-1`, `audit-nuit`, et la branche par défaut `claude/modest-bohr-xvk53n`) — choisir la branche cible avant de
  fusionner.
- `annee-1` reste une branche produit : ne la fusionner qu'après sa propre revue.
