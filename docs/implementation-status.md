# État du plan de reprise

Le plan historique est conservé dans cloud-roadmap.md. Le parcours livré
est décrit dans complete-experiment.md ; les commandes de combat initiales
restent disponibles.

| Lot | Réalisation |
|---|---|
| A — Linux | Bootstrap versionné et vérifié, CI, chemins avec espaces, archives Gradle stables, fingerprint récursif, identités/provenance séparées et backend Docker optionnel. |
| B — Stockage | Schémas validés, migration SQLite 1→2, checkpoints transactionnels, filiation, artefacts par hash, verrou d'écrivain et export autonome. |
| C — Outils/MCP | Huit outils communs, SDK MCP verrouillé, client stdio de test, quotas, refus des accès croisés et environnement worker sans clés. |
| D — Corpus | Index, règles, syntaxe, comportements des fonctions des exemples, attribution au moteur figé et trois prompts français versionnés. |
| E — Sessions | Fournisseur simulé, réparation après diagnostic, tests et replays réels, soumissions invalides/absentes, budgets, pannes simulées et reprise. |
| F — API/coûts | OpenAI/compatible et Anthropic, fixtures conformes, historique natif, usages/cache, Decimal, réservations globales, retries bornés et états distants inconnus bloqués. |
| G — Adaptation | G0, checkpoints clonés en contrôle/feedback, code adverse masqué, seeds séparées, G1 contemporain et évaluations sur panel G0/contrôles communs. |
| H — Rapports | JSON/CSV/Markdown/HTML, matrices, invalidités et absences visibles, agrégation par modèle, comparaison appariée, bootstrap exploratoire stratifié et Pareto sans coût inconnu. |

Le corpus décrit les fonctions des exemples et renvoie aux signatures
pour les autres fonctions ; il ne constitue pas une encyclopédie complète
de leurs comportements. Les répliques simulées ne sont pas des générations
effectuées par des LLM.

Les validations d'intégration utilisent le vrai moteur. Les adaptateurs
API sont validés hors ligne : un smoke réel exige les clés, modèles
exacts, tarifs et plafond financier explicitement choisis. Aucun appel
payant ne fait partie de la CI ou des démonstrations.

Les intervalles sont conditionnels au panel figé et exploratoires.
Ils ne sont calculés qu'avec au moins deux conversations complètes par
modèle ; la démo à une réplication n'en produit pas. Les prix calculés
ne sont pas des factures confirmées. Une composante d'usage indisponible
reste inconnue, et une réservation distante incertaine n'est pas relancée.

Hors périmètre du plan : service public multi-utilisateur, nouveaux
langages, infrastructure distribuée, interface web riche, batch avancé
et divulgation du code adverse. La CI GitHub doit être observée après
le push ; la configuration cloud enregistrée doit être publiée par
l'utilisateur pour un nouvel environnement.
