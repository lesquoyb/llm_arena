# Reprise cloud — plan d'implémentation de LLM Arena

Document de transmission du 13 octobre 2026. État de départ inspecté : commit local `f6ddac5` (`first commit`). Ce plan décrit le travail à réaliser ; les commandes et modules marqués « cible » n'existent pas encore.

## 1. Mission à transmettre à l'agent

> Continue l'implémentation de LLM Arena à partir du code existant. Lis README.md, docs/engine-audit.md, docs/protocol.md et ce plan. Le produit compare des LLM qui écrivent des stratégies LeekScript pour Leek Wars, avec préparation outillée, tournoi, suivi des coûts et amélioration avec ou sans feedback. Reste en LeekScript 4 pour cette version. Commence par rendre le build et les tests fiables sous Linux, puis implémente une expérience complète avec un fournisseur simulé avant les adaptateurs API réels. Réutilise le moteur et le tournoi actuels. Livre par étapes exécutables, avec critères de validation et documentation. Les clés absentes ne doivent pas empêcher le développement et les tests hors ligne. N'engage pas de dépenses réelles sans une configuration explicite de modèles et de plafond financier. Préserve les sources, conversations, usages et résultats nécessaires à l'audit. À chaque livraison, distingue les fonctionnalités exécutées, les simulations et les intégrations qui restent à valider avec de vraies API.

L'objectif de la prochaine version est une commande lançant toute la chaîne : configuration → conversations indépendantes → soumissions → tournoi G0 → branches contrôle/feedback → G1 → évaluations communes → rapport.

## 2. Décisions déjà prises

| Sujet | Décision |
|---|---|
| Langage des stratégies | LeekScript 4 uniquement. Python/JavaScript sont des extensions éventuelles ; TypeScript est hors périmètre. |
| Langage de l'orchestrateur | Python, en conservant le socle existant. |
| Moteur | Générateur officiel à un commit figé, pas le frontend Leek Wars. |
| Équipes initiales | 2 contre 2, statistiques et équipements identiques ; même point d'entrée pour les membres d'une équipe, rôles possibles dans le script. |
| Préparation | Documentation locale figée et outils identiques pour tous. |
| Réplications | Conversations indépendantes, même prompt et mêmes ressources pour chaque réplication. |
| Évaluation | Toutes les paires, deux positions par seed, concurrents du même modèle inclus. |
| Miroirs exacts | Diagnostics séparés, exclus du score principal. |
| Adaptation | Branches appariées issues du même état G0 : amélioration seule / amélioration avec résultats et logs. |
| Code adverse | Masqué dans l'expérience principale. Une condition avec code pourra être ajoutée ultérieurement. |
| Classement | Matrice des confrontations et scores descriptifs d'abord. Elo est facultatif. |
| Interface initiale | CLI et rapports exportables. Une application web n'est pas nécessaire à cette tranche. |

Les nombres de modèles, réplications, tours, tokens et dollars sont configurables. Les valeurs de pilote ci-dessous sont des propositions, pas une autorisation de dépense.

## 3. État exact du socle

### Fonctionnel et vérifié localement

- Bootstrap du générateur et de son sous-module ; contrôle des commits et des empreintes.
- Adaptateur Java appliquant la carte, le contexte, le propriétaire des IA et les métriques.
- Analyse de scripts et combats réels, avec budgets d'opérations natifs LeekScript.
- Soumissions multifichiers `.leek`, includes limités au dossier du participant.
- Tournoi aller-retour, miroirs, sources figées, rapports Markdown/JSON.
- Reprise séquentielle d'un tournoi avec vérification de résultats déjà enregistrés.
- Export de signatures : 378 fonctions, 416 constantes et données d'équipement.
- 11 tests réussis sous Windows ; tournoi de démonstration de 18 combats sans panne.

Les tests Linux n'ont pas encore été exécutés. Les trois concurrents de démonstration sont des scripts de contrôle écrits à la main. Aucun modèle n'a encore généré de stratégie dans cette application.

### Cartographie du code

