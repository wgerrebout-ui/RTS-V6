"""Rendu Kivy du monde : dessin procédural lisible (silhouettes différentes par type d'unité et de bâtiment,
couleurs par faction, anneau d'équipe). Si assets/<faction>_<type>.png existe, il remplace le dessin."""
import math
import os

from kivy.graphics import Color, Ellipse, Line, Quad, Rectangle, Triangle
from kivy.core.image import Image as CoreImage

from game import MAP_W, MAP_H

TEAM = {0: (0.25, 0.55, 1.0), 1: (1.0, 0.3, 0.25)}
# (corps, accent) par faction
PAL = {'kingdom': ((0.85, 0.8, 0.65), (0.95, 0.8, 0.2)),
       'horde': ((0.45, 0.62, 0.3), (0.7, 0.15, 0.1)),
       'sylvan': ((0.78, 0.9, 0.75), (0.2, 0.65, 0.35))}
WALL = {'kingdom': (0.72, 0.72, 0.78), 'horde': (0.4, 0.28, 0.2), 'sylvan': (0.55, 0.42, 0.28)}
ROOF = {'kingdom': (0.2, 0.35, 0.75), 'horde': (0.55, 0.1, 0.1), 'sylvan': (0.2, 0.6, 0.3)}
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
_tex = {}


def tex(name):
    if name not in _tex:
        p = os.path.join(ASSETS, name + '.png')
        try:
            _tex[name] = CoreImage(p).texture if os.path.exists(p) else None
        except Exception:
            _tex[name] = None
    return _tex[name]


class View:
    """Caméra + conversions monde <-> écran (origine écran en bas à gauche)."""

    def __init__(self):
        self.zoom = 1.0
        self.w = self.h = 100

    def to_screen(self, g, x, y):
        return (x - g.cam[0]) * self.zoom, self.h - (y - g.cam[1]) * self.zoom

    def to_world(self, g, sx, sy):
        return sx / self.zoom + g.cam[0], (self.h - sy) / self.zoom + g.cam[1]

    def clamp(self, g):
        g.cam[0] = max(0, min(MAP_W - self.w / self.zoom, g.cam[0]))
        g.cam[1] = max(0, min(MAP_H - self.h / self.zoom, g.cam[1]))

    def center(self, g, x, y):
        g.cam[0], g.cam[1] = x - self.w / 2 / self.zoom, y - self.h / 2 / self.zoom
        self.clamp(g)


def circle(x, y, r, col, a=1.0):
    Color(*col, a)
    Ellipse(pos=(x - r, y - r), size=(2 * r, 2 * r))


def ring(x, y, rx, ry, col, w=1.5, a=1.0):
    Color(*col, a)
    Line(ellipse=(x - rx, y - ry, 2 * rx, 2 * ry), width=w)


def line(pts, col, w=2.0, a=1.0):
    Color(*col, a)
    Line(points=pts, width=w)


def bar(x, y, w, frac, col):
    Color(0, 0, 0, 0.6)
    Rectangle(pos=(x - w / 2 - 1, y - 1), size=(w + 2, 5))
    Color(*col, 1)
    Rectangle(pos=(x - w / 2, y), size=(w * max(0, min(1, frac)), 3))


# ---------------------------------------------------------------- terrain
def draw_ground(v, g):
    Color(0.2, 0.34, 0.2, 1)
    Rectangle(pos=(0, 0), size=(v.w, v.h))
    step = 160 * v.zoom
    ox, oy = -(g.cam[0] * v.zoom) % step, -(g.cam[1] * v.zoom) % step
    Color(0.23, 0.38, 0.23, 1)
    n = int(max(v.w, v.h) / step) + 2
    for i in range(n):
        for j in range(n):
            if (i + j) % 2 == 0:
                Rectangle(pos=(ox + i * step - step, oy + j * step - step), size=(step, step))
    # bords de la carte
    x0, y0 = v.to_screen(g, 0, MAP_H)
    x1, y1 = v.to_screen(g, MAP_W, 0)
    Color(0.9, 0.9, 0.9, 0.5)
    Line(rectangle=(x0, y0, x1 - x0, y1 - y0), width=2)


