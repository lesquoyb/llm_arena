# Développement Linux

Pour Windows natif, voir [le guide Windows](windows.md). Le bootstrap
portable `python scripts/bootstrap.py` fonctionne aussi sous Linux si
un JDK 25 est déjà installé ; le script Bash ci-dessous installe aussi le JDK.

Prérequis système : Linux x86_64, Python ≥ 3.11, Git, curl, tar et unzip.
Depuis le checkout :

```bash
bash scripts/bootstrap-linux.sh
bash scripts/validate-linux.sh
```

Le bootstrap installe Oracle JDK 25.0.4.1 et Gradle 9.3.1 dans
`.arena/tools`, vérifie leurs SHA-256, puis compile les commits de
`engine.lock.json`. Consulter les conditions de licence Oracle avant une
utilisation hors développement. Les sources amont restent inchangées.
`ARENA_TOOLS_DIR` et `GRADLE_USER_HOME` permettent de choisir des caches
dédiés. Le script écrit sa configuration dans ce cache Gradle ; ne pas
lui fournir un cache partagé contenant une configuration personnelle.

Le proxy HTTPS fourni par la machine est transmis à Gradle sans désactiver
TLS. Sur les distributions fournissant `/etc/ssl/certs/java/cacerts`, ce
magasin système permet d'utiliser les autorités de certification de
l'environnement. Aucun secret n'est nécessaire.

La validation exige un moteur construit avant de lancer les tests :
un moteur absent fait échouer `doctor`, même si unittest aurait ignoré
les tests d'intégration. Elle vérifie les replays, les 18 combats de
contrôle et la reprise sans nouvelle tentative. Chaque appel utilise
un nouveau dossier, ou celui fourni en argument.

Les tests rapides sans moteur restent disponibles :

```bash
python -m unittest discover -s tests -p test_arena.py -k ProtocolTests -v
```

La CI Linux compile depuis un checkout propre et conserve logs,
rapports et replays, y compris en cas d'échec. Son exécution sur GitHub
reste à vérifier après publication du code.

Après compilation, les combats utilisent uniquement le Java enregistré
dans `.arena/engine.json` et les ressources locales ; aucun service,
base de données ou appel fournisseur n'intervient. Ne pas transférer
ce fichier depuis une autre machine : le régénérer avec le bootstrap.
Un tournoi d'une autre plateforme ne peut pas être repris implicitement.

Le backend processus Java impose délai global, heap et quotas de sortie.
Le backend Docker optionnel, MCP et les adaptateurs fournisseurs sont
décrits dans le [guide complet](complete-experiment.md).
Le fingerprint couvre les sous-packages et prompts ; les archives Gradle
ont un ordre stable sans timestamps. La reprise reste stricte sur le
runtime, même avec une identité scientifique séparée.