| Fichier | Rôle |
|---|---|
| `arena/core.py` | Validation, scénarios, hachage et copie des soumissions. |
| `arena/engine.py` | Bootstrap, vérification du runtime, lancement Java, analyse et export de documentation. |
| `arena/tournament.py` | Calendrier, reprise, enregistrement et rapports. |
| `arena/cli.py` | Commandes publiques existantes. |
| `engine/ArenaMain.java` | Adaptateur au générateur, résolveur d'includes et métriques. |
| `engine/leekscript.init.gradle` | Exclusion du binaire natif polyglotte pour compiler LeekScript seul. |
| `engine.lock.json` | Versions figées du moteur et des outils. |
| `examples/tournament.json` | Tournoi de contrôle : 12 rencontres classées et 6 miroirs. |
| `tests/test_arena.py` | Tests unitaires et intégration avec le vrai moteur. |
| `docs/leekscript-v1/` | Première référence figée, encore incomplète sur la sémantique. |

### Versions et particularités à préserver

- Générateur : `b99a174dd938260d9e47b2e65a208cb32230e26e`.
- LeekScript : `8152f399faf7b418bbc5b2216d755c3822cda23b`.
- JDK 25 et Gradle 9.3.1 ; le wrapper du dépôt amont est trop ancien.
- `winner = 0/1` désigne les côtés ; `winner = -1` est un nul. Le champ `team` des entités du replay utilise 1/2.
- Le compteur de durée peut atteindre `max_turns + 1` : ce n'est pas nécessairement un tour joué supplémentaire.
- `cores × 1_000_000` fixe les opérations par tour. Le champ d'exemple amont `max_operations_per_entity` est ignoré par son parser.
- Les temps mesurés actuellement sont des temps écoulés, pas des temps CPU.
- Les 5 secondes et 3 dépassements concernent le runtime polyglotte, qui n'est pas utilisé ici. Ne pas modifier ces constantes pour cette version.

### Limites connues à traiter

- Aucun orchestrateur de conversations, adaptateur fournisseur, MCP ou suivi de facturation.
- Les tests d'intégration sont actuellement ignorés si le moteur n'est pas construit : une CI simplement verte ne suffira pas.
- `ROOT` est dérivé du dossier du package ; vérifier les chemins lors d'une installation et séparer les ressources du projet des données d'exécution.
- La reprise compare aussi les versions Python/Java et la plateforme. Un run Windows ne doit pas être repris silencieusement sous Linux.
- Un seul écrivain par tournoi ; pas de verrou interprocessus ni de journal transactionnel global.
- Le hash du runner ne couvre actuellement que les fichiers Python directement dans `arena/` : l'étendre lorsque des sous-packages seront ajoutés.
- Les archives vérifient le résultat brut et compact, mais leur validation peut être renforcée pour couvrir scénario, métadonnées et copies de sources.
- Un processus Java séparé et `-Xmx512m` ne constituent pas une isolation OS complète ni une limite de mémoire totale du processus.
- Les sorties de processus sont écrites sans quota de taille ; les plafonner pour les scripts très bavards.
- Le rapport est recalculé et les replays relus après chaque combat : optimiser progressivement avant les grands tournois.

## 4. Transfert et premier démarrage cloud

Le code nécessaire est suivi par Git. Un remote nommé `origin` existe ; sa synchronisation avec le commit local n'a pas été vérifiée. Le présent plan devra lui aussi être inclus dans le commit accessible à l'agent.

Les dossiers `vendor/`, `.arena/` et `runs/` sont ignorés. Ils ne seront pas présents dans un checkout cloud. Ne pas copier `.arena/engine.json` : il contient des chemins et identités du runtime local. Reconstruire avec `setup`. Les anciens rapports peuvent être transférés comme artefacts de référence, mais ils ne sont pas nécessaires pour développer.

Premières actions de l'agent :

