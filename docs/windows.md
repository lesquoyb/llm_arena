# Windows natif (PowerShell)

Les combats, tournois, expériences G0/G1, outils MCP et exports peuvent
s'exécuter avec Python et Java Windows, sans WSL ni Bash. La CI Windows
construit le moteur et exécute les mêmes tests d'intégration que Linux,
y compris le cycle G0/G1, la reprise après interruption et l'export.
L'ajout de cette CI ne vaut pas encore constat de réussite : consulter
le workflow **Windows native engine** après publication des changements.

## 1. Installer les prérequis

- [Python 3.11 ou plus récent](https://www.python.org/downloads/windows/),
  avec le lanceur `py` (Python 3.12 est utilisé dans la CI).
- [Git pour Windows](https://git-scm.com/downloads/win), accessible depuis PowerShell.
- Un **JDK 25 complet**, par exemple [Eclipse Temurin 25](https://adoptium.net/temurin/releases/?version=25).
  Choisir le paquet JDK Windows correspondant à votre machine.
  Configurer `JAVA_HOME` vers le dossier du JDK, ou ajouter son sous-dossier
  `bin` au `PATH`, puis ouvrir un nouveau terminal.

Gradle 9.3.1 et les dépendances Python sont installés automatiquement
par le script ci-dessous. L'installation initiale nécessite Internet ;
les combats et la démo simulée deviennent ensuite entièrement locaux.

## 2. Installer le projet

```powershell
git clone https://github.com/lesquoyb/llm_arena.git
cd llm_arena
py -3 scripts/bootstrap.py
```

Pour un dépôt déjà cloné, se placer dans ce dépôt et lancer seulement
la dernière commande. Le bootstrap vérifie le JDK, télécharge Gradle
avec contrôle SHA-256, crée `.venv`, installe MCP et compile le moteur figé.
Il conserve Gradle dans `.arena/tools` et son cache dans
`.arena/gradle-portable`, sans modifier l'installation système.
`ARENA_TOOLS_DIR` peut modifier le dossier des outils.

Si le JDK n'est pas détecté, définir son chemin réel pour le terminal courant :

```powershell
$env:JAVA_HOME = 'C:\Program Files\Eclipse Adoptium\VOTRE_DOSSIER_JDK_25'
py -3 scripts/bootstrap.py
```

Cette valeur est un exemple à remplacer. Le bootstrap donne la priorité
à `JAVA_HOME`, puis cherche Java dans le `PATH`.

## 3. Ouvrir l’interface graphique

```powershell
.\.venv\Scripts\python.exe -m arena ui --open
```

Le navigateur s’ouvre sur http://127.0.0.1:8765. On peut y configurer les
participants et leurs tarifs, gérer les compétitions, consulter les prompts,
versions du code et résultats, et rejouer les combats sur une carte.
Garder le terminal ouvert. Voir [le guide de l’interface](ui.md).

## 4. Essayer un combat et une expérience

Lancer directement le Python du projet évite d'avoir à activer un script
PowerShell ou modifier sa politique d'exécution :

```powershell
.\.venv\Scripts\python.exe -m arena doctor
.\.venv\Scripts\python.exe -m arena fight examples/strategies/rush examples/strategies/passive
.\.venv\Scripts\python.exe -m arena experiment plan configs/offline-complete.json
.\.venv\Scripts\python.exe -m arena experiment run configs/offline-complete.json --out runs/mon-premier-test
```

La démo compare des **participants simulés**, qui fournissent des stratégies
prédéfinies. Les combats Java sont réels ; aucun LLM ni appel API payant
n'intervient. Le cycle prévoit 80 combats d'évaluation et des essais de
préparation. Lire `runs/mon-premier-test/analysis.md` pour les scores et
`report.md` pour l'état d'exécution.

Pour reprendre une interruption, consulter l'état et exporter :

```powershell
.\.venv\Scripts\python.exe -m arena experiment resume runs/mon-premier-test
.\.venv\Scripts\python.exe -m arena experiment status runs/mon-premier-test
.\.venv\Scripts\python.exe -m arena experiment export runs/mon-premier-test --out runs/mon-export
```

Utiliser un **nouveau dossier** pour une nouvelle expérience ou un nouvel
export. Reprendre exige le même code, la même configuration et le même
runtime ; un run Linux ne se reprend pas directement sous Windows.
Les résultats exportés restent lisibles sur les deux plateformes.

## 5. Validation et outils avancés

```powershell
.\.venv\Scripts\python.exe scripts/validate.py
```

Cette commande vérifie le moteur, lance toute la suite de tests, puis
un tournoi de 18 combats et une reprise sans recalcul. Elle peut prendre
plusieurs minutes. Le serveur MCP se lance avec le même Python Windows ;
voir le [guide du cycle complet](complete-experiment.md#mcp).
Pour les clés API, modèles et budgets explicites, voir
[le guide des fournisseurs](providers.md).

Le backend par défaut est un processus Java natif avec heap limité,
délai global et surveillance de la taille des sorties. Sous Windows,
la limite de 8 Mo par fichier est surveillée périodiquement et peut être
brièvement dépassée ; sous Linux une limite système s'ajoute à ce contrôle.
L'arrêt utilise `taskkill /T /F` sous Windows pour terminer aussi les enfants.
Les verrous sont libérés par le système si le processus se termine.

Le script optionnel de construction du worker Docker reste un outil Linux ;
il n'est pas nécessaire pour l'exécution native décrite ici.
