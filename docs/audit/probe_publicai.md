# Sonde Public AI — ce que l'API fait vraiment

> Écrit par `prototype/scripts/sonde_publicai.py` : réponses BRUTES, aucune retouche. La clé n'est jamais écrite ;
> les requêtes sont consignées sans en-tête d'autorisation. Un verdict ne vaut que pour la date, l'hôte et le modèle ci-dessous.

- Date : 2026-10-01 19:01 UTC
- Hôte : `https://api.inference.cscs.ch/v1`
- Clé fournie : oui
- Modèle : `swiss-ai/Apertus-70B-Instruct-2509`
- **État : exécutée contre https://api.inference.cscs.ch/v1 avec le modèle « swiss-ai/Apertus-70B-Instruct-2509 »**

| Essai | Verdict | Raison | HTTP | Durée |
|---|---|---|---|---|
| modèles | **SUPPORTED** | 11 modèles listés | 200 | 1411 ms |
| JSON simple (prompt) | **ERROR** | HTTP 403 | 403 | 219 ms |
| response_format json_schema (strict) | **ERROR** | HTTP 403 | 403 | 225 ms |
| tools (tool_choice required) | **ERROR** | HTTP 403 | 403 | 220 ms |
| non-thinking | **UNKNOWN** | aucune réponse de chat à examiner | — | — |

## Modèles listés (GET /models)

- `google/gemma-4-31B-it`
- `moonshotai/Kimi-K2.7-Code`
- `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16`
- `swiss-ai/Apertus-70B-Instruct-2509`
- `swiss-ai/Apertus-8B-Instruct-2509`
- `swiss-ai/Apertus-v1.5-70B`
- `swiss-ai/Apertus-v1.5-70B-thinking`
- `swiss-ai/Apertus-v1.5-8B`
- `swiss-ai/Apertus-v1.5-8B-thinking`
- `zai-org/GLM-5.2`
- `zai-org/GLM-5.3`

## modèles


Requête :

```json
{
  "methode": "GET",
  "url": "https://api.inference.cscs.ch/v1/models"
}
```

Réponse brute (HTTP 200) :

```
{"data":[{"id":"swiss-ai/Apertus-70B-Instruct-2509","created":1790366177,"object":"model","owned_by":"Envoy AI Gateway"},{"id":"swiss-ai/Apertus-8B-Instruct-2509","created":1790366177,"object":"model","owned_by":"Envoy AI Gateway"},{"id":"swiss-ai/Apertus-v1.5-70B","created":1790366177,"object":"model","owned_by":"Envoy AI Gateway"},{"id":"swiss-ai/Apertus-v1.5-70B-thinking","created":1790366177,"object":"model","owned_by":"Envoy AI Gateway"},{"id":"swiss-ai/Apertus-v1.5-8B","created":1790366177,"object":"model","owned_by":"Envoy AI Gateway"},{"id":"swiss-ai/Apertus-v1.5-8B-thinking","created":1790366177,"object":"model","owned_by":"Envoy AI Gateway"},{"id":"google/gemma-4-31B-it","created":1790366177,"object":"model","owned_by":"Envoy AI Gateway"},{"id":"zai-org/GLM-5.2","created":1790366177,"object":"model","owned_by":"Envoy AI Gateway"},{"id":"zai-org/GLM-5.3","created":1790366177,"object":"model","owned_by":"Envoy AI Gateway"},{"id":"moonshotai/Kimi-K2.7-Code","created":1790366177,"object":"model","owned_by":"Envoy AI Gateway"},{"id":"nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16","created":1790366177,"object":"model","owned_by":"Envoy AI Gateway"}],"object":"list"}
```

## JSON simple (prompt)


Requête :

```json
{
  "methode": "POST",
  "url": "https://api.inference.cscs.ch/v1/chat/completions",
  "corps": {
    "model": "swiss-ai/Apertus-70B-Instruct-2509",
    "temperature": 0,
    "max_tokens": 300,
    "messages": [
      {
        "role": "system",
        "content": "Réponds UNIQUEMENT par un objet JSON, sans texte autour."
      },
      {
        "role": "user",
        "content": "Donne {\"ville\": <ville principale du Valais>, \"langues\": [<langues officielles>]}."
      }
    ]
  }
}
```

Réponse brute (HTTP 403) :

```
key not authorized for this model
```

## response_format json_schema (strict)


Requête :

```json
{
  "methode": "POST",
  "url": "https://api.inference.cscs.ch/v1/chat/completions",
  "corps": {
    "model": "swiss-ai/Apertus-70B-Instruct-2509",
    "temperature": 0,
    "max_tokens": 300,
    "messages": [
      {
        "role": "user",
        "content": "Dans quel canton se trouve Sion ?"
      }
    ],
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "name": "reponse",
        "schema": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "canton",
            "code_postal_min"
          ],
          "properties": {
            "canton": {
              "type": "string",
              "enum": [
                "VS",
                "VD",
                "GE"
              ]
            },
            "code_postal_min": {
              "type": "integer"
            }
          }
        },
        "strict": true
      }
    }
  }
}
```

Réponse brute (HTTP 403) :

```
key not authorized for this model
```

## tools (tool_choice required)


Requête :

```json
{
  "methode": "POST",
  "url": "https://api.inference.cscs.ch/v1/chat/completions",
  "corps": {
    "model": "swiss-ai/Apertus-70B-Instruct-2509",
    "temperature": 0,
    "max_tokens": 300,
    "messages": [
      {
        "role": "user",
        "content": "Je peux prêter mon minibus de 14 places vendredi."
      }
    ],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "enregistrer_offre",
          "description": "Enregistre une offre d'aide d'un membre du Club.",
          "parameters": {
            "type": "object",
            "additionalProperties": false,
            "required": [
              "nature",
              "places"
            ],
            "properties": {
              "nature": {
                "type": "string",
                "enum": [
                  "objet",
                  "lieu",
                  "competence"
                ]
              },
              "places": {
                "type": "integer"
              }
            }
          }
        }
      }
    ],
    "tool_choice": "required"
  }
}
```

Réponse brute (HTTP 403) :

```
key not authorized for this model
```