1. Lire les éventuels `AGENTS.md` du checkout, puis les documents indiqués ci-dessus.
2. Inspecter Git et conserver les modifications déjà présentes.
3. Installer/vérifier Python ≥ 3.11, JDK 25, Git et Gradle 9.3.1 dans l'environnement Linux.
4. Donner au bootstrap l'accès nécessaire à GitHub, à la distribution Gradle et aux dépendances Maven ; vérifier ces besoins dans les logs du build.
5. Exécuter depuis la racine du projet :

```bash
python -m arena setup
python -m arena doctor
python -m unittest discover -s tests -v
python -m arena verify examples/strategies/rush examples/strategies/single-shot
python -m arena tournament examples/tournament.json --out runs/cloud-smoke
python -m arena tournament examples/tournament.json --out runs/cloud-smoke --resume
```

Le dernier appel doit réutiliser les 18 résultats et ne lancer aucun nouveau combat. Le premier objectif est de retrouver les invariants des tests, pas d'obtenir les mêmes temps d'exécution que sur Windows.

## 5. Architecture cible

Conserver un processus d'orchestration central au départ. SQLite convient à ce stade ; ne pas introduire une infrastructure distribuée avant d'en avoir besoin.

```text
CLI experiment
  └─ Orchestrateur + journal SQLite + artefacts
      ├─ Sessions de génération
      │   ├─ Adaptateur fournisseur réel ou simulé
      │   ├─ Historique et budgets
      │   └─ Service d'outils commun, exposable en MCP
      │       ├─ Fichiers propres à la session / documentation figée
      │       └─ Tests de préparation → worker LeekScript
      ├─ Soumissions immuables
      ├─ Calendrier d'évaluation → worker LeekScript
      └─ Rapports / feedback / branches de génération suivante
```

L'orchestrateur possède les clés fournisseurs. Le worker de combat reçoit uniquement les soumissions et les données de jeu. Les outils accessibles au modèle n'exposent ni le checkout complet, ni les autres sessions, ni les scénarios réservés.

Organisation suggérée, à adapter sans refonte gratuite :

```text
arena/
  experiment.py          # cycle global, générations et reprise
  sessions.py            # boucle modèle ↔ outils
  storage.py             # transactions, états et migrations
  budgets.py             # réservations et consommations
  usage.py               # normalisation et tarification
  providers/
    base.py
    mock.py
    ...                  # adaptateurs explicitement implémentés
  tools/
    service.py
    schemas.py
    mcp_server.py
  feedback.py
  analysis.py
configs/                  # manifestes publics d'exemple
prompts/                  # prompts versionnés
scripts/                  # setup Linux et commandes de validation
tests/                    # cas locaux + fixtures fournisseurs
```

## 6. Lot A — Portabilité, reproductibilité et CI

**But :** un checkout Linux propre devient utilisable sans fichiers provenant du poste local.

Travail :

1. Ajouter un bootstrap Linux documenté, versions et checksums des téléchargements fixés. Conserver `engine.lock.json` comme référence.
2. Installer les dépendances pendant la préparation ; démontrer ensuite l'exécution des combats sans téléchargement.
3. Ajouter une CI Linux avec build, tests unitaires, intégration réelle et conservation des logs/rapports en cas d'échec.
4. Rendre l'absence du moteur bloquante dans le job d'intégration. Garder une suite unitaire rapide indépendante du moteur.
5. Tester les chemins avec espaces, les includes multifichiers et les exécutables Java sur Linux.
6. Séparer identité scientifique et provenance de machine. Garder les détails de plateforme, sans autoriser une fusion implicite de résultats entre environnements différents.
7. Rendre l'assemblage des artefacts stable lorsque c'est possible ; distinguer une différence de binaire liée au packaging d'un changement de sources.
8. Étendre le fingerprint du runner aux sous-packages et aux ressources qui modifient le comportement ; versionner le schéma d'artefacts.
9. Prévoir un runner conteneurisé si l'environnement le permet. Ne pas supposer Docker disponible dans l'agent cloud. À défaut, isoler l'interface de worker et documenter précisément les limites du backend processus.

**Acceptation :** build depuis zéro, tous les tests d'intégration exécutés, 18 combats terminés, reprise sans recomputation, vérification de replay stable sur les contrôles. Aucune dépendance à un chemin `C:\\Users\\...`.

