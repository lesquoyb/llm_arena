# Fonctions du contrôle, vérifiées dans le moteur figé

| Appel | Paramètres / retour | Coût de base déclaré |
|---|---|---:|
| getNearestEnemy() | ID de l'ennemi vivant le plus proche géométriquement ; −1 si absent. Ne pas supposer null. | 25 |
| getWeapons() | Tableau des IDs d'armes équipées de l'entité active. | 50 |
| setWeapon(weapon_id) | Sélectionne une arme équipée ; booléen, false pour arme absente/invalide. | 15 |
| moveToward(entity_id[, mp_to_use]) | Se rapproche ; retourne déplacement effectué. null ne déplace pas et produit un warning. | 500 |
| getTP() | TP restants de l'entité active. | 15 |
| getWeaponCost([weapon_id]) | Coût en TP ; sans argument, arme active ; −1 si inconnue ou absente. | 15 |
| isAlive(entity_id) | true si entité connue et vivante, false sinon. | 15 |
| useWeapon(entity_id) | Tente un tir ; code entier, comparer à USE_SUCCESS. −1 notamment si cible absente/invalide. | 3000 |

Les coûts déclarés ne sont pas nécessairement le coût total : moveToward
facture aussi des opérations dans son implémentation. Les effets et
portées dépendent de weapons.json. Ne pas boucler sur un tir échoué.
Un test d'analyse ne garantit pas l'efficacité ni l'absence d'erreur runtime.

Exemple sûr pour l'équipement avec au moins une arme :

```javascript
var enemy = getNearestEnemy()
if (enemy >= 0 && isAlive(enemy)) {
    setWeapon(getWeapons()[0])
    moveToward(enemy)
    while (getWeaponCost() >= 0 && getTP() >= getWeaponCost() && isAlive(enemy)) {
        if (useWeapon(enemy) != USE_SUCCESS) break
    }
}
```

Sources exactes : FightFunctions.java pour signatures/coûts,
classes/FightClass.java pour recherche/déplacement,
classes/EntityClass.java pour armes/TP/vie et
classes/WeaponClass.java pour coûts et tirs, au commit indiqué dans index.md.
Les autres fonctions restent décrites par la référence de signatures ;
leur comportement n'est pas déduit de leur nom.