def draw_props(v, g):
    z = v.zoom
    for x, y, r in g.ponds:
        sx, sy = v.to_screen(g, x, y)
        if -r * z < sx < v.w + r * z and -r * z < sy < v.h + r * z:
            circle(sx, sy, r * z * 1.05, (0.55, 0.75, 0.9), 0.5)
            circle(sx, sy, r * z, (0.2, 0.45, 0.75))
            ring(sx - r * z * .25, sy + r * z * .2, r * z * .3, r * z * .12, (0.8, 0.92, 1), 1.2, 0.6)
    for x, y, r in g.rocks:
        sx, sy = v.to_screen(g, x, y)
        if -r * z < sx < v.w + r * z and -r * z < sy < v.h + r * z:
            circle(sx + 2 * z, sy - 3 * z, r * z, (0.15, 0.2, 0.15), 0.5)
            circle(sx, sy, r * z, (0.5, 0.5, 0.52))
            circle(sx - r * z * .25, sy + r * z * .25, r * z * .5, (0.65, 0.65, 0.68))
    for r in g.res:
        sx, sy = v.to_screen(g, r.x, r.y)
        if not (-40 < sx < v.w + 40 and -40 < sy < v.h + 40):
            continue
        if r.kind == 'wood':   # arbre : tronc brun + houppier vert
            Color(0.4, 0.26, 0.12, 1)
            Rectangle(pos=(sx - 2.5 * z, sy - 14 * z), size=(5 * z, 12 * z))
            circle(sx, sy + 3 * z, 12 * z, (0.1, 0.4, 0.15))
            circle(sx - 3 * z, sy + 7 * z, 8 * z, (0.18, 0.55, 0.22))
        else:                  # minerai : cristaux dorés
            Color(0.3, 0.3, 0.3, 1)
            Ellipse(pos=(sx - 15 * z, sy - 13 * z), size=(30 * z, 14 * z))
            for dx, hh, c in ((-7, 20, (0.95, 0.8, 0.2)), (2, 26, (1, 0.9, 0.35)), (9, 15, (0.85, 0.65, 0.1))):
                Color(*c, 1)
                Triangle(points=(sx + (dx - 5) * z, sy - 4 * z, sx + (dx + 5) * z, sy - 4 * z, sx + dx * z, sy + hh * z - 4 * z))
        if r.amount < r.max:
            bar(sx, sy - 22 * z, 22 * z, r.amount / r.max, (0.9, 0.9, 0.3))


