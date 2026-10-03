# Lot 6 — Confiance et conformité

> **Construit — branche `annee-1`, pas dans la démo.** Tous les textes juridiques sont des projets **à valider par un
> juriste**. La checklist ASVS est une auto-évaluation, pas un audit externe.

**Une vraie vérification, faite cette nuit.** Les reçus de consentement (alignés ISO/IEC TS 27560, pas certifiés)
emploient le vocabulaire DPV du W3C. Leurs termes avaient été choisis, le 3 octobre, sans accès à la spécification. La
liste officielle de DPV 2.1 a été récupérée depuis le dépôt du W3C (le site w3id.org reste bloqué depuis la session) :
**11 termes sur 13 existaient ; `dpv:hasExpiryTime` et `dpv:hasWithdrawalTime` n'existent pas.** Remplacés par
`dpv:hasDuration` (`dpv:UntilTimeDuration`) et par le statut `dpv:ConsentWithdrawn` daté (`dct:modified`). Un test
vérifie désormais chaque terme. **La démo (`foire-2026`) garde les deux anciens termes** : à dire si un jury pose la
question.

**ASVS 4.0.3, niveau 2** ([ASVS_L2.md](../conformite/ASVS_L2.md)) : 259 exigences, généré depuis le fichier officiel
de l'OWASP — 38 conformes (chacune avec sa preuve), 13 partielles, 2 non conformes (durées de conservation non
appliquées, pas de SBOM), 23 sans objet (aucun mot de passe, aucun cookie de session), **183 non évaluées**.

**Journal des accès** : chaque consultation de la console du secrétariat est un fait (qui, quelle route, quand —
jamais les données rendues), lisible par l'administration seulement.

**Textes** : [registre](../conformite/REGISTRE_TRAITEMENTS.md), [analyse d'impact](../conformite/AIPD_MODELE.md),
politique de confidentialité [FR](../conformite/POLITIQUE_CONFIDENTIALITE_FR.md) / [DE](../conformite/POLITIQUE_CONFIDENTIALITE_DE.md),
conditions d'utilisation [FR](../conformite/CONDITIONS_UTILISATION_FR.md) / [DE](../conformite/CONDITIONS_UTILISATION_DE.md),
[contrat de sous-traitance](../conformite/CONTRAT_SOUS_TRAITANCE_MODELE.md).
