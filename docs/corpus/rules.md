# Règles et catalogue de préparation

Les deux équipes ont même effectif, statistiques, armes et puces.
Le manifeste fixe l'équipement ; il est communiqué dans le prompt initial.
Chaque membre exécute le même point d'entrée à chacun de ses tours.
Victoire moteur : côté 0 ou 1 ; nul : −1. Les entités du replay utilisent
des équipes numérotées 1 et 2. Les miroirs sont diagnostiques et exclus
du score principal.

TP limite les actions, MP les déplacements, cores × 1 000 000 les
opérations par tour. RAM limite la mémoire LeekScript ; le heap Java
est un garde-fou distinct. La fin de durée peut être max_turns + 1
dans le compteur moteur. Les temps sont des temps écoulés, pas CPU.

La carte possède 613 identifiants de cases (0–612). Les obstacles
interdisent le placement et influencent chemin et visibilité.
getDistance mesure la distance géométrique ; getCellDistance mesure
la distance de grille sans garantir un chemin praticable.
Une arme doit être équipée, avoir des TP suffisants, respecter portée
et règles de ligne de vue de sa fiche ; vérifier le code de useWeapon.

Préparation publique : scenario_id training, seed_id train-17,
opponent_id passive. test exécute les deux positions et consomme
deux combats. Les seeds de feedback et de mesure finale sont distinctes
et ne sont jamais acceptées par l'outil test. Les scores de G1 sont
comparés sur le même panel G0 figé et les mêmes contrôles fixes.

Sources : Fight.java, maps/Map.java, classes/FieldClass.java,
state/State.java et fight/entity/EntityAI.java dans le générateur figé.
Le texte est une synthèse originale des sources ; les données et
signatures gardent leur attribution au projet Leek Wars / LeekScript.