## 7. Lot B — Contrats d'expérience et stockage durable

**But :** définir clairement une expérience et pouvoir reprendre un travail interrompu.

Créer un schéma validé contenant :

- version de schéma, identifiant d'expérience et langue du prompt ;
- moteur, corpus documentaire, prompt et règles d'équipement par hash ;
- fournisseurs, identifiants exacts des modèles et paramètres réellement supportés ;
- nombre de réplications, générations et conditions de feedback ;
- plafonds de tokens, de tests, de pas d'agent, de temps et de coût ;
- ensembles préparation / feedback / évaluation finale ;
- politique de soumission, d'échec, de retry et de contexte ;
- tarifs datés et devise, ou statut explicite « tarif inconnu ».

Entités minimales du journal : `Experiment`, `Session`, `ModelCall`, `ToolCall`, `Submission`, `Match`, `UsageEvent`, `FeedbackArtifact`. Chaque objet a un identifiant stable, son parent éventuel, des horodatages et des liens vers ses artefacts.

Une session est repérée par `(model, replicate, generation, condition)` et sa filiation. Une soumission est repérée par son contenu complet, son point d'entrée et la session qui l'a créée.

États de session proposés : `pending`, `running`, `submitted`, `budget_exhausted`, `generation_failed`, `provider_unavailable`, `needs_reconciliation`. Une interruption de développement n'est pas automatiquement un échec du modèle.

Travail supplémentaire :

- migrations de schéma ; transactions pour les changements d'état ; verrou empêchant deux orchestrateurs d'écrire dans la même expérience ;
- artefacts volumineux sur disque, référencés par hash depuis SQLite ;
- écritures atomiques et reprise d'un essai partiellement enregistré ;
- export d'une expérience autonome, sans clés ni chemins de machine obligatoires ;
- conservation des anciens formats de tournois ou migration explicitement testée.

**Acceptation :** arrêt simulé entre chaque étape critique, reprise cohérente, détection des sources/configurations modifiées, tentative de double lancement refusée proprement.

## 8. Lot C — Service de préparation et MCP

**But :** donner à chaque participant les mêmes possibilités de lire, coder et tester.

Implémenter d'abord un service Python testable directement, puis un adaptateur MCP utilisant un SDK maintenu et figé. Les adaptateurs fournisseurs peuvent appeler ce service via leurs outils natifs : aucun fournisseur ne doit être obligé de prendre en charge MCP lui-même.

| Outil proposé | Contrat |
|---|---|
| `list_files` | Liste uniquement l'espace de travail de la session. |
| `read_file(path, offset, limit)` | Lecture paginée de ses fichiers. |
| `write_file(path, content)` | Écrit un fichier autorisé, taille plafonnée, avec hash retourné. |
| `read_docs(path, offset, limit)` | Lit le corpus figé commun, en lecture seule. |
| `analyze(entrypoint)` | Diagnostics normalisés, liés au hash exact analysé. |
| `test(entrypoint, scenario_id, seed_id, opponent_id)` | Test uniquement sur le catalogue de préparation autorisé. |
| `read_replay(test_id, section, offset, limit)` | Lecture bornée des actions ou logs d'un test de la session. |
| `submit(entrypoint)` | Fige explicitement la soumission et clôt la préparation. |

Règles : pas de shell arbitraire ; validation côté serveur des chemins, identifiants et quotas ; résolution des liens et `..` ; aucun résultat d'un autre participant via un identifiant deviné. Les erreurs d'outils reviennent au modèle de manière exploitable et sont enregistrées.

Chaque réponse précise si elle est tronquée et comment lire la suite. Un test doit retourner un résumé, puis donner accès au replay à la demande. Les appels `analyze` et les lectures doivent aussi être limités par un nombre global de pas d'agent ; un plafond de combats seul ne suffit pas.

Documenter l'unité de test : par exemple un appel teste les deux positions et consomme deux exécutions moteur. Préférer cette paire pour ne pas favoriser arbitrairement un côté. Fixer ce choix pour tous les modèles.

