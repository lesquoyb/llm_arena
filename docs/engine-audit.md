# Audit du moteur retenu

Commit générateur : `b99a174dd938260d9e47b2e65a208cb32230e26e`.
Sous-module LeekScript : `8152f399faf7b418bbc5b2216d755c3822cda23b`.
Constats issus des sources locales, le 13 octobre 2026.

## Limites de temps et opérations

Dans `PolyglotEntityAI.java`, `DEFAULT_TURN_WALL_CLOCK_LIMIT_MS = 5_000` est un garde-fou par tour ; `MAX_WALL_CLOCK_TIMEOUTS = 3` est le nombre de dépassements avant désactivation, pas une limite de trois secondes. La méthode publique `setTurnWallClockLimitMs` permet déjà de régler la durée.

Le cas problématique décrit par le guide concerne une stratégie qui borne sa recherche avec `getOperations()`. Si son calcul Python/JavaScript n'incrémente pas le compteur, elle poursuit sa recherche jusqu'au délai de temps sans rendre son action. Allonger le délai retarde l'interruption, mais ne rétablit pas le comptage manquant.

Le code de ce commit a évolué par rapport au guide : `getOperations()` utilise en priorité un compteur de statements déterministe fourni par l'isolate custom, avec des facteurs de calibration. Le calcul synthétique par temps CPU/temps écoulé reste le chemin de secours si ce compteur est absent ou échoue. Le support polyglotte n'a pas été exécuté dans cette tranche.

En LeekScript, `EntityAI.applyEntityBudgets()` fixe le budget d'opérations à `cores × 1_000_000` (plafonné à un entier Java), et la mémoire à `min(50, ram) × 8_000_000` unités du runtime. Le test avec une boucle infinie et un cœur vérifie que le moteur interrompt bien le calcul et signale un dépassement d'opérations. Aucune constante du moteur n'est modifiée.

## Adaptation du lanceur

Le `Scenario.fromFile` amont ne lit pas la carte ni le champ `max_operations_per_entity` de son scénario d'exemple. Il ne restitue pas non plus le propriétaire de l'IA depuis `ai_owner`. L'adaptateur de l'arène applique explicitement la carte, le contexte de test, le type équipe et le propriétaire de chaque côté ; les budgets passent par les caractéristiques reconnues.

Le gestionnaire local de registres amont tente une connexion PostgreSQL. L'arène le remplace par des registres initialement vides et non persistés. Le gestionnaire de statistiques local est étendu pour exposer les opérations, temps écoulés, tours, erreurs et dépassements par équipe.

Les sources amont ne sont pas modifiées. Un script d'initialisation Gradle retire uniquement la dépendance binaire native polyglotte du build. Les autres dépendances nécessaires à la compilation des classes du moteur restent présentes. Le wrapper amont pointe vers Gradle 8.5 ; l'arène exige Gradle 9.3.1 avec Java 25.

## Interprétation des mesures

`Fight.getWinner()` renvoie un index d'équipe à partir de zéro ; les entités sérialisées dans le replay utilisent `team + 1`. Une égalité renvoie −1. Cette conversion est couverte par des combats réels avec inversion des côtés.

`Fight.startTurn()` mesure ses tours avec `System.nanoTime()`. Ces durées sont du temps écoulé et ne sont pas présentées comme des mesures CPU. La signature de reproductibilité exclut les temps, conserve les actions, la carte, les entités, les opérations et le résultat.

Les tests confirment la reproductibilité sur les stratégies de contrôle et les seeds testées. Ils ne permettent pas de généraliser à toutes les fonctions de temps ou sources d'aléatoire du langage.

Sources amont : [générateur au commit retenu](https://github.com/leek-wars/leek-wars-generator/tree/b99a174dd938260d9e47b2e65a208cb32230e26e), [LeekScript au commit retenu](https://github.com/leek-wars/leekscript/tree/8152f399faf7b418bbc5b2216d755c3822cda23b).
