# Fournisseurs et budget financier

Quatre protocoles API : openai (Chat Completions), anthropic (Messages),
gemini (Google generateContent natif) et openai-compatible
(endpoint HTTPS explicite, contrat Chat Completions).
Le fournisseur mock n'effectue aucune requête réseau. Les adaptateurs
réels sont testés avec des fixtures conformes, pas des appels payants.

Pour activer une API dans un manifeste, chaque modèle doit déclarer :

```json
{
  "id": "participant",
  "provider": "openai",
  "model": "IDENTIFIANT_EXACT_CHOISI_PAR_VOUS",
  "api_key_env": "ARENA_OPENAI_KEY",
  "max_input_tokens_per_call": 150000,
  "max_output_tokens": 12000,
  "timeout_seconds": 60,
  "max_retries": 1,
  "parameters": {},
  "pricing": {
    "date": "AAAA-MM-JJ",
    "currency": "USD",
    "input_per_million": "PRIX_OFFICIEL",
    "output_per_million": "PRIX_OFFICIEL"
  }
}
```

Cet exemple est un formulaire, pas un manifeste exécutable. Vérifier les
identifiants exacts, paramètres et tarifs dans la documentation officielle.
Pour Anthropic, utiliser provider anthropic et ARENA_ANTHROPIC_KEY.
Pour Gemini, utiliser provider gemini et ARENA_GEMINI_KEY ; les identifiants
`gemini-…` et `models/gemini-…` sont acceptés. Un endpoint Gemini personnalisé
désigne la racine API, par exemple `https://generativelanguage.googleapis.com/v1beta`.
Pour un endpoint compatible, déclarer endpoint ; seuls HTTPS et
authentification Bearer sont pris en charge. Pas de credentials dans l'URL.

Le manifeste doit aussi déclarer spending.allow_paid_calls=true, un
max_total_usd positif, et des plafonds de session max_input_tokens,
max_output_tokens et max_cost_usd. Sans cela, la validation refuse
l'expérience avant tout appel. Aucun alias de modèle ou prix réel
n'est codé en dur ; les tarifs des tests sont purement synthétiques.

Le plan affiche les noms des variables nécessaires, jamais leurs valeurs.
En cloud, fournir les clés dans les paramètres sécurisés, avec destination
api.openai.com, api.anthropic.com ou generativelanguage.googleapis.com
(ou l’hôte compatible). Les noms
ARENA_* évitent les noms réservés par la plateforme. Ne pas les écrire
dans le manifeste, les prompts, les sources ou le terminal.

## Comptabilité et reprise

Avant l'envoi, une réservation est enregistrée dans SQLite. Le plafond
est contrôlé globalement et par session ; le verrou exclut un deuxième
orchestrateur. L'admission utilise une borne UTF-8 et une borne d'entrée
configurée. Ce plafond financier reste **au mieux** : aucune garantie
universelle de facturation n'est possible entre fournisseurs/tokenizers.
Les coûts sont Decimal, calculés sur usage retourné et tarif daté ;
ils ne sont pas confirmés par une facture.

L'entrée totale OpenAI inclut son cache ; l'entrée Anthropic additionne
entrée normale, cache lu et cache créé. Les tokens de raisonnement sont
un détail de l’output OpenAI lorsqu’exposés, jamais additionnés une seconde fois.
Gemini retourne séparément `candidatesTokenCount` et `thoughtsTokenCount` :
leur somme donne la sortie facturable. `promptTokenCount` inclut le cache.
Tout usage indisponible reste null. Les prix de cache facultatifs
retombent prudemment sur le prix d'entrée ordinaire.

Seul un HTTP 429 explicite peut être retenté, jusqu'à max_retries (0–3).
Un timeout après envoi, un HTTP 5xx, une réponse malformée ou un usage
manquant conserve une réservation et needs_reconciliation. La reprise
ne relance pas ce paiement. Examiner request_id, journaux et facturation
avant une décision manuelle ; aucun endpoint de récupération/idempotence
non garanti n'est inventé.

Les objets natifs nécessaires à la continuation sont conservés : appels
d'outils OpenAI, blocs tool_use et thinking/signature Anthropic, parties natives et
`thoughtSignature` Gemini. Les
branches G1 rejouent une copie de l'historique complet. Aucun résumé
ne remplace silencieusement un checkpoint.

Contrats consultés le 14 octobre 2026 :
- OpenAI SDK officiel : github.com/openai/openai-python,
  types/chat/completion_create_params.py.
- Anthropic SDK officiel : github.com/anthropics/anthropic-sdk-python,
  types/message_create_params.py.
- Tarifs : https://openai.com/api/pricing/ et https://platform.claude.com/docs/en/about-claude/pricing.

Un smoke réel exige vos clés, modèles et plafond explicite. Aucun
smoke réel n'est exécuté par la CI standard.


## Catalogue, seeds et requêtes

Dans l’interface, **Charger les modèles** appelle GET `/v1/models` pour OpenAI
et Anthropic, GET `/v1beta/models` pour Gemini, avec pagination. Gemini exclut
les modèles sans `generateContent`. Les serveurs compatibles utilisent le
chemin `/models` associé à leur endpoint `/chat/completions`. Si le serveur
ne fournit pas cette liste, la saisie manuelle reste disponible. Le catalogue
n’indique pas automatiquement les prix ni la compatibilité de chaque modèle
avec les outils. Charger la liste ne lance pas de génération.

Le champ **Seed du modèle** vaut 0 pour un nouveau profil OpenAI ou Gemini.
Il se retrouve dans `parameters.seed`, puis dans la requête native. Les anciens
profils ne sont pas modifiés automatiquement ; vider le champ supprime la seed.
Les compatibles acceptent le même paramètre si leur serveur le prend en charge.
Anthropic Messages n’expose pas de seed : la validation refuse ce paramètre.
Certains modèles OpenAI peuvent également le refuser ; retirer la seed pour
ces modèles au lieu de supposer qu’elle est ignorée.

Une seed n’est qu’une aide à la reproductibilité, pas une garantie de réponse
identique. L’ensemble des messages, outils, paramètres et le backend doivent
être comparés. Un prompt système identique seul ne suffit pas pour déceler
une fuite de contexte. Les requêtes sont construites à partir de l’historique
de la session sélectionnée ; aucune mémoire de conversation n’est partagée
par les adaptateurs. Les branches appariées héritent volontairement de G0.

Chaque nouvelle intention d’appel conserve le corps complet de la requête,
son SHA-256 et l’endpoint avant exécution. Les en-têtes d’authentification sont
masqués. Les réponses conservent aussi la requête, le modèle retourné et
`system_fingerprint` OpenAI lorsqu’ils sont fournis. Les participants simulés
utilisent la même interface `respond(history, tools, output_limit)` et reçoivent
les prompts et schémas d’outils ; leur requête locale est également journalisée.
Les contrôles fixes d’évaluation reçoivent directement un fichier `.leek` :
ils n’ont aucune conversation de génération et aucun prompt n’est inventé.
Les anciennes archives ne gagnent pas rétroactivement de requêtes natives.

Sources officielles consultées le 15 octobre 2026 :

- [OpenAI — seed et absence de garantie déterministe](https://github.com/openai/openai-python/blob/main/src/openai/types/chat/completion_create_params.py).
- [Anthropic — paramètres Messages, sans seed](https://github.com/anthropics/anthropic-sdk-python/blob/main/src/anthropic/types/message_create_params.py).
- [Google — GenerateContentConfig.seed, au mieux](https://github.com/googleapis/python-genai/blob/main/google/genai/types.py).