# ---------------------------------------------------------------- unités
def draw_unit(v, g, e):
    z = v.zoom
    sx, sy = v.to_screen(g, e.x, e.y)
    if not (-40 < sx < v.w + 40 and -40 < sy < v.h + 40):
        return
    fac = g.fac[e.team]
    body, acc = PAL[fac]
    r = e.r * z
    tc = TEAM[e.team]
    t = g.time
    walk = math.sin(t * 12 + e.id) * 2 * z if e.moving else 0
    ring(sx, sy - r * .6, r * 1.15, r * .55, tc, 2.2, 0.95)          # anneau d'équipe
    t_img = tex('%s_%s' % (fac, e.kind))
    ca, sa = math.cos(e.ang), -math.sin(e.ang)                       # direction (écran : y inversé)
    if t_img is not None:
        Color(1, 1, 1, 1)
        Rectangle(texture=t_img, pos=(sx - r * 1.4, sy - r * 1.2), size=(r * 2.8, r * 2.8))
    else:
        k = e.kind
        if e.flash > 0:
            circle(sx, sy, r * 1.35, (1, 1, 0.7), 0.5)
        if k == 'worker':
            circle(sx, sy + walk, r, body)
            line((sx - ca * r * .2, sy, sx + ca * r * 1.5, sy + sa * r * 1.5 + (2 * z * math.sin(t * 14) if e.working else 0)), (0.5, 0.35, 0.2), 2.5 * z)
            if e.carry:
                circle(sx, sy + r * 1.1, 4 * z, (0.9, 0.7, 0.2) if e.ctype == 'ore' else (0.45, 0.3, 0.12))
        elif k == 'soldier':
            circle(sx, sy + walk, r, body)
            circle(sx + ca * r * .8, sy + sa * r * .8, r * .55, acc)           # bouclier
            line((sx - ca * r * .6, sy - sa * r * .6, sx - ca * r * .6 + sa * r * .2 - ca * r, sy - sa * r * .6 + ca * r * .2 + sa * r), (0.85, 0.85, 0.9), 2.5 * z)
        elif k == 'archer':
            circle(sx, sy + walk, r, body)
            bx, by = sx + ca * r * 1.2, sy + sa * r * 1.2
            Color(0.5, 0.33, 0.15, 1)
            Line(circle=(bx, by, r * .9, math.degrees(math.atan2(ca, sa)) - 70, math.degrees(math.atan2(ca, sa)) + 70), width=2 * z)
            circle(sx, sy + r * .1, r * .45, acc)
        elif k == 'knight':
            Color(*[c * .75 for c in body], 1)
            Ellipse(pos=(sx - r * 1.4, sy - r * .8), size=(r * 2.8, r * 1.4))     # monture
            circle(sx + ca * r * 1.1, sy + sa * r * .5 + r * .2, r * .55, (0.8, 0.8, 0.8))
            circle(sx, sy + r * .55, r * .6, acc)                                  # cavalier
            line((sx, sy + r * .5, sx + ca * r * 2.2, sy + sa * r * 2.2 + r * .5), (0.9, 0.9, 0.95), 2 * z)
        elif k == 'healer':
            circle(sx, sy, r * 1.3, (0.5, 1, 0.6), 0.25 + 0.15 * math.sin(t * 4))
            circle(sx, sy, r, (0.95, 0.95, 1))
            Color(0.9, 0.15, 0.15, 1)
            Rectangle(pos=(sx - r * .2, sy - r * .65), size=(r * .4, r * 1.3))
            Rectangle(pos=(sx - r * .65, sy - r * .2), size=(r * 1.3, r * .4))
        elif k == 'heavy':
            if fac == 'kingdom':      # catapulte
                Color(0.45, 0.3, 0.15, 1)
                Rectangle(pos=(sx - r, sy - r * .6), size=(r * 2, r * 1.2))
                circle(sx - r * .7, sy - r * .7, r * .4, (0.2, 0.15, 0.1))
                circle(sx + r * .7, sy - r * .7, r * .4, (0.2, 0.15, 0.1))
                line((sx, sy, sx + ca * r * 1.5, sy + sa * r * 1.5 + r), (0.6, 0.4, 0.2), 3 * z)
                circle(sx + ca * r * 1.5, sy + sa * r * 1.5 + r, r * .35, (0.4, 0.4, 0.4))
            elif fac == 'horde':      # ogre
                circle(sx, sy, r, (0.55, 0.55, 0.3))
                circle(sx, sy + r * .9, r * .5, (0.6, 0.6, 0.35))
                line((sx + r * .8, sy - r * .8, sx + r * 1.3, sy + r * 1.3), (0.4, 0.25, 0.1), 5 * z)
                circle(sx + r * 1.3, sy + r * 1.3, r * .4, (0.45, 0.3, 0.15))
            else:                     # ent
                Color(0.35, 0.24, 0.12, 1)
                Rectangle(pos=(sx - r * .45, sy - r), size=(r * .9, r * 1.6))
                circle(sx, sy + r * .8, r, (0.12, 0.45, 0.2))
                circle(sx - r * .5, sy + r * 1.1, r * .6, (0.22, 0.6, 0.3))
        else:
            circle(sx, sy, r, body)
    if e in g.sel:
        ring(sx, sy - r * .4, r * 1.5, r * .85, (1, 1, 1), 2.5)
    if e.hp < e.maxhp or e in g.sel:
        bar(sx, sy + r * 1.6, max(20, r * 2.2), e.hp / e.maxhp, (0.3, 0.9, 0.3) if e.hp > e.maxhp * .4 else (0.95, 0.3, 0.2))


