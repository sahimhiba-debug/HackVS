# Sonde Public AI — ce que l'API fait vraiment

> Écrit par `prototype/scripts/sonde_publicai.py` : réponses BRUTES, aucune retouche. La clé n'est jamais écrite ;
> les requêtes sont consignées sans en-tête d'autorisation. Un verdict ne vaut que pour la date, l'hôte et le modèle ci-dessous.

- Date : 2026-09-30 17:50 UTC
- Hôte : `https://api.publicai.co/v1`
- Clé fournie : oui
- Modèle : `—`
- **État : UNKNOWN — injoignable : ProxyError: 403 Forbidden sur GET /models : aucun autre essai n'est significatif.**

| Essai | Verdict | Raison | HTTP | Durée |
|---|---|---|---|---|
| modèles | **UNKNOWN** | injoignable : ProxyError: 403 Forbidden | — | — |
| JSON simple (prompt) | **UNKNOWN** | GET /models a échoué | — | — |
| response_format json_schema (strict) | **UNKNOWN** | GET /models a échoué | — | — |
| tools (tool_choice required) | **UNKNOWN** | GET /models a échoué | — | — |
| non-thinking | **UNKNOWN** | GET /models a échoué | — | — |

## modèles


Requête :

```json
{
  "methode": "GET",
  "url": "https://api.publicai.co/v1/models"
}
```

Réponse brute (HTTP —) :

```
injoignable : ProxyError: 403 Forbidden
```
