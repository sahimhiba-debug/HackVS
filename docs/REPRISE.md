# État de reprise (fin du lot 3, 28.09.2026)

Pour reprendre le travail sans relire toute la conversation.

## Où en est-on
- Branche `claude/modest-bohr-xvk53n` ; le dernier commit est cité dans AUDIT_PACKET.md.
- Lot 2 **livré** : Bourse des besoins complète, vue scène, moteur corrigé (6 fragilités), flux Claude prêt, évaluation sur 3 jeux,
  19 tests, parcours navigateur, axe à 0 violation, vidéo de 50 s, documentation.
- Lot 3 **livré** : vue du Club, profil en 30 s, acte 2 « le Club se répare », couverture (pluriels, allemand), présentation `/presentation`, QR, Docker. 22 tests.
- Préparation de la démo : charger l'historique fictif **avant** d'ouvrir la scène, et ne plus réinitialiser (DEMO.md).
- **Aucun retour d'audit reçu** (ni du cycle 1 sous forme de texte, ni du lot 2). Les corrections du lot 2 s'appuient sur le résumé des fragilités transmis par Hiba.

## Ce qui attend une entrée extérieure
| Élément | Bloque | Débloque |
|---|---|---|
| Clé API Anthropic | Mesure réelle de Claude | `python scripts/verifier_claude.py --confirmer` (≈ 0,56 USD estimés) |
| Accès réseau aux sites officiels (foireduvalais.ch, hevs.ch, devpost.com…) | Lecture complète des sources | Paramètres réseau de l'environnement cloud |
| Texte complet de l'audit ChatGPT (sources et cas adversariaux transmis) | Vérifier que chaque point est traité | Le déposer dans `docs/audits/` |
| Brief et règlement de Hack VS | Direction finale ; réutilisation du code | Brief officiel |

## Prochaines actions proposées (par valeur pour la démo)
1. Mesurer Claude sur les 3 jeux ; si la couverture du jeu réservé progresse sans violation, activer Claude pour la démo (le badge le dira).
2. Faire écrire 10 cas **indépendants** (équipe ou auditeur) ; les exécuter une fois.
3. Interface bilingue FR/DE (hypothèse H10).
4. Selon le brief : compagnon de soirée (3 personnes à rencontrer) ou serveur MCP.
5. Sur place : remplir les espaces ambre de la présentation (équipe, chiffres terrain) ; décider du déploiement public (QR).

## Commandes de vérification rapide
```bash
cd prototype && python -m pytest -q tests && python -m eval.run_eval
uvicorn app.main:app & python scripts/parcours_demo.py
```

## Pièges connus pour la personne qui reprend
- Le serveur de développement avec `--reload` ne recharge pas `web/` (fichiers statiques servis tels quels : rafraîchir le navigateur suffit).
- `eval/cas_reserve.json` **ne doit pas** servir à régler le moteur avant l'audit (il perdrait sa valeur d'estimation).
- Le journal (`/api/journal`, `/api/flux`) expose les identités : réservé à la démo.