# ---------------------------------------------------------------- bâtiments
def draw_building(v, g, e):
    z = v.zoom
    sx, sy = v.to_screen(g, e.x, e.y)
    r = e.r * z
    if not (-r * 2 < sx < v.w + r * 2 and -r * 2 < sy < v.h + r * 2):
        return
    fac = g.fac[e.team]
    k = e.kind
    ring(sx, sy - r * .5, r * 1.25, r * .7, TEAM[e.team], 3, 0.9)
    a = 1.0 if e.built else 0.55
    t_img = tex('%s_%s' % (fac, k))
    if t_img is not None:
        Color(1, 1, 1, a)
        Rectangle(texture=t_img, pos=(sx - r, sy - r * .6), size=(r * 2, r * 2))
    else:
        wall, roof = WALL[fac], ROOF[fac]
        Color(*[c * .55 for c in wall], a)
        Rectangle(pos=(sx - r * .95, sy - r * .85), size=(r * 1.9, r * .4))
        Color(*wall, a)
        Rectangle(pos=(sx - r * .85, sy - r * .65), size=(r * 1.7, r * 1.15))
        if k == 'tower':
            Color(*wall, a)
            Rectangle(pos=(sx - r * .5, sy - r * .65), size=(r, r * 2.2))
            Color(*roof, a)
            Triangle(points=(sx - r * .7, sy + r * 1.55, sx + r * .7, sy + r * 1.55, sx, sy + r * 2.3))
        elif k == 'hq':
            Color(*roof, a)
            Triangle(points=(sx - r, sy + r * .5, sx + r, sy + r * .5, sx, sy + r * 1.3))
            for dx in (-.7, .7):
                Color(*wall, a)
                Rectangle(pos=(sx + dx * r - r * .2, sy + r * .5), size=(r * .4, r * .7))
            line((sx, sy + r * 1.3, sx, sy + r * 1.9), (0.3, 0.2, 0.1), 2 * z)
            Color(*TEAM[e.team], a)
            Triangle(points=(sx, sy + r * 1.9, sx + r * .5, sy + r * 1.7, sx, sy + r * 1.5))
        else:
            Color(*roof, a)
            Triangle(points=(sx - r * .98, sy + r * .5, sx + r * .98, sy + r * .5, sx, sy + r * 1.15))
        # emblème selon le type
        Color(1, 1, 1, a)
        if k == 'barracks':
            line((sx - r * .35, sy - r * .4, sx + r * .35, sy + r * .3), (0.95, 0.95, 1), 3 * z, a)
            line((sx + r * .35, sy - r * .4, sx - r * .35, sy + r * .3), (0.95, 0.95, 1), 3 * z, a)
        elif k == 'stable':
            Color(0.95, 0.85, 0.3, a)
            Line(circle=(sx, sy - r * .05, r * .3, 40, 320), width=3 * z)
        elif k == 'depot':
            for dx in (-.4, .1):
                Color(0.65, 0.45, 0.2, a)
                Rectangle(pos=(sx + dx * r, sy - r * .5), size=(r * .45, r * .45))
        elif k == 'forge':
            Color(1, 0.55, 0.1, a)
            circle(sx, sy - r * .1, r * .3, (1, 0.5 + 0.2 * math.sin(g.time * 6), 0.1), a)
            Color(0.25, 0.25, 0.28, a)
            Rectangle(pos=(sx - r * .35, sy - r * .5), size=(r * .7, r * .2))
        elif k == 'temple':
            Color(0.95, 0.95, 1, a)
            Rectangle(pos=(sx - r * .12, sy - r * .5), size=(r * .24, r * .9))
            Rectangle(pos=(sx - r * .4, sy - r * .1), size=(r * .8, r * .24))
        elif k == 'sanctum':
            Color(0.9, 0.75, 0.2, a)
            Line(circle=(sx, sy - r * .05, r * .4), width=3 * z)
            circle(sx, sy - r * .05, r * .15, (0.9, 0.75, 0.2), a)
    if not e.built:
        bar(sx, sy + r * 1.2, r * 1.6, e.bt / max(1, e.d['time']), (0.95, 0.8, 0.2))
    if e.queue:
        tm = g.ust[e.team][e.queue[0]]['time']
        bar(sx, sy + r * 1.1, r * 1.6, e.qt / tm, (0.4, 0.7, 1))
    if e in g.sel:
        ring(sx, sy, r * 1.35, r * 1.0, (1, 1, 1), 2.5)
    if e.hp < e.maxhp:
        bar(sx, sy - r * 1.05, r * 1.6, e.hp / e.maxhp, (0.3, 0.9, 0.3))


