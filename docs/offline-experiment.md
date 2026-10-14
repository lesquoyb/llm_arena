# Expérience hors ligne G0

```bash
python -m arena experiment plan configs/offline-demo.json
python -m arena experiment run configs/offline-demo.json --out runs/offline-demo-new
python -m arena experiment status runs/offline-demo-new
python -m arena experiment resume runs/offline-demo-new
python -m arena experiment report runs/offline-demo-new
```

La démonstration crée quatre conversations indépendantes : deux profils
simulés et deux réplications. Le profil réparation écrit un script invalide,
reçoit les diagnostics du vrai moteur, écrit le contrôle agressif, teste
les deux positions contre le contrôle passif, consulte les métriques
du replay puis soumet. Le second profil soumet le contrôle single-shot.
Les scripts sont des fixtures déterministes écrites à la main :
aucun LLM n'a généré ces stratégies.

Le tournoi G0 exécute 12 combats classés et 4 miroirs sur la seed 101.
La préparation utilise uniquement la seed 17 et le contrôle passif.
Les miroirs restent exclus du score. Les absences et scripts invalides
figurent dans le rapport, sans être retirés silencieusement des sessions.
Les scores portent sur les soumissions présentes.

## Artefacts et reprise

- `experiment.json` fige le manifeste, prompt, corpus, moteur et runner.
- `corpus/` contient uniquement authoring.md et la référence LeekScript.
- `journal.sqlite` conserve états, intentions d'appels, réponses,
  résultats d'outils, budgets et horodatages, avec transactions SQLite.
- `sessions/*/workspace` contient les fichiers propres à une session.
- `sessions/*/submission` contient sa soumission figée.
- `sessions/*/conversation.json` exporte la conversation canonique.
- `sessions/*/tools` conserve diagnostics, combats de préparation et replays.
- `report.md`, `report.json` et `tournament/` rendent les résultats.

Une réponse sauvegardée est réutilisée après interruption ; un résultat
de combat terminé est réutilisé. Une invocation moteur interrompue peut
être rejouée dans un nouvel essai conservant le premier dossier.
Il n'y a aucune promesse de facturation exactement une fois : les API
réelles ne sont pas implémentées. Un verrou OS refuse un second écrivain.
La reprise refuse un changement de configuration, runtime, runner,
corpus ou soumission figée. La CLI report lit le dernier rapport final ;
status est utilisable pendant une exécution interrompue.

## Outils et budgets

Service Python direct : list_files, read_file, write_file, read_docs,
analyze, test, read_replay et submit. Aucune commande shell.
Les chemins absolus, liens et traversées sont refusés. Les lectures
sont paginées, les fichiers limités à 128 sources .leek et 2 Mo.
Un test consomme deux exécutions moteur. Le fournisseur simulé n'a
aucun accès aux fichiers en dehors de ces outils.

Les plafonds couvrent appels modèle, appels d'outils, combats de test
et temps cumulé. Le temps est vérifié entre les opérations ; une
opération en cours peut dépasser le budget jusqu'au délai moteur de
90 secondes. Un arrêt brutal peut perdre le temps écoulé depuis le
dernier checkpoint. Le dernier état est soumis à l'épuisement du budget.
Les analyses finales sont une étape d'évaluation indépendante du budget
de préparation.

Les tokens restent null : aucun tokenizer fournisseur n'est exécuté.
Le coût fournisseur nul est explicitement une simulation.
Les manifests autorisant des appels payants ou un fournisseur réel
sont refusés.

Sous Linux, le worker Java reçoit un environnement minimal sans clés
fournisseurs, limite chaque fichier de sortie à 8 Mo et termine le groupe
de processus au timeout. Il conserve sa limite de heap de 512 Mo.
Ce backend n'est pas une isolation OS complète ; ne pas l'utiliser
comme service public pour des soumissions hostiles.

## Limites de cette livraison

G0 uniquement : pas encore de branches G1 contrôle/feedback, catalogue
final réservé, tarification réelle, retries fournisseurs ou export
d'expérience autonome. Le service d'outils est direct, sans transport MCP.
Les profils invalid, empty et malformed servent aux tests de politiques
d'échec. Timeout réseau et limitation de débit restent à simuler.
Le corpus actuel est une référence de signatures, encore incomplet sur
la sémantique. L'orchestrateur utilise le verrou POSIX et cible Linux.
