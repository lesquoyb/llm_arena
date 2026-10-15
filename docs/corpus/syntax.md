# Syntaxe et état LeekScript 4

var déclare une variable ; if, while et break contrôlent le flot.
Les tableaux s'indexent à partir de zéro. Les fonctions de jeu sont
globales : aucun import Python ou JavaScript n'est nécessaire.
main.leek est le point d'entrée. include("lib/helper.leek") charge un
fichier de la même soumission ; liens et sorties du dossier sont refusés.
Les sources sont limitées à 128 fichiers .leek et 2 Mo au total.

Les variables ordinaires du script ne sont pas une sauvegarde entre
combats. Les registres de l'adaptateur démarrent vides pour chaque
combat, sans connexion PostgreSQL ni persistance globale.
Les APIs getAllies/isAlly et getEntity permettent de distinguer équipes
et entités ; leurs signatures figurent dans la référence.
say dépense 1 TP et sa taille et sa fréquence sont bornées par le moteur ;
listen retourne des paires ID/message. Cette communication n'est pas
un canal vers les fichiers d'autres sessions ou leurs conversations.

Sources : LeekScript au commit 8152f399faf7b418bbc5b2216d755c3822cda23b,
classes/EntityClass.java et l'adaptateur engine/ArenaMain.java.
Ce guide volontairement court couvre les exemples livrés. Il ne
prétend pas documenter intégralement toutes les sémantiques du langage.
