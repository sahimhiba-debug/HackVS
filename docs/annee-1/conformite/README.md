# Confiance et conformité (ANNÉE 1 · lot 6)

> **Construit — branche `annee-1`, pas dans la démo.** Tous les textes juridiques sont des **projets à valider par
> un juriste** ; aucun n'est un avis juridique.

| Document | Contenu |
|---|---|
| [REGISTRE_TRAITEMENTS.md](REGISTRE_TRAITEMENTS.md) | registre des activités de traitement (nLPD art. 12), durées PROPOSÉES |
| [AIPD_MODELE.md](AIPD_MODELE.md) | analyse d'impact pré-remplie (nLPD art. 22), cotation à faire |
| [POLITIQUE_CONFIDENTIALITE_FR.md](POLITIQUE_CONFIDENTIALITE_FR.md) · [DE](POLITIQUE_CONFIDENTIALITE_DE.md) | politique de confidentialité |
| [CONDITIONS_UTILISATION_FR.md](CONDITIONS_UTILISATION_FR.md) · [DE](CONDITIONS_UTILISATION_DE.md) | conditions d'utilisation |
| [CONTRAT_SOUS_TRAITANCE_MODELE.md](CONTRAT_SOUS_TRAITANCE_MODELE.md) | modèle de contrat de sous-traitance (nLPD art. 9) |
| [ASVS_L2.md](ASVS_L2.md) | OWASP ASVS 4.0.3 niveau 2 : statut de chacune des 259 exigences (auto-évaluation) |
| [dpv-2.1-termes.txt](dpv-2.1-termes.txt) | noms des termes DPV 2.1 : chaque terme des reçus 27560 y est vérifié |
| [asvs-4.0.3-en.csv](asvs-4.0.3-en.csv) | fichier officiel de l'OWASP (CC BY-SA 3.0) |

Dans le code : reçus alignés ISO/IEC TS 27560 exportés en JSON-LD (termes DPV vérifiés, `test_annee1_dpv.py`) ;
journal des accès à la console (`/api/pulse/secretariat/acces`, administration seulement) ; en-têtes de sécurité
(CSP, nosniff, Referrer-Policy, Permissions-Policy, COOP, X-Frame-Options ; HSTS si `HACKVS_HSTS=1`).
