# MINI RTS v6

Jeu de stratégie en temps réel pour Android (Python / Kivy), jouable en solo ou à deux téléphones sur le même Wi-Fi.

## Fonctionnalités

- **3 factions** bien différenciées (unités, bâtiments, statistiques, arbre technologique et capacité propres) :
  - **Royaume d'Aurèle** : équilibré, bâtiments robustes, catapultes, prêtres. Capacité : *Ordre royal*.
  - **Horde de Gorak** : brutale et bon marché, loups rapides, ogres, bâtiments fragiles. Capacité : *Fureur sanguinaire*.
  - **Sylve d'Elenwë** : précise et agile, archers longue portée, tours redoutables, Ents. Capacité : *Souffle de la forêt*.
- **Escarmouche** : choix des deux factions et de la difficulté (Facile / Normal / Difficile).
- **Campagne** : 5 missions par faction (récolte, levée d'armée, survie, raid, guerre totale), progression sauvegardée.
- **Tutoriel** par faction (9 étapes : économie, construction, armée, recherches, capacité, attaque).
- **Multijoueur** téléphone à téléphone en Wi-Fi local (TCP, port 47625).
- **Arbre technologique** (12 recherches par faction) et **capacité active** de faction.
- **Rendu lisible** : silhouette distincte par unité et par bâtiment, anneau d'équipe bleu/rouge, minimap.
- **Intro animée** au lancement.

## Structure du dépôt

| Fichier | Rôle |
|---|---|
| `main.py` | Application Kivy : intro, menus, écran de jeu, commandes tactiles |
| `game.py` | Moteur : carte, unités, bâtiments, combat, déplacement, IA, instantanés réseau |
| `game_ext.py` | Extensions du moteur : recherches, capacités, soigneurs, régénération, IA de recherche |
| `campaign.py` | Missions, tutoriel, sauvegarde de progression |
| `net.py` | Réseau hôte / client |
| `render.py` | Dessin du monde et de la minimap |
| `assets/` | *(optionnel)* PNG `<faction>_<type>.png` qui remplacent le dessin procédural |

`game_ext.py` doit être importé **avant** la création d'un `Game()` (c'est le cas dans `main.py`).

## Jouer

**Commandes tactiles**

- Tap sur une unité ou un bâtiment : sélection. Double tap : toutes les unités du même type à l'écran.
- Tap sur le sol, une ressource ou un ennemi avec une sélection : déplacement, récolte ou attaque.
- Glisser sur le sol : déplacer la caméra. Minimap : tap pour s'y rendre. Boutons `+` / `−` : zoom.
- Bouton **Boîte** puis glisser : sélection par rectangle.
- Bouton **Attaque** : le prochain ordre devient un déplacement offensif.
- **Armée**, **Inactifs**, **Stop**, **Pause** : raccourcis de sélection et de contrôle.
- **Construire** : sélectionner un récolteur, choisir le bâtiment, glisser puis relâcher à l'emplacement voulu.
- **Techs** : ouvre l'arbre technologique. **Capacité** : déclenche la capacité de faction.

**Prérequis de construction** : Forge et Temple demandent une Caserne ; le Sanctuaire demande une Forge.

## Multijoueur

1. Les deux téléphones sont sur le même Wi-Fi.
2. Le premier choisit *Multijoueur → Héberger une partie* (son IP s'affiche).
3. Le second saisit cette IP et appuie sur *Rejoindre*.

L'hôte simule la partie, le client reçoit des instantanés et envoie ses ordres.

## Lancer sur ordinateur

```bash
pip install kivy
python main.py
```

## Compiler l'APK (Buildozer)

Extrait de `buildozer.spec` :

```ini
requirements = python3,kivy
source.include_exts = py,png
orientation = landscape
android.archs = arm64-v8a
android.api = 33
android.ndk = 25b
```

Le build via GitHub Actions utilise Java 17.

## Ajouter des images

Déposer des PNG dans `assets/` nommés `<faction>_<type>.png`, par exemple `horde_soldier.png` ou `kingdom_barracks.png`.
Factions : `kingdom`, `horde`, `sylvan`. Unités : `worker`, `soldier`, `archer`, `knight`, `healer`, `heavy`.
Bâtiments : `hq`, `barracks`, `stable`, `depot`, `tower`, `forge`, `temple`, `sanctum`.
Un PNG absent est remplacé par le dessin procédural.

## Limites connues

- Pas de brouillard de guerre, pas de son.
- Multijoueur à deux joueurs uniquement, réseau local.
- L'interface Kivy a été validée avec un faux module graphique : à tester sur téléphone.
