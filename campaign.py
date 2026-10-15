"""Campagne (5 missions x 3 factions), tutoriels par faction et progression sauvegardée."""
import json
import os

from game import FACTIONS, ABILITY

# faction jouée -> faction ennemie de sa campagne
ENEMY = {'kingdom': 'horde', 'horde': 'sylvan', 'sylvan': 'kingdom'}
# unité mise en avant dans la mission « armée » de chaque faction
SPECIAL = {'kingdom': 'knight', 'horde': 'soldier', 'sylvan': 'archer'}

STORY = {
    'kingdom': ("Les terres d'Aurèle", "Le roi vous confie le Château d'Aurèle. La Horde de Gorak rôde aux frontières : "
                "bâtissez, armez-vous, puis portez la guerre chez eux."),
    'horde': ("Le sang de Gorak", "Gorak vous donne sa Forteresse. Les elfes de la Sylve ont brûlé vos totems : "
              "pillez, forgez une armée et rasez leur Arbre-cité."),
    'sylvan': ("La voix de la forêt", "L'Arbre-cité d'Elenwë vous appelle. Les humains d'Aurèle abattent vos bois : "
               "défendez la forêt, puis frappez leur Château."),
}


def missions(fac):
    sp = SPECIAL[fac]
    foe = ENEMY[fac]
    return [
        dict(id=1, name='Premières récoltes', diff=0, enemy=foe,
             brief="Votre peuple a faim. Envoyez vos récolteurs au bois et au minerai : rassemblez 600 ressources. "
                   "Aucun ennemi n'est signalé... pour l'instant.",
             setup=dict(res=(200, 100), ai=dict(grace=9999, think=3.0),
                        mission=dict(type='gather', target=600))),
        dict(id=2, name='Levée des troupes', diff=0, enemy=foe,
             brief="Construisez une caserne (puis une écurie si besoin) et entraînez 8 unités de l'espèce demandée. "
                   "Les éclaireurs ennemis arrivent dans quelques minutes.",
             setup=dict(res=(300, 150), ai=dict(grace=420, think=2.2, wave_n=8),
                        mission=dict(type='army', target=8, kind=sp))),
        dict(id=3, name='Tenir la ligne', diff=1, enemy=foe,
             brief="L'ennemi lance de grosses vagues. Fortifiez-vous (tours !) et survivez 5 minutes.",
             setup=dict(res=(400, 200), units=[('soldier', 4), ('archer', 3)],
                        e_units=[('soldier', 5), ('archer', 3)], e_blds=[('barracks', 160, -120)],
                        ai=dict(grace=60, think=1.2, wave_n=5),
                        mission=dict(type='survive', target=300))),
        dict(id=4, name='Le raid', diff=1, enemy=foe,
             brief="Votre armée est déjà formée. Frappez vite la base ennemie avant qu'elle ne se renforce.",
             setup=dict(res=(300, 200), units=[('soldier', 6), ('archer', 4), ('knight', 3)],
                        e_units=[('soldier', 3), ('archer', 2)], ai=dict(grace=240, think=1.3, wave_n=7),
                        mission=dict(type='destroy_hq'))),
        dict(id=5, name='Guerre totale', diff=2, enemy=foe,
             brief="Ressources égales, ennemi acharné. Recherchez vos technologies, utilisez la capacité de faction "
                   "et détruisez leur base.",
             setup=dict(res=(500, 300), e_res=(500, 300),
                        units=[('soldier', 3), ('archer', 2)], e_units=[('soldier', 3), ('archer', 2)],
                        e_blds=[('barracks', 170, -110), ('tower', 210, 40)],
                        ai=dict(grace=150, think=0.9, wave_n=6),
                        mission=dict(type='destroy_hq'))),
    ]


# ---------------------------------------------------------------- tutoriel
def tutorial_steps(g):
    """Étapes du tutoriel, avec les noms propres à la faction du joueur (g.me)."""
    u = g.ust[g.me]
    b = g.bst[g.me]
    f = g.fac[g.me]
    ab = ABILITY[f]['name']
    mine = lambda: [e for e in g.ents if e.team == g.me and not e.dead]
    return [
        dict(text="Bienvenue ! Touchez un %s pour le sélectionner, puis touchez une forêt pour le faire récolter. "
                  "Faites travailler 3 récolteurs." % u['worker']['label'].lower(),
             done=lambda: sum(1 for e in mine() if e.kind == 'worker' and e.mode == 'harvest') >= 3),
        dict(text="Touchez votre %s, puis choisissez une unité de base à produire dans la barre du bas." % b['hq']['label'],
             done=lambda: any(e.queue for e in mine() if e.kind == 'hq') or g.pop(g.me) > 4),
        dict(text="Sélectionnez un récolteur et construisez : %s (barre du bas), puis touchez le sol à côté de votre base."
                  % b['barracks']['label'],
             done=lambda: any(e.kind == 'barracks' for e in mine())),
        dict(text="Attendez la fin du chantier : le récolteur construit tout seul.",
             done=lambda: any(e.kind == 'barracks' and e.built for e in mine())),
        dict(text="Touchez la %s et entraînez 3 unités de combat." % b['barracks']['label'].lower(),
             done=lambda: len(g.mil(g.me)) >= 4),
        dict(text="Bâtissez une %s avec un récolteur : elle débloque les recherches." % b['forge']['label'].lower(),
             done=lambda: any(e.kind == 'forge' and e.built for e in mine())),
        dict(text="Ouvrez le bouton « Techs » et lancez une recherche.",
             done=lambda: bool(g.techs[g.me]) or bool(g.rsch[g.me])),
        dict(text="Touchez « Capacité » pour déclencher : %s." % ab,
             done=lambda: g.ab_t[g.me] > 0 or g.ab_cd[g.me] > 0),
        dict(text="Bouton « Armée » puis touchez l'ennemi : attaquez et détruisez sa base pour gagner !",
             done=lambda: False),
    ]


class Tutorial:
    def __init__(self, g):
        self.g = g
        self.steps = tutorial_steps(g)
        self.i = 0

    def update(self):
        if self.i < len(self.steps) and self.steps[self.i]['done']():
            self.i += 1
            self.g.step_i = self.i
            self.g.step_flash = 1.5

    def text(self):
        if self.i >= len(self.steps):
            return ''
        return 'Tutoriel %d/%d : %s' % (self.i + 1, len(self.steps), self.steps[self.i]['text'])


def tutorial_setup():
    return dict(res=(400, 200), ai=dict(grace=1200, think=3.0, wave_n=12), mission=dict(type='destroy_hq'))


# ---------------------------------------------------------------- progression
def _file(base):
    return os.path.join(base, 'progress.json')


def load_progress(base):
    try:
        with open(_file(base)) as f:
            d = json.load(f)
        return {k: int(v) for k, v in d.items() if k in FACTIONS}
    except Exception:
        return {}


def save_progress(base, prog):
    try:
        os.makedirs(base, exist_ok=True)
        with open(_file(base), 'w') as f:
            json.dump(prog, f)
    except Exception:
        pass


def unlocked(prog, fac):
    """Nombre de missions terminées (la suivante est jouable)."""
    return prog.get(fac, 0)
