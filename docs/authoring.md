# Écrire une stratégie pour l'arène

Le moteur exécute du LeekScript 4. Le fichier `main.leek` constitue la logique d'un tour. Les fonctions globales du jeu sont disponibles sans import. Chaque entité joue sa stratégie à son tour ; les équipes disposent de statistiques et d'équipements identiques fixés par le scénario.

Les points d'action (`getTP()`) et de mouvement (`getMP()`) limitent les actions de jeu. Le compteur `getOperations()` limite le calcul exécuté pendant le tour. Ce sont trois ressources différentes. Dans le pilote, chaque entité a 10 cœurs, soit 10 millions d'opérations par tour. Une stratégie de recherche doit rendre son action avant d'épuiser son budget.

Exemple minimal testé sur l'équipement du pilote :

```javascript
var enemy = getNearestEnemy()
if (enemy != null) {
    setWeapon(getWeapons()[0])
    moveToward(enemy)
    while (getTP() >= getWeaponCost() && isAlive(enemy)) {
        if (useWeapon(enemy) != USE_SUCCESS) break
    }
}
```

`getWeapons()` donne les armes équipées ; `setWeapon` sélectionne l'arme active. `moveToward` dépense du mouvement pour se rapprocher de la cible. `useWeapon` tente un tir et renvoie un code de résultat : vérifier `USE_SUCCESS` pour éviter une boucle sans progrès lorsque la cible est hors de portée ou masquée. Le script ci-dessus suppose au moins une arme, comme le scénario fourni.

Les fichiers de support doivent être dans le même dossier de soumission. Par exemple, `include("lib/targeting.leek")` charge un fichier interne. Aucun fichier d'un adversaire ni fichier extérieur n'est accessible par le résolveur. Les registres démarrent vides à chaque combat et ne persistent pas entre combats.

Tester l'analyse, puis le comportement réel : une IA peut être syntaxiquement valide sans agir efficacement.

```powershell
python -m arena analyze chemin/vers/ma-strategie
python -m arena fight chemin/vers/ma-strategie examples/strategies/rush
```

Lire `outcome.json` pour le replay et les logs de jeu, `result.json` pour le résultat compact et les métriques par équipe. Les commandes impriment le chemin du dossier d'artefacts créé.

La [référence figée](leekscript-v1/api.md) donne les signatures et coûts de base déclarés. `weapons.json`, `chips.json` et `summons.json` dans le même dossier contiennent les caractéristiques du jeu utilisées. Les noms d'arguments et les descriptions détaillées des effets seront enrichis avant les expériences LLM.
