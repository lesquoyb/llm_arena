# LLM Arena — cadrage initial

Évaluer la capacité des modèles à écrire, déboguer et améliorer une stratégie de combat Leek Wars avec une documentation et un budget contrôlés. Le résultat mesure une compétence située (programmation et stratégie dans ce jeu), pas une compétence générale en code.

Ce document propose le protocole cible. Le socle local LeekScript est implémenté ; voir le README à la racine pour les fonctionnalités disponibles et les étapes restantes.

## Faisabilité à vérifier

La première version utilise exclusivement LeekScript 4. Python et JavaScript restent des extensions éventuelles ; TypeScript est retiré du périmètre. Les fonctions et constantes du jeu sont injectées par le moteur.

Le socle fonctionne directement sous Windows avec Java 25 et Gradle 9.3.1. Le binaire natif polyglotte Linux est exclu du build LeekScript. Ne pas confondre le frontend du site avec le générateur de combats.

L'audit du commit retenu montre un compteur polyglotte déterministe avec repli temporel : le guide décrit surtout ce dernier. Les 5 secondes par tour et les 3 dépassements avant désactivation concernent le chemin polyglotte. LeekScript utilise son budget d'opérations dérivé des cœurs. Voir engine-audit.md. Une limite de temps du processus complet reste un garde-fou d'infrastructure et n'attribue pas de défaite à un participant.

Sources consultées le 13 octobre 2026 :

- https://github.com/leek-wars/leek-wars-generator
- https://github.com/leek-wars/leek-wars-generator/blob/master/POLYGLOT_PORTING_GUIDE.md
- https://github.com/leek-wars/leekscript

## Unité expérimentale et règles

Une stratégie est identifiée par (modèle exact, langage, réplication, génération, condition de feedback). Une réplication démarre dans une conversation indépendante. Les générations suivantes poursuivent cette conversation, avec une politique identique de conservation du contexte.

Fixer les caractéristiques, équipements et taille des équipes. Autoriser un fichier commun ou plusieurs rôles selon une règle annoncée. Commencer avec du 2 contre 2 et un équipement identique, puis introduire des scénarios spécialisés. Le moteur, les données de jeu, les compilateurs, prompts et documents sont figés par version et hash.

Chaque participant dispose du même environnement d'agent : lecture/écriture de son espace, consultation de sa documentation, analyse et tests locaux. Aucun accès aux secrets des fournisseurs, aux espaces concurrents ou aux scénarios d'évaluation cachés. Isoler également l'exécution du code soumis, avec limites de ressources et accès réseau désactivé.

Le livrable est un répertoire source avec un point d'entrée déclaré. À l'échéance, figer et hacher le livrable. Ne pas sélectionner manuellement la meilleure réplication. Une erreur de compilation ou d'exécution appartient aux résultats ; une panne d'infrastructure déclenche une relance documentée selon une règle préalable.

## Documentation et outils

Produire un corpus local figé : règles du jeu communes, fonctions et constantes disponibles, signatures, retours, coûts documentés, cycle de vie, modules autorisés et exemples minimaux. Vérifier les exemples sur le moteur retenu. Commencer avec LeekScript ; si Python/JavaScript sont ajoutés, fournir une référence adaptée à leur runtime.

Un index court est fourni dans le prompt ; les références complètes restent lisibles dans des fichiers locaux. Tous ont accès aux mêmes informations de jeu. Enregistrer les fichiers consultés. LeekScript peut tester l'apprentissage d'une API inhabituelle, mais son absence des données d'entraînement ne peut pas être garantie.

Le MCP expose une interface stable :

- `analyze(entrypoint)` : diagnostics de compilation/chargement.
- `test(entrypoint, scenario_id, seed)` : combat sur un scénario d'entraînement autorisé.
- `read_replay(test_id, offset, limit)` : logs paginés et bornés.

Le service choisit les chemins autorisés et n'accepte pas de commandes shell arbitraires. Les adversaires de préparation sont fixes et communs à tous. Les appels d'outils, erreurs et résultats sont archivés.

## Budgets

Préannoncer un plafond de génération, un plafond de contexte cumulé facturé, un nombre de tests et un délai de sécurité. Arrêter au premier plafond atteint. Enregistrer tokens d'entrée, entrée en cache, sortie et raisonnement selon les champs réellement fournis ; marquer les champs indisponibles. Conserver les réponses d'usage brutes pour éviter les doubles comptes.

Les tokens des différents tokenizers ne sont pas une unité universelle de travail. Publier des pistes séparées : budget de tokens annoncé et budget monétaire égal. Enregistrer fournisseur, identifiant/version du modèle, paramètres, effort de raisonnement, tarif daté et coût effectif. Les modèles locaux ont des coûts d'infrastructure distincts.

