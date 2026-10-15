# Interface web locale

L’interface permet de configurer les IA et les compétitions, puis de lire
les conversations, les versions du code, les combats et les bilans dans
un navigateur. Elle utilise les mêmes expériences et le même moteur que
la ligne de commande. Aucun service Leek Wars, Node.js ou base de données
à installer séparément n’est nécessaire.

## Démarrer

Installer d’abord le projet : [Windows natif](windows.md) ou [Linux](linux.md).
Depuis le dépôt, sous PowerShell :

```powershell
.\.venv\Scripts\python.exe -m arena ui --open
```

Sous Linux :

```bash
.venv/bin/python -m arena ui --open
```

Le navigateur s’ouvre sur **http://127.0.0.1:8765**. Sans `--open`, ouvrir
cette adresse soi-même. Garder le terminal ouvert ; Ctrl+C ferme le serveur
et demande l’arrêt de son expérience active. Un autre port est possible :
`python -m arena ui --port 9000`. `--runs CHEMIN` choisit un autre dossier
contenant les résultats à explorer. L’interface est locale, accessible
uniquement depuis cette machine ; ce n’est pas un service multiutilisateur.

Les anciennes expériences du dossier `runs` apparaissent automatiquement.
Elles restent consultables même lorsque leur runtime d’origine n’est plus
disponible. Pour reprendre une expérience, il faut toutefois retrouver
exactement son code, son moteur et ses paramètres. **Dupliquer sa
configuration** permet de démarrer une nouvelle expérience avec le code actuel.

## Premier essai, sans API payante

1. Dans **Vue d’ensemble**, cliquer sur **Configurer la démo**.
2. Donner un nom à la compétition et conserver les deux participants simulés.
3. Cliquer sur **Calculer le calendrier**, puis **Enregistrer la configuration**.
4. Dans **Compétitions**, cliquer sur **Lancer**, puis **Démarrer la compétition**.
5. Ouvrir les différents onglets pour suivre sa progression et lire les résultats.

Le cycle complet de la démo prévoit 80 combats d’évaluation, en plus des
combats de préparation réellement demandés par les participants. Pour un
premier essai plus court, choisir **G0 : première stratégie**, une répétition
et une seule seed. Les combats peuvent prendre plusieurs minutes.

**Les participants simulés ne sont pas des LLM.** Ils fournissent des scripts
prédéfinis ; les diagnostics et les combats Java sont réels. Le gain programmé
dans la branche feedback démontre le fonctionnement du protocole, pas un
apprentissage ni la supériorité d’un modèle.

## 1. Configurer les participants