# ---------------------------------------------------------------- effets
def draw_fx(v, g):
    z = v.zoom
    for f in g.fx:
        if f['t'] == 'p':
            sx, sy = v.to_screen(g, f['x'], f['y'])
            circle(sx, sy, f['size'] * z, f['col'], max(0, f['life'] / f['max']))
        else:
            x0, y0 = v.to_screen(g, f['x'], f['y'])
            x1, y1 = v.to_screen(g, f['x1'], f['y1'])
            k = 1 - f['life'] / f['max']
            px, py = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
            p = f.get('p', 'arrow')
            if p == 'orb':
                circle(px, py, 5 * z, (0.5, 1, 0.8), 0.9)
            elif p == 'bolt':
                line((px, py, px - (x1 - x0) * .08, py - (y1 - y0) * .08), (1, 0.4, 0.2), 3 * z)
            else:
                line((px, py, px - (x1 - x0) * .1, py - (y1 - y0) * .1), (0.95, 0.95, 0.8), 2 * z)
    for c in g.corpses:
        sx, sy = v.to_screen(g, c['x'], c['y'])
        circle(sx, sy - 4 * z, 9 * z, TEAM[c['team']], max(0, c['life'] / 3.2) * 0.5)


def draw_world(v, g):
    draw_ground(v, g)
    draw_props(v, g)
    for e in g.ents:
        if e.b and not e.dead:
            draw_building(v, g, e)
    for e in sorted((e for e in g.ents if not e.b and not e.dead), key=lambda e: e.y):
        draw_unit(v, g, e)
    draw_fx(v, g)
    # fantôme de construction
    if g.placing and getattr(v, 'ghost', None):
        wx, wy = v.ghost
        sx, sy = v.to_screen(g, wx, wy)
        r = g.bst[g.me][g.placing]['r'] * v.zoom
        ok = g.can_place(g.me, g.placing, wx, wy)
        circle(sx, sy, r, (0.2, 1, 0.3) if ok else (1, 0.2, 0.2), 0.35)
        ring(sx, sy, r, r, (1, 1, 1), 2)
    if g.drag:
        x0, y0, x1, y1 = g.drag
        Color(1, 1, 1, 0.9)
        Line(rectangle=(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0)), width=1.5)


def draw_minimap(v, g, x, y, w, h):
    Color(0, 0, 0, 0.6)
    Rectangle(pos=(x - 2, y - 2), size=(w + 4, h + 4))
    Color(0.2, 0.34, 0.2, 1)
    Rectangle(pos=(x, y), size=(w, h))
    kx, ky = w / MAP_W, h / MAP_H
    for px, py, r in g.ponds:
        circle(x + px * kx, y + h - py * ky, r * kx, (0.2, 0.45, 0.75))
    for r in g.res:
        Color(0.2, 0.5, 0.2, 1) if r.kind == 'wood' else Color(0.9, 0.8, 0.2, 1)
        Rectangle(pos=(x + r.x * kx - 1, y + h - r.y * ky - 1), size=(2, 2))
    for e in g.ents:
        if e.dead:
            continue
        s = 5 if e.b else 3
        Color(*TEAM[e.team], 1)
        Rectangle(pos=(x + e.x * kx - s / 2, y + h - e.y * ky - s / 2), size=(s, s))
    Color(1, 1, 1, 0.9)
    Line(rectangle=(x + g.cam[0] * kx, y + h - (g.cam[1] + v.h / v.zoom) * ky, v.w / v.zoom * kx, v.h / v.zoom * ky), width=1.2)
