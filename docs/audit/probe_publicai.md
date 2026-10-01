# Sonde Public AI — ce que l'API fait vraiment

> Écrit par `prototype/scripts/sonde_publicai.py` : réponses BRUTES, aucune retouche. La clé n'est jamais écrite ;
> les requêtes sont consignées sans en-tête d'autorisation. Un verdict ne vaut que pour la date, l'hôte et le modèle ci-dessous.

- Date : 2026-10-01 19:10 UTC
- Hôte : `https://api.inference.cscs.ch/v1`
- Clé fournie : oui
- Modèle : `swiss-ai/Apertus-v1.5-70B`
- **État : exécutée contre https://api.inference.cscs.ch/v1 avec le modèle « swiss-ai/Apertus-v1.5-70B »**

| Essai | Verdict | Raison | HTTP | Durée |
|---|---|---|---|---|
| modèles | **SUPPORTED** | 11 modèles listés | 200 | 1245 ms |
| JSON simple (prompt) | **SUPPORTED** | JSON valide avec les clés demandées | 200 | 996 ms |
| response_format json_schema (strict) | **SUPPORTED** | sortie conforme à un schéma absent du prompt | 200 | 707 ms |
| tools (tool_choice required) | **SUPPORTED** | tool_call valide | 200 | 817 ms |
| non-thinking | **SUPPORTED** | aucune trace de raisonnement dans 3 réponses | — | — |

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
    "model": "swiss-ai/Apertus-v1.5-70B",
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

Réponse brute (HTTP 200) :

```
{"id":"chatcmpl-5100e4fb-aa03-4ab6-9ced-35bbb8f22236","object":"chat.completion","created":1790881822,"model":"swiss-ai/Apertus-v1.5-70B","choices":[{"index":0,"message":{"role":"assistant","content":"{\n  \"ville\": \"Sion\",\n  \"langues\": [\"français\", \"allemand\"]\n}","refusal":null,"annotations":null,"audio":null,"function_call":null,"reasoning":null},"logprobs":null,"finish_reason":"stop","stop_reason":68,"token_ids":null,"routed_experts":null}],"service_tier":null,"system_fingerprint":"vllm-0.23.1rc1.dev1029+ga601a9d99-tp4-1381023c","usage":{"prompt_tokens":57,"total_tokens":81,"completion_tokens":24,"prompt_tokens_details":{"cached_tokens":0,"multimodal_tokens":null}},"prompt_logprobs":null,"prompt_token_ids":null,"prompt_text":null,"kv_transfer_params":null,"metrics":null}
```

## response_format json_schema (strict)


Requête :

```json
{
  "methode": "POST",
  "url": "https://api.inference.cscs.ch/v1/chat/completions",
  "corps": {
    "model": "swiss-ai/Apertus-v1.5-70B",
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

Réponse brute (HTTP 200) :

```
{"id":"chatcmpl-c1c224f7-fc8c-41c1-bb41-105709c79b2e","object":"chat.completion","created":1790881823,"model":"swiss-ai/Apertus-v1.5-70B","choices":[{"index":0,"message":{"role":"assistant","content":"{ \n  \"canton\": \"VS\",\n  \"code_postal_min\": 1950\n}","refusal":null,"annotations":null,"audio":null,"function_call":null,"reasoning":null},"logprobs":null,"finish_reason":"stop","stop_reason":null,"token_ids":null,"routed_experts":null}],"service_tier":null,"system_fingerprint":"vllm-0.23.1rc1.dev1029+ga601a9d99-tp4-1381023c","usage":{"prompt_tokens":69,"total_tokens":98,"completion_tokens":29,"prompt_tokens_details":{"cached_tokens":0,"multimodal_tokens":null}},"prompt_logprobs":null,"prompt_token_ids":null,"prompt_text":null,"kv_transfer_params":null,"metrics":null}
```

## tools (tool_choice required)


Requête :

```json
{
  "methode": "POST",
  "url": "https://api.inference.cscs.ch/v1/chat/completions",
  "corps": {
    "model": "swiss-ai/Apertus-v1.5-70B",
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

Réponse brute (HTTP 200) :

```
{"id":"chatcmpl-98e5c916-349e-44a2-aac9-444f0b803878","object":"chat.completion","created":1790881823,"model":"swiss-ai/Apertus-v1.5-70B","choices":[{"index":0,"message":{"role":"assistant","content":"","refusal":null,"annotations":null,"audio":null,"function_call":null,"tool_calls":[{"id":"chatcmpl-tool-93d1091597c06cb2","type":"function","function":{"name":"enregistrer_offre","arguments":"{\"nature\": \"lieu\", \"places\": 14}"}}],"reasoning":null},"logprobs":null,"finish_reason":"tool_calls","stop_reason":null,"token_ids":null,"routed_experts":null}],"service_tier":null,"system_fingerprint":"vllm-0.23.1rc1.dev1029+ga601a9d99-tp4-1381023c","usage":{"prompt_tokens":122,"total_tokens":159,"completion_tokens":37,"prompt_tokens_details":{"cached_tokens":32,"multimodal_tokens":null}},"prompt_logprobs":null,"prompt_token_ids":null,"prompt_text":null,"kv_transfer_params":null,"metrics":null}
```