Ajouter des quotas aux sorties du worker, une limite de ressources du processus et la terminaison de son arbre en cas d'arrêt. Les clés fournisseurs ne doivent pas être héritées par son environnement.

**Acceptation :** mêmes réponses via appel direct et MCP ; refus des accès croisés ; quotas effectifs ; vrais tests moteur depuis un espace de session temporaire ; protocole MCP validé par un client de test.

## 9. Lot D — Corpus documentaire et prompts

**But :** rendre les documents suffisants pour apprendre et utiliser correctement l'API sans consulter le web pendant l'expérience.

La référence actuelle énumère types et valeurs, mais ne décrit pas tous les paramètres, effets, règles de portée ou retours d'erreur. L'enrichir avant le pilote scientifique.

Livrables :

- `index.md` court : où trouver chaque information ;
- règles des tours, victoire/nul, carte, distance, obstacles et ligne de vue ;
- caractéristiques, équipements, effets, équipes et communication ;
- syntaxe LeekScript nécessaire, includes et persistance des variables ;
- API avec noms d'arguments, sens des retours, erreurs, exemples et coûts lorsqu'ils sont connus ;
- scénario de préparation exact, ressources disponibles et contrat de soumission ;
- références sources, version et hashes de tous les documents.

Extraire les informations des sources/documents officiels et les confronter au commit retenu. Éviter de compléter une ambiguïté par supposition. Faire compiler et exécuter les exemples importants. Conserver une licence/attribution appropriée pour les documents importés.

Créer trois prompts versionnés : préparation G0, amélioration contrôle, amélioration avec feedback. Le prompt initial expose l'objectif, les règles, l'index documentaire, les outils et les budgets. Choisir une langue unique pour le pilote, par défaut le français comme le projet, et la figer. Ne pas ajouter d'aide propre à un modèle.

**Acceptation :** toutes les fonctions utilisées par les exemples sont documentées et les exemples passent dans le moteur figé ; le corpus est identifiable par hash et monté de façon identique pour tous les participants.

## 10. Lot E — Boucle d'agent et fournisseur simulé

**But :** une expérience complète fonctionne sans clé API et sans coût.

Définir une interface fournisseur indépendante de l'API réelle : requête, message assistant, liste d'appels d'outils, raison d'arrêt, usage brut et normalisé, identifiant fournisseur, métadonnées de modèle.

Conserver un historique canonique ainsi que les objets natifs nécessaires pour poursuivre une conversation. Ne pas reconstruire artificiellement une chaîne de raisonnement non exposée par le fournisseur ; préserver seulement les champs requis et disponibles.

Boucle d'une session :

1. Créer son espace et ses documents, puis enregistrer le prompt et les paramètres.
2. Vérifier/réserver le budget du prochain appel et enregistrer son intention avant envoi.
3. Appeler le fournisseur ; sauvegarder la réponse et son usage avant d'exécuter les outils.
4. Valider les appels, les exécuter dans un ordre défini, enregistrer leur résultat et le renvoyer.
5. Continuer jusqu'à `submit`, arrêt du modèle, budget épuisé ou erreur terminale.
6. Figer les fichiers et le statut selon la politique ci-dessous, puis les transmettre au tournoi.

Politique initiale proposée : soumission explicite si disponible ; à l'arrêt par budget ou message final, figer le dernier état sauvegardé. Ne pas sélectionner automatiquement le meilleur script parmi les essais. Si cet état est invalide, conserver l'échec. Si aucun point d'entrée n'existe, conserver `no_submission` et inclure ce cas dans les mesures d'échec de génération, sans le supprimer du groupe.

Le fournisseur simulé doit couvrir : script valide, réparation après diagnostic, tests et lecture de logs, soumission invalide, appels malformés, dépassement de budget, réponse vide, timeout, limitation de débit et interruption après réception d'une réponse.

