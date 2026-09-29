# comprendre_demande — v1
Consigne système : celle de `app/parser_llm.systeme(taxonomie)` (vocabulaire fermé de compétences, langues et zones ;
chaque critère avec l'extrait EXACT du texte). Sortie : JSON conforme à `app/parser_llm.SCHEMA`, revalidé par le code
(`app/parser_llm.valider`) : tout concept hors vocabulaire ou extrait introuvable est retiré et signalé.
