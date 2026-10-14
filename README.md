# LLM Arena

Première implémentation d'une arène locale pour comparer des stratégies **LeekScript 4**, avec le moteur officiel Leek Wars figé au commit `b99a174dd938260d9e47b2e65a208cb32230e26e`.

Le socle exécute réellement les combats : analyse de scripts, équipes symétriques, round-robin aller-retour, miroirs séparés, compteurs d'opérations, replays, empreintes des sources et reprise après interruption. Les trois stratégies fournies sont des contrôles écrits à la main, pas des résultats de LLM.

## Démarrage

Sous Linux x86_64 : `bash scripts/bootstrap-linux.sh`, puis
`bash scripts/validate-linux.sh`. Voir [le guide Linux](docs/linux.md)
pour le proxy, les checksums, la CI et les limites.

Prérequis : **Python ≥ 3.11, JDK 25, Git et Gradle 9.3.1**. Aucun paquet Python tiers n'est nécessaire. Exécuter les commandes depuis ce dépôt. Java 25 doit être sur le PATH ; le bootstrap remplace localement une éventuelle configuration Gradle pointant vers un ancien JDK, sans modifier la configuration globale.

```powershell
python -m arena setup
python -m arena doctor
python -m arena analyze examples/strategies/rush
python -m arena fight examples/strategies/rush examples/strategies/passive
python -m arena plan examples/tournament.json
python -m arena tournament examples/tournament.json --out runs/my-first-tournament
```

`setup` télécharge les sources publiques, vérifie les commits et compile le moteur. Gradle est recherché sur le PATH puis dans son cache local ; si nécessaire, fournir `--gradle CHEMIN_VERS_GRADLE`. Le wrapper amont est trop ancien pour ce build. Après le build initial, les combats sont locaux et ne nécessitent pas de service Leek Wars, de base de données ni de clé d'API.

Le rapport est écrit dans `runs/my-first-tournament/report.md` et `report.json`. Le tournoi fourni exécute **12 confrontations classées + 6 miroirs**, sur deux seeds. Pour reprendre une exécution avec les mêmes sources, moteur et paramètres :

```powershell
python -m arena tournament examples/tournament.json --out runs/my-first-tournament --resume
python -m arena report runs/my-first-tournament
```

Les résultats terminés sont vérifiés et réutilisés ; les combats interrompus ou en panne sont rejoués dans un nouveau dossier d'essai. Ne lancer qu'un processus sur un même dossier de tournoi. Pour une nouvelle expérience ou un moteur modifié, utiliser un nouveau dossier.

## Ajouter une stratégie

Une [expérience G0 hors ligne](docs/offline-experiment.md) est disponible :
`python -m arena experiment run configs/offline-demo.json --out runs/offline-demo`.
Elle orchestre des fournisseurs simulés, les outils de préparation et un
tournoi réel, sans clé ni appel API.

Créer un dossier avec `main.leek` et éventuellement des fichiers `.leek` inclus. Les chemins dans le manifeste sont relatifs à ce manifeste. Exemple d'inscription :

```json
{"id": "model-a-rep-1", "path": "strategies/model-a-rep-1", "entrypoint": "main.leek", "model": "exact-model-id", "replicate": 1}
```

Chaque membre d'une équipe exécute le même point d'entrée ; le script peut choisir son rôle avec l'API du jeu. Les deux équipes ont les mêmes caractéristiques. Les includes sont limités au dossier de la stratégie. Seuls les fichiers `.leek` sont soumis, au maximum 128 fichiers et 2 Mo. Les scripts et tous leurs includes sont hachés avant leur copie dans l'expérience.

Le manifeste contrôle `team_size`, `max_turns` (1–64), les statistiques et l'équipement de chaque entité. `cores` fixe le budget d'opérations par tour et `ram` la mémoire LeekScript. Une carte personnalisée peut fournir `obstacles` (objet `{"300": true}`), `team1` et `team2` (cases de départ explicites). La grille du moteur est de 18×18, avec des cases numérotées de 0 à 612. Sans carte explicite, le moteur génère carte et placement depuis la seed.

Les champs non pris en charge sont refusés pour éviter des paramètres silencieusement ignorés. En particulier, le champ amont d'exemple `max_operations_per_entity` n'est pas appliqué : utiliser `entity.cores`.

## Résultats et reproductibilité

- `experiment.json` : configuration, calendrier, versions et empreintes du moteur, du runner et des sources.
- `submissions/` : sources figées des participants.
- `matches/…/attempt-N/` : scénario exact, sources de chaque côté, données de jeu, résultat brut, logs et métriques.
- `records/` : dernier essai de chaque confrontation, conservé après chaque combat.
- `report.md` et `report.json` : scores descriptifs par stratégie, matrice des confrontations et miroirs.

Le vainqueur moteur est **0 pour la première équipe, 1 pour la seconde et −1 pour un nul**. Les numéros d'équipes du replay sont en revanche 1 et 2. Le compteur `duration` du moteur peut atteindre `max_turns + 1` à l'épuisement des tours ; il est conservé tel quel dans les résultats.

Une erreur dans une IA reste un résultat de jeu et apparaît dans ses métriques. Une panne moteur ou le délai du processus complet produit un résultat non classé, sans défaite artificielle. `--timeout 90` contrôle ce délai global ; ce n'est pas le budget de calcul d'un tour.

Les temps `turn_elapsed_ns` mesurent le temps écoulé autour de l'exécution des tours, **pas le temps CPU**. Les opérations sont le compteur natif LeekScript. Le score est `(victoires + 0,5 × nuls) / matchs terminés`, hors miroirs. Les statistiques par modèle, intervalles d'incertitude et coûts LLM viendront avec l'orchestrateur de générations.

```powershell
python -m arena verify examples/strategies/rush examples/strategies/single-shot
python -m unittest discover -s tests -v
```

`verify` répète un duel dans deux processus et compare le replay, le résultat et les opérations, en excluant les mesures de temps et les messages debug. Ce contrôle est une vérification locale, pas une preuve de déterminisme pour tous les scripts et toutes les machines. Les tests d'intégration sont activés lorsque le moteur est compilé.

## Documentation et suite

- [Contrat de soumission et guide de départ](docs/authoring.md).
- [API figée : 378 fonctions et 416 constantes](docs/leekscript-v1/api.md), avec données d'équipement JSON et empreintes. C'est une référence de signatures et de valeurs, pas encore une documentation complète des comportements.
- [Audit du moteur et des limites](docs/engine-audit.md).
- [Protocole expérimental cible](docs/protocol.md).

Pour régénérer une référence dans un nouveau dossier : `python -m arena docs --out docs/new-snapshot`.

La prochaine tranche est l'orchestrateur de conversations : adaptateurs fournisseurs, budgets et usages de tokens, outils MCP de préparation, puis générations avec/sans feedback. Aucun appel payant à un LLM n'est implémenté ou lancé dans cette première tranche. Python/JavaScript restent optionnels ; TypeScript est hors périmètre.

L'exécution actuelle utilise un processus Java séparé, une limite mémoire, un délai global et un résolveur d'includes par soumission. L'isolation par conteneur pour des soumissions publiques hostiles reste à ajouter avant un service ouvert.
