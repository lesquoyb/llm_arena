# Cycle complet G0 → G1

```bash
source .venv/bin/activate
python -m arena experiment plan configs/offline-complete.json
python -m arena experiment run configs/offline-complete.json --out runs/complete-demo
python -m arena experiment resume runs/complete-demo
python -m arena experiment export runs/complete-demo --out runs/complete-export
```

Le manifeste de démonstration crée deux conversations G0, puis deux
branches par conversation : contrôle et feedback. Ce sont des fixtures
simulées, avec de vrais diagnostics et combats Java, pas des générations
effectuées par un LLM. Les branches partagent exactement le même code
et historique G0 avant le nouveau message d'amélioration.

Préparation : seed 17, contrôle passif, deux positions. Feedback :
seed 101. Mesure finale : seed 301, inaccessible aux outils des sessions.
Les scripts sont tous figés avant leur round. Le feedback expose seulement
résultats pseudonymisés, propres métriques et courts extraits numériques
du replay, sans code adverse, chemins ni logs système.

La démonstration prévoit 4 combats G0, 16 combats contemporains G1 et
60 combats de référence : G0 et les deux branches G1 jouent tous
contre le même panel G0 et les contrôles fixes, dans les deux positions.
Les matchs contre soi dans les rounds sont des miroirs séparés.
Les rencontres contre le panel de référence incluent le point d'ancrage
G0 de chaque trajectoire et sont publiées comme mesure contre panel.

## Rapports et artefacts

- report.json/report.md : synthèse d'exécution.
- tournament/ et g1-tournament/ : matrices contemporaines distinctes.
- evaluations/g0-panel et g1-panel : mêmes adversaires et fixtures.
- feedback/ : données réellement fournies aux seules branches feedback.
- analysis.json/csv/md/html : scores par stratégie, génération, modèle
  et type de panel ; effets appariés ; coût total et trajectoires.
- journal.sqlite et artifacts/ : checkpoints, appels, usages, matches
  et filiation auditables, avec empreintes des artefacts.
- export.json : inventaire autonome des fichiers et SHA-256.

Les absences, invalidités et pannes restent visibles. Le score est
conditionnel aux soumissions présentes ; il ne mesure pas une performance
globale qui pénaliserait arbitrairement les générations absentes.
Les modèles sont agrégés avec poids égal par réplication. Les matrices
conservent aussi les rencontres entre réplications du même modèle.
L'intervalle bootstrap rééchantillonne les conversations appariées en
gardant leurs fixtures ensemble ; il reste exploratoire et ne modélise
pas toutes les dépendances entre adversaires. La démo, à une réplication
par modèle, ne permet aucune conclusion scientifique sur de vrais modèles.
Le coût nul des mocks est explicitement une simulation ; les coûts
inconnus ne participent pas à la frontière de Pareto.

L'export contient les sources et résultats nécessaires à une lecture
indépendante de la machine. Les chemins d'origine sont conservés comme
provenance, pas comme dépendances de lecture. La reprise exige toujours
le runtime enregistré : aucune fusion Windows/Linux implicite.

## MCP

```bash
python -m arena experiment init configs/offline-demo.json --out runs/mcp-preparation
python -m arena mcp serve --experiment runs/mcp-preparation --session mock-single-r0
```

Le serveur utilise stdio et le SDK MCP 1.30.0 avec dépendances verrouillées.
Il expose les mêmes huit outils et la même exécution journalisée que
les fournisseurs natifs. Il exige une session ouverte sans réponse
fournisseur en attente, tient le verrou et applique les quotas.
Après submit, la session est fermée. Les clés ne sont jamais transmises
au moteur Java.

## Backend isolé optionnel

```bash
bash scripts/build-worker.sh
export ARENA_WORKER_BACKEND=docker
export ARENA_WORKER_IMAGE="$(cat .arena/worker-image.txt)"
python -m arena fight examples/strategies/rush examples/strategies/passive
```

Le backend Docker utilise le JDK vérifié, une base Debian enregistrée
par digest, un réseau désactivé, un système racine en lecture seule,
aucune capability, un utilisateur non root, 768 Mo de mémoire et une
limite de processus. Seuls le runtime moteur en lecture seule et le
dossier du combat sont montés. Le backend et son digest sont inclus
dans l'identité ; ne pas changer de backend en reprenant un run.
Le backend processus reste disponible avec ses limites documentées.
Le profil JVM startup (compilation tier 1) est commun à tous les workers
pour ces processus courts. ARENA_JVM_PROFILE=full rétablit la compilation
HotSpot complète. Le profil est enregistré ; ne pas le modifier en reprenant
une expérience. Les temps de ces profils ne sont pas fusionnés.
Les images Docker ne sont pas supposées survivre à une nouvelle tâche :
reconstruire l'image quand ce backend est choisi.

## Installation et ressources

bash scripts/bootstrap-linux.sh prépare Java, Gradle, le venv, MCP et
l'installation éditable. ARENA_PROJECT_ROOT permet de pointer vers
les ressources du checkout ; ARENA_STATE_ROOT sépare les artefacts
moteur du code. Ne pas déplacer un runtime déjà enregistré sans setup.
Le fingerprint couvre récursivement le package et les prompts.
L'identité scientifique et la provenance Python/Java/plateforme sont
séparées, mais la reprise conserve une vérification stricte du runtime.