**Acceptation :** commande de démonstration hors ligne créant plusieurs sessions indépendantes, produisant des stratégies, exécutant le vrai tournoi et un rapport. Toute la chaîne est testée, pas seulement des fonctions mockées isolément.

## 11. Lot F — Tokens, coûts et adaptateurs réels

### Comptabilité avant les appels payants

Enregistrer par appel : input total, part en cache si exposée, output, raisonnement si exposé, unités facturées spécifiques, durée, request ID et usage brut. Un champ indisponible vaut `null`, pas zéro. Le raisonnement peut être inclus dans l'output : ne pas l'ajouter automatiquement une seconde fois. Les détails exacts dépendent du fournisseur.

Les coûts doivent être calculés à partir d'un tarif figé, daté et associé au modèle exact. Séparer coût estimé, coût calculé sur usage retourné et coût confirmé par facturation lorsqu'il est disponible. Aucun coût fictif pour un modèle non tarifé.

Budgets par session et expérience : tokens input cumulés, tokens output facturables cumulés, appels, exécutions de test, délai et dollars. Enregistrer aussi le budget restant communiqué au modèle. Les tokens ne sont pas directement comparables entre tokenizers ; publier séparément les observations à budget token et financier.

Réserver de manière atomique le coût maximal défendable du prochain appel, en tenant compte de la réponse plafonnée et d'une entrée estimée prudemment. Refuser un nouvel appel lorsque la borne ne tient plus dans le budget. Si un fournisseur ne permet pas une borne fiable, marquer le plafond comme « au mieux » et le signaler dans le plan d'exécution ; ne pas promettre un plafond strict.

### Intégrations fournisseurs

Commencer par **un** adaptateur réel de bout en bout, puis un deuxième d'un autre fournisseur pour vérifier que l'abstraction est correcte. Préparer un adaptateur à endpoint compatible configurable pour les modèles ouverts, sans supposer que tous les serveurs dits compatibles ont les mêmes usages ou outils.

Vérifier les API, paramètres, prix et possibilités de cache dans la documentation officielle au moment de l'implémentation. Les noms de modèles des notes initiales sont provisoires : aucun alias incertain ne doit devenir une dépendance codée en dur.

Fonctions nécessaires : clés par variables d'environnement, choix du modèle exact, outils, reprise d'historique, limites de sortie, timeouts, erreurs typées, retries bornés et paramètres de raisonnement lorsque supportés. Enregistrer les paramètres réellement envoyés ; ne pas fabriquer une température commune si un modèle ne la supporte pas.

### Reprise des appels et facturation incertaine

Un timeout réseau après l'envoi peut correspondre à une requête déjà exécutée et facturée. Distinguer « envoi non effectué », « réponse sauvegardée » et « état distant inconnu ». Exploiter les request IDs, fonctions de récupération et clés d'idempotence quand le fournisseur les garantit. Sinon conserver `needs_reconciliation` et la réservation prudente ; ne pas relancer aveuglément en prétendant éviter toute double facturation.

### Optimisations ultérieures

Préfixe documentaire stable pour le cache ; logs demandés par pages ; parallélisme borné entre sessions ; batch seulement pour les appels indépendants et les fournisseurs compatibles. Ne pas faire dépendre la validité du protocole d'un cache dont l'usage n'est pas garanti.

**Acceptation :** fixtures de réponses réelles anonymisées ou fixtures conformes documentées, tests d'erreurs et de calcul financier, plafond global résistant aux sessions concurrentes. Le test réel est séparé, opt-in, avec un petit budget explicite ; aucune clé n'est nécessaire à la CI standard.

## 12. Lot G — Tournois de générations et feedback contrôlé

**But :** mesurer l'effet du feedback sans confondre amélioration, changement d'adversaires et budget supplémentaire.

Créer trois ensembles identifiés et séparés :

1. Préparation : scénarios, seeds et adversaires fixes accessibles aux outils.
2. Feedback : rencontres du round, dont certains résultats seront remis à la branche feedback.
3. Final : scénarios/seeds non exposés aux participants, utilisés seulement à la mesure terminale.