Chaque profil contient un identifiant stable, un fournisseur et, pour une
API réelle, l’identifiant exact du modèle, les paramètres et les limites par
appel. OpenAI, Anthropic, Gemini natif et les endpoints compatibles OpenAI sont pris en charge.
**Charger les modèles** remplit un sélecteur avec les modèles accessibles à la clé
configurée ; la saisie manuelle reste possible si ce catalogue n’est pas disponible.
Le champ **Seed du modèle** est envoyé avec chaque requête pour OpenAI et Gemini
(selon les capacités du modèle). Anthropic n’expose pas cette option.
Voir [les limites de reproductibilité](providers.md#catalogue-seeds-et-requêtes).

Les prix sont **en USD par million de tokens**, avec leur date. Par exemple,
un tarif d’entrée de 2 signifie 2 USD pour un million de tokens d’entrée,
et non 2 USD par token. Saisir les tarifs officiels du modèle choisi ; aucun
prix réel ni modèle commercial n’est présélectionné. Les tarifs du cache sont
facultatifs ; sans eux, le tarif ordinaire d’entrée est utilisé.

Une clé peut provenir de l’environnement du serveur, par exemple
`ARENA_OPENAI_KEY`, ou être saisie dans le champ masqué. Une clé saisie reste
en mémoire jusqu’à la fermeture du serveur. Elle n’est ni renvoyée dans les
réponses HTTP ni enregistrée dans le catalogue, les configurations ou les
artefacts. Laisser le champ vide conserve la clé déjà disponible. Pour
l’effacer, fermer le serveur ; une variable définie dans le système doit
être retirée du système séparément.

Le profil ne contient pas les futures conversations. Une compétition
conserve une copie de ses paramètres ; modifier ensuite le profil ne
réécrit pas les expériences déjà enregistrées. Voir aussi
[les règles de facturation et de reprise](providers.md).

## 2. Préparer et gérer les compétitions

Le formulaire permet de choisir :

- les participants et le nombre de conversations indépendantes par participant ;
- une évaluation G0 seule ou le cycle G0 → G1 avec les branches appariées ;
- les seeds, les équipes, le nombre de tours, les statistiques et l’équipement ;
- les budgets d’appels, d’outils, de tests, de temps, de tokens et de coût ;
- une carte personnalisée ou un manifeste JSON complet, si nécessaire.

Une **seed** identifie un tirage reproductible de carte et de placement.
Les seeds de préparation (17), de feedback et de mesure finale sont séparées.
Les miroirs opposent une stratégie à elle-même et restent hors du score.

Enregistrer une configuration ne lance aucun appel. Avant une exécution
payante, l’écran de lancement demande de confirmer son plafond global.
Ce plafond inclut G0 et toutes les branches G1 ; chaque conversation a aussi
ses propres limites. Les réservations restent une estimation prudente de
la facturation et non une garantie universelle entre fournisseurs.

Une seule compétition est exécutée à la fois par ce serveur. **Arrêter**
conserve les checkpoints ; **Reprendre** les vérifie et réutilise les résultats
terminés. Si une réponse payante est incertaine, le système conserve sa
réservation et exige un rapprochement avec la facturation : la reprise ne
relance pas aveuglément cet appel. Le journal de lancement affiche les
messages et erreurs nécessaires au diagnostic.

Retirer un profil ou une configuration n’efface pas les résultats existants.
**Exporter** crée une copie autonome avec son inventaire d’empreintes, en
deuxième exemplaire dans `runs` ; les copies sont exclues des agrégations.

## 3. Explorer le code à chaque étape

**Code & versions** reconstruit les fichiers après chaque écriture réussie.
Choisir une conversation, une version et un fichier, puis comparer à une
version antérieure ou à l’état vide. Le diff distingue les ajouts et retraits ;
l’empreinte SHA-256 permet de reconnaître le contenu exact.

Les propositions de modification dont l’outil a renvoyé une erreur sont
visibles dans la conversation mais ne deviennent pas des versions du code.
Les branches G1 conservent aussi les écritures héritées de leur parent G0.
Le bouton **Voir la conversation** revient aux messages correspondants.

Il n’est pas nécessaire d’ajouter Git à chaque dossier d’IA : les contenus
sont déjà conservés dans le journal et les artefacts. L’explorateur est en
lecture seule, pour préserver les soumissions et leur reproductibilité.
**Fichiers** permet aussi de consulter et télécharger les sources figées,
les diagnostics, les configurations, les logs et les rapports.
Le bouton **Brut / Interprété** permet de lire les Markdown avec une mise en
forme simple (HTML échappé), et les JSON sous forme d’arbre repliable.
Les données statiques du moteur sont masquées par défaut ; cocher
**Inclure les données statiques du moteur** pour les consulter.

`data/forbidden_words.txt` est un fichier du moteur officiel Leek Wars,
copié avec ses ressources figées. Il ne s’agit pas d’une règle ajoutée par
l’arène pour filtrer les conversations LLM. Le bridge local ne charge pas
cette liste dans `Censorship.setSwearWords`. Le fichier reste conservé pour
respecter l’inventaire du moteur, sans filtrage de chat ajouté par l’arène.

## 4. Comprendre les conversations

**Conversations** affiche les prompts complets, les réponses retournées par
les fournisseurs, les appels d’outils et leurs résultats. Chaque objet peut
être ouvert intégralement, avec ses usages, coûts, identifiants de requête
et paramètres natifs lorsqu’ils ont été enregistrés. La pagination ne
supprime aucun message. **Suivre en direct** avance vers les nouveaux messages.

L’interface ne donne pas accès à un raisonnement interne que le fournisseur
n’a pas exposé. Elle montre exactement les données enregistrées, sans inventer
de texte intermédiaire. Les participants simulés ont les mêmes prompts et
outils que les participants réels ; leurs nouvelles requêtes sont affichées
explicitement. Les tournois recevant directement des scripts ne passent par
aucune génération : on peut consulter leurs sources figées dans **Code & versions**,
mais ils n’ont pas de prompts de génération.
Le **Journal** ajoute les horodatages et les étapes
d’exécution ; ouvrir un événement vérifie l’empreinte de son artefact.

## 5. Lire les combats

**Combats** filtre les rencontres par étape, adversaire ou seed. Le lecteur
présente une carte schématique, les positions, les PV et le journal des actions.
On peut lire, mettre en pause, changer de vitesse, avancer d’une action ou
se déplacer dans le replay avec le curseur. Les équipes bleue et orange
correspondent aux deux côtés indiqués pour la rencontre.

Cette projection reproduit les déplacements, tirs, dégâts, soins, variations
de vitalité, éliminations et résurrections enregistrés. Elle ne reproduit
pas toutes les animations ni tous les effets détaillés du client officiel.
Les actions brutes restent affichées ; une action inconnue n’est pas inventée.
Les métriques finales du moteur sont la référence pour le résultat.
**Statistiques du combat** affiche le total du combat, les totaux par équipe
et par leek, puis le détail par tour et par leek :
opérations, actions, tirs, puces, changements d’arme, déplacements, cases
parcourues, PA/PM retirés par les événements du replay, dégâts et soins donnés/reçus, érosion, morts,
erreurs et limites d’opérations. Une action correspond à un déplacement,
un changement d’arme, un tir ou une puce ; les effets automatiques ne sont
pas comptés comme des décisions. La limite du moteur figé est de
**20 000 000 opérations par tour joué et par leek**.

La télémétrie du bridge attribue les dégâts et soins à leur véritable source,
y compris les effets différés. Les anciennes archives n’ont pas les opérations
par tour ni toutes les attributions : ces valeurs restent `—`. Leurs dégâts
reçus sont ceux annoncés par le replay, qui peuvent inclure un surplus par
rapport aux PV restants. Les opérations cumulées historiques du moteur peuvent
être attribuées à l’invocateur pour ses invocations ; les nouveaux détails
distinguent chaque entité.
Une panne ou un timeout est visible même lorsqu’aucun replay n’a été produit.

## 6. Lire les bilans

Dans **Synthèse**, G0 signifie première stratégie, G1 signifie amélioration.
Le contrôle améliore sans résultats de combat ; le feedback améliore avec
ces résultats. Les deux branches partent du même historique.

Le score vaut `(victoires + 0,5 × nuls) / combats terminés`. Un score de 70 %
n’est donc pas nécessairement un taux de victoire de 70 %. Une différence de
0,4 dans le score représente **40 points de pourcentage**.

Le sélecteur du panel distingue tous les adversaires, les stratégies G0
figées et les contrôles fixes écrits à la main. Comparer les versions contre
un même panel permet d’éviter de confondre un changement de stratégie avec
un changement d’adversaires. Les classements contemporains G0 et G1 restent
consultables séparément dans les données complètes.
**Statistiques des combats** ajoute les totaux par stratégie et une matrice
ligne contre colonne (victoires / nuls / défaites, score et pannes). Le sélecteur
d’étape sépare préparation, tournois contemporains et panels G0/G1.
Les miroirs sont exclus de la matrice et inclus dans les totaux de jeu.

Les tableaux incluent scores, combats et pannes, opérations LeekScript,
erreurs, dépassements de limites, tokens et coûts. Les opérations ne sont
pas des tokens. Une valeur inconnue reste inconnue ; le coût nul d’une
simulation signifie absence d’appel API, hors coût de la machine.

## 7. Comparer plusieurs compétitions

**Comparer les résultats** agrège les scores contre les stratégies fixes,
avec un poids égal pour chaque conversation complète. Les conversations
incomplètes sont comptées à part. Les coûts et usages disponibles restent
consultables, y compris lorsque certains scores ne peuvent pas être retenus.

Seules les expériences ayant les mêmes règles, seeds finales, sources des
adversaires fixes, budgets et corpus de préparation, identité scientifique
du moteur et mode simulé/réel sont
réunies. Sinon, elles apparaissent dans des groupes séparés. Les paramètres
d’un modèle font aussi partie de son identité. Les exports ne sont pas
comptés une deuxième fois. Le graphique montre l’évolution entre exécutions ;
il ne construit pas un classement universel à partir de contextes différents.

## Développement et vérifications

Le serveur et le stockage utilisent uniquement la bibliothèque standard
Python. Les fichiers de l’interface sont inclus dans le package `arena_web`,
séparé du runner scientifique : changer son CSS ne modifie pas l’identité des
expériences. Le transport MCP garde sa dépendance optionnelle habituelle.

```bash
python -m unittest discover -s tests -p test_web.py -v
```

Ces tests couvrent les historiques, les clés, les plafonds, les protections
HTTP, les protocoles et, avec le moteur compilé, un arrêt/reprise et une
reprise sans recalcul par le worker de l’interface. Ils font partie de la
validation Linux et Windows.

Le workflow **Local web interface** teste également les parcours dans
Chromium, sur des archives synthétiques sans moteur ni API. Son outil de
vérification utilise Playwright 1.62.1 et Node 22 ; ils ne sont nécessaires
qu’au développement et à cette CI. Le script est `node scripts/test-ui.cjs`.
Il produit des captures dans `runs/ui-browser` ;
`ARENA_BROWSER_EXECUTABLE` peut choisir un Chromium déjà installé.


## Mettre à jour cette version

Le bridge enregistre désormais la télémétrie par tour et par entité. Après
mise à jour du dépôt, relancer `py -3 scripts/bootstrap.py` sous Windows
(ou le bootstrap Linux) pour recompiler ce bridge, puis redémarrer le serveur.
Les anciennes expériences restent consultables. Leur identité scientifique
ayant changé, dupliquer leur configuration pour un nouveau run ; une reprise
ancienne exige toujours le code et le runtime de sa création.
