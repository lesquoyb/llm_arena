# Fournisseurs et budget financier

Trois modes API : openai (Chat Completions), anthropic (Messages) et
openai-compatible (endpoint HTTPS explicite, contrat Chat Completions).
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
Pour un endpoint compatible, déclarer endpoint ; seuls HTTPS et
authentification Bearer sont pris en charge. Pas de credentials dans l'URL.

Le manifeste doit aussi déclarer spending.allow_paid_calls=true, un
max_total_usd positif, et des plafonds de session max_input_tokens,
max_output_tokens et max_cost_usd. Sans cela, la validation refuse
l'expérience avant tout appel. Aucun alias de modèle ou prix réel
n'est codé en dur ; les tarifs des tests sont purement synthétiques.

Le plan affiche les noms des variables nécessaires, jamais leurs valeurs.
En cloud, fournir les clés dans les paramètres sécurisés, avec destination
api.openai.com ou api.anthropic.com (ou l'hôte compatible). Les noms
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
un détail de l'output lorsqu'exposés, jamais additionnés une seconde fois.
Tout usage indisponible reste null. Les prix de cache facultatifs
retombent prudemment sur le prix d'entrée ordinaire.

Seul un HTTP 429 explicite peut être retenté, jusqu'à max_retries (0–3).
Un timeout après envoi, un HTTP 5xx, une réponse malformée ou un usage
manquant conserve une réservation et needs_reconciliation. La reprise
ne relance pas ce paiement. Examiner request_id, journaux et facturation
avant une décision manuelle ; aucun endpoint de récupération/idempotence
non garanti n'est inventé.

Les objets natifs nécessaires à la continuation sont conservés : appels
d'outils OpenAI, blocs tool_use et thinking/signature Anthropic. Les
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