Le fait qu'un fichier soit dans le dépôt développeur ne le rend pas secret pour un agent ayant accès au dépôt. Monter uniquement le corpus et l'espace autorisés dans les sessions des modèles évalués. Le modèle auteur ne doit pas pouvoir demander arbitrairement un chemin ou une seed finale au moteur.

Après G0, figer toutes les soumissions avant de lancer le round. Pour chaque réplication, créer deux branches à partir du même checkpoint de conversation et du même code. Les paramètres, budgets d'amélioration et droits de test restent égaux ; seule l'information de feedback varie.

Le checkpoint doit être clonable sans état fournisseur partagé mutable. Rejouer l'historique avec ses champs natifs si nécessaire. Ne pas remplacer silencieusement une branche par une nouvelle conversation ou un résumé : cela modifierait l'expérience. Si une API ne permet pas la condition retenue, marquer le modèle incompatible ou définir une autre piste expérimentale explicite.

Feedback proposé : adversaires pseudonymisés, résultats agrégés, erreurs du script, consommation d'opérations et sélection déterministe d'extraits de combats. Limiter la taille selon une règle commune. Ne pas envoyer code adverse, chemins internes ni logs système contenant des secrets. Indiquer que tous les adversaires peuvent évoluer. La branche contrôle reçoit la même consigne d'amélioration sans ces résultats.

Évaluer G1 de trois façons, en rapports distincts : contre contemporains, contre un panel figé G0 et contre les contrôles fixes. Pour estimer l'effet du feedback, comparer les deux branches sur **les mêmes** adversaires et scénarios. Un classement G0/G1 dans des populations différentes n'est pas une mesure suffisante de progrès.

Les budgets de G1 sont supplémentaires ; publier coûts de G1 et coûts cumulés depuis G0. Les artefacts initiaux partagés ne doivent pas être facturés deux fois dans le total réellement payé de l'expérience. Distinguer ce total du coût hypothétique de chaque trajectoire indépendante.

**Acceptation :** test hors ligne G0 → branchement → G1, aucun accès au feedback dans le contrôle, aucun accès aux données finales, mêmes adversaires de référence pour la comparaison appariée, conservation complète de la filiation.

## 13. Lot H — Analyse et rapports utiles

Produire un rapport Markdown/HTML autonome et des exports JSON/CSV. Conserver les replays bruts hors du rapport pour éviter un document énorme.

Mesures :

- validité des soumissions, absence de soumission, erreurs d'exécution, dépassements et pannes d'infrastructure ;
- score, W/D/L, matrice par stratégie et par modèle ;
- dispersion entre réplications, résultats par scénario et par génération ;
- amélioration contre le panel fixe et effet apparié feedback/contrôle ;
- tokens d'entrée, cache, sortie et coûts avec leur statut de précision ;
- opérations totales et par tour exécuté, temps écoulés, éventuellement CPU mesuré séparément ;
- performance selon le budget et frontière de Pareto performance/coût.

Pondérer explicitement modèles, réplications et scénarios. Présenter les rencontres entre réplications du même modèle séparément dans l'analyse agrégée, tout en les conservant dans la matrice. Ne pas donner plus de poids à un fournisseur parce qu'il a plus de participants.

Prévoir des intervalles par rééchantillonnage respectant la structure : conversations indépendantes comme unités principales, paires aller-retour et dépendance entre adversaires préservées. Un intervalle binomial sur des centaines de combats du même script surestime l'information. Avec trois réplications, qualifier les estimations d'exploratoires.

Les runs avec pannes non résolues restent visibles et signalés comme incomplets. Les scripts absents/invalides doivent apparaître dans la mesure de réussite de génération ; une moyenne de victoire limitée aux seuls survivants doit être clairement distinguée de la performance globale. Préannoncer la politique de pénalité avant un pilote payant.

**Acceptation :** totaux vérifiables depuis les artefacts ; miroirs exclus du score ; erreurs et données manquantes visibles ; comparaison G0/G1 sur référence stable ; aucun classement coût calculé avec un prix inconnu assimilé à zéro.

