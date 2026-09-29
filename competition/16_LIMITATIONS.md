# 16 — Limites (à dire avant qu'on nous les demande)

- Aucune donnée réelle ; aucun test avec de vrais membres ; utilité non mesurée.
- Authentification des membres non implémentée ; aucun canal d'envoi réel (actions SIMULÉES, et étiquetées).
- Claude et Apertus jamais vérifiés contre leurs API réelles (aucune clé) ; le produit n'en dépend pas.
- Benchmark synthétique : vérité définie par nous ; ne prédit pas la performance réelle.
- Décroissance des liens (demi-vie de 30 jours), seuil « relation actuelle / à raviver » (90 jours) et budget d'attention
  (3 relances par membre et par jour) : hypothèses de produit, non mesurées auprès de vrais membres.
- Montée en charge mesurée jusqu'à 5000 membres GÉNÉRÉS, une machine, SQLite (`eval/resultats_perf_echelle.md`) ; aucune
  mesure en conditions réelles (concurrence de nombreux utilisateurs).
- Membres populaires : budget d'attention en place (relances, interventions) ; mais sur le benchmark d'intervention, notre
  plan « cohésion » ne bat PAS la méthode « relier les plus connectés » sur la taille du plus grand groupe (BENCHMARK_MEMO).
- Analyse des besoins par règles : échecs sur paraphrases et besoins en allemand / anglais libres (22 / 112 cas).
- Vues d'organisation (plan de soirée, tableau du Club, interventions) sans rôle authentifié : démo uniquement.
- Micro-cercle : glouton, pas un optimum ; consentement au format de groupe non modélisé.
- Le prototype a été préparé AVANT Hack VS : ne jamais le présenter comme réalisé pendant les 24 heures.
