# LLM Arena

<p align="center"><img src="docs/assets/arena-logo.png" alt="LLM Arena — robot gladiateur" width="360"></p>

Arène locale pour préparer, exécuter et comparer des stratégies **LeekScript 4**, avec le moteur officiel Leek Wars figé au commit `b99a174dd938260d9e47b2e65a208cb32230e26e`.

Le socle exécute réellement les combats : analyse de scripts, équipes symétriques, round-robin aller-retour, miroirs séparés, compteurs d'opérations, replays, empreintes des sources et reprise après interruption. Les trois stratégies fournies sont des contrôles écrits à la main, pas des résultats de LLM.

## Interface web locale

Après installation, lancer `.\.venv\Scripts\python.exe -m arena ui --open`
sous Windows, ou `.venv/bin/python -m arena ui --open` sous Linux.
L’interface s’ouvre sur **http://127.0.0.1:8765** : participants et tarifs,
configuration et suivi des compétitions, conversations intégrales,
versions/diffs du code, lecteur graphique schématique des combats,
bilans et agrégations entre compétitions comparables.
Voir [le guide de l’interface](docs/ui.md), qui explique aussi les scores
et les limites des démonstrations simulées. Aucun Node.js n’est requis.

## Démarrage

Sous **Windows natif (PowerShell)**, installer Python ≥ 3.11, Git et un
JDK 25 complet, puis :

```powershell
py -3 scripts/bootstrap.py
.\.venv\Scripts\python.exe -m arena doctor
.\.venv\Scripts\python.exe -m arena experiment run configs/offline-complete.json --out runs/mon-premier-test
```

Voir [le guide Windows](docs/windows.md) pour l'installation, les combats,
la reprise et la validation. Aucune activation PowerShell, WSL ou Bash
n'est nécessaire. La démo utilise des participants simulés et de vrais
combats, sans appel API payant.

Sous Linux x86_64 : `bash scripts/bootstrap-linux.sh`, puis
`bash scripts/validate-linux.sh`. Voir [le guide Linux](docs/linux.md)
pour le proxy, les checksums, la CI et les limites.

Prérequis : **Python ≥ 3.11, JDK 25, Git et Gradle 9.3.1**.
Le moteur et les adaptateurs API utilisent la bibliothèque standard ;
le transport MCP utilise le SDK verrouillé installé par le bootstrap.
Exécuter les commandes depuis le dépôt et activer .venv pour MCP.
Le bootstrap Linux installe Java ; le bootstrap portable utilise le JDK 25
installé via JAVA_HOME ou PATH. Les deux configurent un cache Gradle local.

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

Les temps `turn_elapsed_ns` mesurent le temps écoulé autour des tours, **pas le temps CPU**.
Les opérations sont le compteur natif LeekScript. Le score est
`(victoires + 0,5 × nuls) / matchs terminés`, hors miroirs.
Le cycle complet ajoute agrégations par modèle, comparaisons appariées
exploratoires et coûts audités.

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

Le [cycle complet G0/G1](docs/complete-experiment.md) est disponible avec
fournisseurs simulés, outils MCP, branches contrôle/feedback, panel commun,
journal SQLite et rapports JSON/CSV/Markdown/HTML.
Les [adaptateurs OpenAI/compatible et Anthropic](docs/providers.md) sont
testés hors ligne ; leur activation exige modèles, tarifs et plafond
financier explicites. Aucun appel payant n'est lancé par les démos ou la CI.
Python/JavaScript restent optionnels ; TypeScript est hors périmètre.

L'exécution utilise un processus Java séparé avec heap, délai et quotas de
sortie, ou un backend Docker optionnel sans réseau. Voir les limites et
les commandes dans le guide du cycle complet. Un service public pour des
soumissions hostiles reste hors périmètre.
