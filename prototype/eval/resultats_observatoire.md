# Observatoire du réseau — benchmark sur réseaux PATHOLOGIQUES générés (SYNTHETIC)

20 graines par cas ; 60 membres ; seuils fixés avant la première exécution.

| Cas | Phénomènes attendus | Exact (nommé, rien d'autre) | Attendu manqué | Fausse alerte en plus | Baseline KPI : « quelque chose d'anormal » |
|---|---|---|---|---|---|
| SAIN | — | 20/20 | — | 0/20 (—) | 0/20 |
| ISOLES | ISOLEMENT | 17/20 | 0/20 | 3/20 (['PONT_FRAGILE']) | 20/20 |
| HUB | CONCENTRATION | 0/20 | 0/20 | 20/20 (['PASSAGE_UNIQUE']) | 20/20 |
| FAUSSE_DIVERSITE | CONCENTRATION | 17/20 | 0/20 | 3/20 (['PASSAGE_UNIQUE']) | 20/20 |
| SILOS | FRAGMENTATION | 0/20 | 0/20 | 20/20 (['PASSAGE_UNIQUE', 'PONT_FRAGILE']) | 20/20 |
| PONT_FRAGILE | PONT_FRAGILE | 20/20 | 0/20 | 0/20 (—) | 18/20 |
| PASSAGE_UNIQUE | PASSAGE_UNIQUE | 20/20 | 0/20 | 0/20 (—) | 17/20 |
| VIEILLISSEMENT | VIEILLISSEMENT | 0/20 | 0/20 | 20/20 (['FRAGMENTATION', 'ISOLEMENT', 'PASSAGE_UNIQUE', 'PONT_FRAGILE']) | 20/20 |
| SUR_SOLLICITATION | SUR_SOLLICITATION | 20/20 | 0/20 | 0/20 (—) | 0/20 |
| ENTRE_SOI | ENTRE_SOI, FRAGMENTATION | 0/20 | 0/20 | 20/20 (['PASSAGE_UNIQUE', 'PONT_FRAGILE']) | 20/20 |

Contre la vérité INDÉPENDANTE (phénomènes réellement présents, recalculés sans l'observatoire) : 0 alerte(s) sans phénomène réel, 0 phénomène(s) réel(s) non signalé(s). Les « fausses alertes en plus » de la table sont donc des phénomènes CO-PRÉSENTS (ex. un réseau vieilli est aussi fragmenté), pas des erreurs.

## Frontière de détection (intensité variable, 20 graines)

| Pathologie | Intensité | Détectée |
|---|---|---|
| ISOLES | 0.3 | 20/20 |
| ISOLES | 0.6 | 20/20 |
| ISOLES | 1.0 | 20/20 |
| VIEILLISSEMENT | 0.3 | 0/20 |
| VIEILLISSEMENT | 0.6 | 9/20 |
| VIEILLISSEMENT | 1.0 | 20/20 |

Lecture : la baseline KPI dit au mieux « quelque chose a changé » ; elle ne nomme jamais le phénomène ni l'intervention. Seuils et générateur sont les nôtres (circularité possible, déclarée).