## 14. Configuration et CLI proposées

Conserver les commandes actuelles de combat. Ajouter une famille `experiment`, par exemple :

```bash
# Cibles à implémenter, pas des commandes déjà disponibles.
python -m arena experiment plan configs/offline-demo.json
python -m arena experiment run configs/offline-demo.json --out runs/offline-demo
python -m arena experiment resume runs/offline-demo
python -m arena experiment status runs/offline-demo
python -m arena experiment report runs/offline-demo
python -m arena mcp serve --session SESSION_ID
```

Le plan doit afficher avant exécution : sessions prévues, générations/branches, nombre de matchs, plafonds de consommation, fournisseurs activés, clés requises et coût maximal calculable. Il valide tous les manifestes avant d'appeler un fournisseur.

Exemple conceptuel de configuration hors ligne, à transformer en schéma réel :

```json
{
  "schema_version": 1,
  "name": "offline-demo",
  "language": "leekscript4",
  "prompt_language": "fr",
  "models": [
    {"id": "mock-a", "provider": "mock", "profile": "repair-and-submit"},
    {"id": "mock-b", "provider": "mock", "profile": "single-shot"}
  ],
  "replicates": 2,
  "generations": 2,
  "improvement_conditions": ["control", "feedback"],
  "budget_per_session": {
    "max_agent_steps": 30,
    "max_input_tokens": 150000,
    "max_output_tokens": 12000,
    "max_test_matches": 20,
    "max_wall_seconds": 900
  },
  "spending": {"allow_paid_calls": false, "max_total_usd": 0},
  "training_catalog": "training-v1",
  "feedback_catalog": "feedback-v1",
  "final_catalog": "heldout-v1"
}
```

Les seuils ci-dessus servent à démontrer l'orchestration. La taille réelle du corpus, les limites de contexte et le coût par modèle doivent guider les budgets du pilote.

Pour un pilote G0 de 3 modèles × 3 réplications, N = 9. Avec 10 seeds et une configuration de jeu, le round-robin comporte `N(N−1)S = 720` matchs classés, plus `NS = 90` miroirs si activés. Multiplier par le nombre de scénarios. Les matchs contre panels et les deux conditions G1 s'ajoutent : le planificateur doit calculer ce total au lieu de réutiliser « 720 » pour toute l'expérience.

## 15. Ordre de livraison et définition de terminé

| Livraison | Lots | Preuve attendue |
|---|---|---|
| 1. Socle Linux | A | Build neuf, CI réelle et tournoi de contrôle. |
| 2. Préparation locale complète | B, C, D | Session isolée, outils/MCP, documents vérifiés et journal durable. |
| 3. Expérience hors ligne | E + comptabilité de F | Plusieurs agents simulés produisent du code, tournoi réel, budgets et reprise testés. |
| 4. Fournisseurs | Reste de F | Un adaptateur réel complet, puis un second ; tests hors ligne systématiques, smoke payant seulement si configuré. |
| 5. Adaptation mesurable | G, H | G0/G1 avec contrôle/feedback, panel figé, rapport coûts/performance. |

Dans chaque livraison : conserver les commandes existantes, ajouter les tests des nouveaux comportements, documenter l'usage exact et les limites, puis fournir les preuves de validation. Des commits ou PR de cette taille facilitent la revue ; éviter une refonte massive avant le premier parcours complet.

La prochaine version est considérée terminée lorsque l'expérience hors ligne entière fonctionne depuis un checkout cloud propre ; que les adaptateurs réels sont prêts et testables sans toucher au cœur ; que les budgets et reprises sont auditables ; et que les branches G1 produisent un rapport comparatif reproductible. L'exécution d'un véritable benchmark multi-modèles dépend ensuite des clés, des modèles et du plafond financier choisis par l'utilisateur.

À laisser pour plus tard : nouveaux langages, interface web riche, exploitation publique multi-utilisateur, cluster distribué, divulgation du code adverse et optimisation batch avancée. Aucun de ces éléments ne doit retarder le premier cycle complet vérifiable.