## Tournoi

Séparer les seeds/scénarios de préparation, ceux utilisés pour le feedback et un jeu final réservé. Pour chaque paire de stratégies, jouer les mêmes seeds dans les deux positions. Vérifier ce que l'inversion change réellement : placement, équipes et initiative. Tester les sources d'aléatoire propres aux langages.

Inclure les stratégies de réplications différentes du même modèle. Les combats d'une stratégie contre elle-même sont des diagnostics séparés et n'entrent pas dans le score principal.

Pour N stratégies et S seeds, un round-robin avec deux positions demande N(N−1)S combats, hors miroirs. Répéter exactement un combat déterministe n'ajoute aucune information ; privilégier des seeds et configurations variées. Répéter certaines seeds sert à auditer le déterminisme.

## Mesures

Publier d'abord la matrice de victoires/nuls/défaites, le taux de validité et le score moyen (1 victoire, 0,5 nul, 0 défaite). Pondérer également les modèles et scénarios pour qu'un modèle avec davantage de stratégies ne pèse pas plus lourd.

Présenter la dispersion entre conversations indépendantes et des intervalles d'incertitude respectant le regroupement par réplication et les paires de matchs. Multiplier les combats d'un même script ne remplace pas les réplications de génération.

Un classement Elo peut servir à l'affichage, mais la matrice reste centrale : des stratégies peuvent former des cycles. Ajouter ensuite un modèle statistique de classement si les résultats le justifient.

Mesurer séparément ressources de jeu (points d'action/mouvement), compteur d'opérations moteur, temps CPU, temps écoulé, mémoire et dépassements. Comparer le compteur surtout au sein d'un runtime. Mesurer le CPU sur matériel figé, avec chauffe contrôlée et concurrence limitée.

Pour les coûts, préférer les courbes performance/budget et la frontière de Pareto à un unique quotient qualité/prix. Conserver les coûts cumulés de toutes les générations.

## Adaptation et contrôle

Après la génération initiale, cloner chaque conversation et son livrable dans deux branches appariées :

- Contrôle : « améliore ta stratégie », sans résultats du tournoi.
- Feedback : même budget et même demande, avec résultats structurés et logs bornés du tour précédent.

Les deux branches gardent les mêmes droits aux tests d'entraînement. Le code adverse reste masqué dans l'expérience principale. Une troisième condition avec code adverse pourra mesurer séparément l'effet de sa divulgation.

Figer toutes les soumissions avant le tournoi suivant. Mesurer les nouvelles générations contre leurs contemporaines, les stratégies figées de génération 0 et des adversaires fixes. Réserver le jeu final à une mesure terminale pour limiter le surapprentissage. Les écarts feedback/contrôle sont évalués sur des adversaires communs, sans dépendre uniquement du classement mouvant.

## Architecture proposée

Un orchestrateur Python pilote les adaptateurs fournisseurs, conversations, budgets et reprises. Un worker moteur exécute les scénarios. Le MCP appelle le même service de test. SQLite conserve les métadonnées ; les sources, prompts, documents, réponses brutes et replays sont des artefacts immuables. Les tâches ont des identifiants idempotents pour reprendre après interruption sans refacturer inutilement.

## Pilote proposé

1. Figer un commit moteur et obtenir deux IA minimales qui combattent localement.
2. Vérifier sorties, vainqueur, nuls, erreurs, seeds, inversion des positions et stabilité des replays.
3. Construire et valider le corpus LeekScript et les outils de préparation.
4. Tester 3 modèles × 3 conversations indépendantes, en LeekScript uniquement, à génération 0.
5. Avec 9 stratégies et 10 seeds en deux positions : 720 combats, plus diagnostics miroir.
6. Ajouter une génération avec branches contrôle/feedback, puis éventuellement Python et JavaScript après audit de leur runtime.

Trois réplications suffisent à un pilote technique, pas à établir un classement définitif. Choisir les identifiants de modèles disponibles au moment de l'exécution plutôt que les noms provisoires des notes.

## Réduction des coûts

Garder un préfixe de prompt stable et vérifier les usages de cache réellement facturés. Fournir des fichiers indexés plutôt que des URL web variables. Retourner des résumés de combats et lire les logs à la demande, avec des plafonds communs. Mettre en cache les combats par code, moteur, configuration et seed uniquement si le déterminisme est validé.

Les traitements batch peuvent être utiles pour des appels indépendants si le fournisseur les permet ; une boucle interactive avec outils exige une orchestration en plusieurs étapes. Vérifier les capacités et tarifs de chaque fournisseur lors de son intégration. Commencer avec un langage et peu de générations réduit directement le coût expérimental.
