"""MINI RTS v6 - application Kivy (Android) : intro, menus, escarmouche, campagne, tutoriel, multijoueur."""
import math
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, Quad, Rectangle, Triangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

import game_ext  # noqa: F401  (installe techs, capacités, soigneurs : à importer avant Game)
import campaign
import net
import render
from game import Game, FACTIONS, ABILITY, TECH_ORDER, tech_info, DIFF_NAMES, POP_MAX

FAC_ORDER = ['kingdom', 'horde', 'sylvan']
FAC_COL = {'kingdom': (0.2, 0.35, 0.8, 1), 'horde': (0.7, 0.2, 0.15, 1), 'sylvan': (0.2, 0.55, 0.3, 1)}
BG = (0.07, 0.09, 0.12, 1)


def btn(text, cb, col=(0.2, 0.28, 0.4, 1), fs=18, **kw):
    b = Button(text=text, font_size=sp(fs), background_normal='', background_color=col, halign='center', **kw)
    b.bind(on_release=lambda *_: cb())
    b.bind(size=lambda w, s: setattr(w, 'text_size', (s[0] - dp(8), None)))
    return b


def label(text, fs=18, **kw):
    kw.setdefault('halign', 'center')
    lb = Label(text=text, font_size=sp(fs), valign='middle', **kw)
    lb.bind(size=lambda w, s: setattr(w, 'text_size', s))
    return lb


class Chooser(BoxLayout):
    """Rangée de boutons exclusifs. .value = valeur choisie."""

    def __init__(self, options, default=None, **kw):
        super().__init__(spacing=dp(6), size_hint_y=None, height=dp(52), **kw)
        self.options, self.value, self.bs = options, default if default is not None else options[0][0], {}
        for val, txt, col in options:
            b = btn(txt, lambda v=val: self.set(v), col)
            self.bs[val] = b
            self.add_widget(b)
        self.set(self.value)

    def set(self, v):
        self.value = v
        for val, txt, col in self.options:
            self.bs[val].background_color = col if val == v else tuple(c * .35 for c in col[:3]) + (1,)


def fac_options():
    return [(f, FACTIONS[f]['short'], FAC_COL[f]) for f in FAC_ORDER]


# ================================================================ intro animée
class Intro(FloatLayout):
    DUR = 8.0

    def __init__(self, on_done, **kw):
        super().__init__(**kw)
        self.on_done, self.t, self.done = on_done, 0.0, False
        self.title = label('MINI RTS', 60, bold=True, color=(1, 0.9, 0.5, 0), pos_hint={'center_x': .5, 'center_y': .62})
        self.sub = label('', 20, color=(1, 1, 1, 0), pos_hint={'center_x': .5, 'center_y': .22}, size_hint=(.9, .2))
        self.skip = label('Touchez pour passer', 14, color=(1, 1, 1, .4), pos_hint={'center_x': .5, 'y': .02}, size_hint=(1, .06))
        for w in (self.title, self.sub, self.skip):
            self.add_widget(w)
        self.ev = Clock.schedule_interval(self.tick, 1 / 30.)

    def tick(self, dt):
        self.t += dt
        t = self.t
        self.title.color = (1, 0.9, 0.5, max(0, min(1, (t - 0.5) / 1.5)))
        names = [("Royaume d'Aurèle", 2.5), ('Horde de Gorak', 4.0), ("Sylve d'Elenwë", 5.5)]
        cur = ''
        for n, t0 in names:
            if t >= t0:
                cur = n
        self.sub.text = cur
        self.sub.color = (1, 1, 1, 1 if t >= 2.5 else 0)
        self.draw()
        if t >= self.DUR:
            self.finish()

    def draw(self):
        w, h = self.size
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*BG)
            Rectangle(pos=self.pos, size=self.size)
            t = self.t
            for i in range(60):                       # braises qui montent
                x = (i * 137.5) % w
                y = ((i * 71 + t * (30 + i % 7 * 9)) % h)
                Color(1, 0.6, 0.2, 0.25 + 0.25 * math.sin(t * 3 + i))
                Ellipse(pos=(x, y), size=(3, 3))
            cx, cy, s = w / 2, h * .42, min(w, h) * .11
            for i, f in enumerate(FAC_ORDER):          # trois emblèmes qui apparaissent un à un
                a = max(0, min(1, (t - (2.2 + i * 1.5)) / 0.8))
                if a <= 0:
                    continue
                x = cx + (i - 1) * s * 3.2
                col = FAC_COL[f]
                Color(col[0], col[1], col[2], a)
                if f == 'kingdom':                     # écu
                    Quad(points=(x - s, cy + s, x + s, cy + s, x + s * .8, cy - s * .5, x, cy - s * 1.2))
                    Quad(points=(x - s * .8, cy - s * .5, x, cy - s * 1.2, x + s * .8, cy - s * .5, x, cy - s * .3))
                    Color(1, 0.85, 0.3, a)
                    Line(points=(x, cy + s * .8, x, cy - s * .8), width=3)
                    Line(points=(x - s * .5, cy + s * .2, x + s * .5, cy + s * .2), width=3)
                elif f == 'horde':                     # crâne
                    Ellipse(pos=(x - s, cy - s * .6), size=(s * 2, s * 1.8))
                    Color(0, 0, 0, a)
                    Ellipse(pos=(x - s * .6, cy + s * .1), size=(s * .45, s * .5))
                    Ellipse(pos=(x + s * .15, cy + s * .1), size=(s * .45, s * .5))
                    Triangle(points=(x - s * .2, cy - s * .1, x + s * .2, cy - s * .1, x, cy - s * .4))
                else:                                  # feuille
                    Triangle(points=(x, cy + s * 1.2, x - s, cy - s * .3, x + s, cy - s * .3))
                    Triangle(points=(x - s * .8, cy - s * .2, x + s * .8, cy - s * .2, x, cy - s * 1.1))
                    Color(0.85, 1, 0.85, a)
                    Line(points=(x, cy + s, x, cy - s * 1.1), width=2)

    def on_touch_down(self, touch):
        self.finish()
        return True

    def finish(self):
        if not self.done:
            self.done = True
            self.ev.cancel()
            self.on_done()


# ================================================================ écran de jeu
class GameView(FloatLayout):
    def __init__(self, app, g, mode, tut=None, session=None, mission=None, fac=None, **kw):
        super().__init__(**kw)
        self.app, self.g, self.mode, self.tut, self.session = app, g, mode, tut, session
        self.mission_info, self.fac, self.sig, self.last_tap = mission, fac, None, (0, 0)
        self.v = render.View()
        self.v.zoom = max(0.6, min(1.3, Window.height / 720.))
        self.box_mode, self.shown_end, self.over_t, self.centered = False, False, 0.0, False
        self.v.w, self.v.h = Window.size
        self.v.center(g, *g.focus_base())
        # --- HUD
        self.top = label('', 15, size_hint=(1, None), height=dp(34), pos_hint={'x': 0, 'top': 1}, halign='left')
        self.obj = label('', 15, size_hint=(.6, None), height=dp(30), pos_hint={'center_x': .45, 'top': .93}, color=(1, .9, .4, 1))
        self.tutl = label('', 15, size_hint=(.6, None), height=dp(64), pos_hint={'center_x': .45, 'top': .88}, color=(.8, 1, .8, 1))
        self.msg = label('', 20, size_hint=(.6, None), height=dp(40), pos_hint={'center_x': .45, 'center_y': .62}, color=(1, .6, .5, 1))
        self.wait = label('', 22, size_hint=(.8, .3), pos_hint={'center_x': .5, 'center_y': .5})
        for w in (self.top, self.obj, self.tutl, self.msg, self.wait):
            self.add_widget(w)
        col = BoxLayout(orientation='vertical', spacing=dp(4), size_hint=(None, None), width=dp(92), height=dp(8 * 44 + 7 * 4),
                        pos_hint={'right': 1, 'top': .93})
        self.b_amove = btn('Attaque', self.toggle_amove, fs=13)
        self.b_box = btn('Boîte', self.toggle_box, fs=13)
        self.b_ab = btn('Capacité', self.use_ability, fs=12)
        for b in (btn('Armée', lambda: self.g.select_army(), fs=13), btn('Inactifs', lambda: self.g.select_idle_workers(), fs=13),
                  self.b_box, self.b_amove, btn('Stop', lambda: self.g.stop_selected(), fs=13),
                  btn('Techs', self.open_techs, fs=13), self.b_ab, btn('Pause', self.toggle_pause, fs=13)):
            b.size_hint_y = None
            b.height = dp(44)
            col.add_widget(b)
        self.add_widget(col)
        zb = BoxLayout(orientation='vertical', spacing=dp(4), size_hint=(None, None), width=dp(44), height=dp(92),
                       pos_hint={'right': .88, 'y': .22})
        zb.add_widget(btn('+', lambda: self.zoom(1.15), fs=20))
        zb.add_widget(btn('−', lambda: self.zoom(1 / 1.15), fs=20))
        self.add_widget(zb)
        self.add_widget(btn('Menu', self.quit_ask, (0.5, 0.2, 0.2, 1), 12, size_hint=(None, None), size=(dp(62), dp(34)),
                            pos_hint={'right': 1, 'top': 1}))
        self.bar = BoxLayout(spacing=dp(4), size_hint=(1, None), height=dp(74), pos_hint={'x': 0, 'y': 0}, padding=dp(3))
        self.add_widget(self.bar)
        self.ev = Clock.schedule_interval(self.tick, 1 / 30.)
        self.bind(size=lambda *_: self.on_resize())

    def on_resize(self):
        self.v.w, self.v.h = self.size

    # ---- boutons
    def zoom(self, k):
        c = self.v.to_world(self.g, self.v.w / 2, self.v.h / 2)
        self.v.zoom = max(0.45, min(2.2, self.v.zoom * k))
        self.v.center(self.g, *c)

    def toggle_amove(self):
        self.g.amove = not self.g.amove

    def toggle_box(self):
        self.box_mode = not self.box_mode

    def toggle_pause(self):
        if self.mode in ('host', 'client'):
            self.g.say('Pas de pause en multijoueur')
        else:
            self.g.paused = not self.g.paused
            self.g.say('PAUSE' if self.g.paused else '')

    def use_ability(self):
        self.g.ability_cmd()

    def quit_ask(self):
        p = Popup(title='Quitter la partie ?', size_hint=(.6, .4), auto_dismiss=True)
        row = BoxLayout(spacing=dp(10), padding=dp(10))
        row.add_widget(btn('Reprendre', lambda: p.dismiss(), (0.2, 0.5, 0.3, 1)))
        row.add_widget(btn('Quitter', lambda: (p.dismiss(), self.leave()), (0.6, 0.2, 0.2, 1)))
        p.content = row
        p.open()

    def open_techs(self):
        g = self.g
        mv = ModalView(size_hint=(.9, .88), auto_dismiss=True)
        root = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(6))
        root.add_widget(label('Technologies — %s' % FACTIONS[g.fac[g.me]]['name'], 20, size_hint_y=None, height=dp(34)))
        sv = ScrollView()
        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        names = {'done': 'ACQUISE', 'busy': 'EN COURS', 'locked': 'Verrouillée', 'nobld': 'Bâtiment requis',
                 'poor': 'Ressources manquantes', 'ok': 'Rechercher'}
        cols = {'done': (0.2, 0.5, 0.25, 1), 'busy': (0.5, 0.45, 0.1, 1), 'locked': (0.25, 0.25, 0.3, 1),
                'nobld': (0.3, 0.25, 0.25, 1), 'poor': (0.4, 0.3, 0.2, 1), 'ok': (0.2, 0.4, 0.7, 1)}
        bnames = {k: v['label'] for k, v in g.bst[g.me].items()}
        for tid in TECH_ORDER:
            info = tech_info(g.fac[g.me], tid)
            st = g.tech_state(g.me, tid)
            txt = '%s\n%s\n%d B / %d M — %ds — %s\n[%s]' % (info['name'], info['desc'], info['cost'][0], info['cost'][1],
                                                         info['time'], bnames[info['b']], names[st])
            b = btn(txt, lambda t=tid: (g.research(t), mv.dismiss()), cols[st], 12, size_hint_y=None, height=dp(120))
            grid.add_widget(b)
        sv.add_widget(grid)
        root.add_widget(sv)
        root.add_widget(btn('Fermer', mv.dismiss, fs=16, size_hint_y=None, height=dp(44)))
        mv.add_widget(root)
        mv.open()

    # ---- boucle
    def tick(self, dt):
        dt = min(dt, 0.05)
        g, s = self.g, self.session
        waiting = ''
        if self.mode == 'host':
            if s.err:
                waiting = s.err
            elif not s.connected:
                waiting = "En attente du 2e joueur…\nVotre IP : %s\n(même Wi-Fi, port %d)" % (net.local_ip(), net.PORT)
            else:
                g.update(dt)
                if not s.tick(dt) and not g.over:
                    g.set_winner(g.me, "L'adversaire a quitté la partie.")
        elif self.mode == 'client':
            ok = s.tick(dt)
            if not s.ready:
                waiting = 'Connexion à la partie…'
            else:
                if not self.centered:
                    self.centered = True
                    self.v.center(g, *g.focus_base())
                g.update(dt)
            if not ok and not g.over:
                g.set_winner(1 - g.me, 'Connexion perdue.')
        elif not g.paused and not g.over:
            g.update(dt)
        if self.tut and not g.over:
            self.tut.update()
        g.events.clear()
        self.wait.text = waiting
        self.refresh_hud()
        if self.mode == 'client' and not s.ready:
            return
        self.draw()
        if g.over and not self.shown_end:
            self.over_t += dt
            if self.over_t > 1.2:
                self.shown_end = True
                self.end_popup()

    def refresh_hud(self):
        g = self.g
        me = g.me
        st = g.stock[me]
        t = int(g.time)
        self.top.text = '  %s    Bois %d   Minerai %d   Pop %d/%d   %d:%02d' % (
            FACTIONS[g.fac[me]]['short'], st['wood'], st['ore'], g.pop(me), POP_MAX, t // 60, t % 60)
        self.obj.text = g.objective_text()
        self.tutl.text = self.tut.text() if self.tut else ''
        self.tutl.color = (1, 1, .4, 1) if g.step_flash > 0 else (.8, 1, .8, 1)
        self.msg.text = g.msg if g.msg_t > 0 or g.paused else ''
        ab = ABILITY[g.fac[me]]
        if g.ab_t[me] > 0:
            self.b_ab.text, self.b_ab.background_color = '%s\nactif %ds' % (ab['name'], g.ab_t[me]), (0.8, 0.6, 0.1, 1)
        elif g.ab_cd[me] > 0:
            self.b_ab.text, self.b_ab.background_color = '%s\n%ds' % (ab['name'], g.ab_cd[me]), (0.3, 0.3, 0.35, 1)
        else:
            self.b_ab.text, self.b_ab.background_color = '%s\nPRÊTE' % ab['name'], (0.2, 0.6, 0.3, 1)
        self.b_amove.background_color = (0.8, 0.3, 0.2, 1) if g.amove else (0.2, 0.28, 0.4, 1)
        self.b_box.background_color = (0.8, 0.6, 0.2, 1) if self.box_mode else (0.2, 0.28, 0.4, 1)
        self.update_bar()

    def update_bar(self):
        g = self.g
        acts = [] if g.placing else g.actions()
        sel = [e for e in g.sel if e.team == g.me or len(g.sel) == 1]
        q = sum(len(e.queue) for e in sel if e.b)
        sig = (tuple(e.id for e in sel), tuple((a['kind'], a['ok']) for a in acts), q, g.placing,
               tuple(int(e.hp / max(1, e.maxhp) * 10) for e in sel[:3]), len(g.sel))
        if sig == self.sig:
            return
        self.sig = sig
        self.bar.clear_widgets()
        self.bar.add_widget(label(self.sel_text(sel), 13, size_hint_x=None, width=dp(170)))
        if g.placing:
            self.bar.add_widget(label('Glissez puis relâchez\npour construire', 15))
            self.bar.add_widget(btn('Annuler', lambda: setattr(g, 'placing', None), (0.6, 0.2, 0.2, 1), size_hint_x=None, width=dp(100)))
            return
        for a in acts:
            c = a['d'].get('cost', (0, 0))
            txt = a['d']['label'] + ('\n%dB %dM' % (c[0], c[1]) if a['kind'] != 'cancel' else '')
            col = (0.2, 0.45, 0.3, 1) if a['ok'] else (0.3, 0.3, 0.33, 1)
            if a['kind'] == 'cancel':
                col = (0.6, 0.25, 0.2, 1)
            b = btn(txt, a['fn'], col, 12, size_hint_x=None, width=dp(96))
            self.bar.add_widget(b)
        self.bar.add_widget(Widget())

    def sel_text(self, sel):
        g = self.g
        if not sel:
            return 'Touchez une unité ou un bâtiment'
        if len(sel) == 1:
            e = sel[0]
            who = 'Ennemi — ' if e.team != g.me else ''
            extra = ''
            if e.b and e.queue:
                extra = '\nFile : ' + ', '.join(g.ust[e.team][k]['label'] for k in e.queue[:3])
            elif not e.b and e.kind == 'worker' and e.carry:
                extra = '\nPorte %d' % e.carry
            return '%s%s\nPV %d/%d%s' % (who, e.d['label'], e.hp, e.maxhp, extra)
        cnt = {}
        for e in sel:
            cnt[e.d['label']] = cnt.get(e.d['label'], 0) + 1
        return '\n'.join('%d × %s' % (n, k) for k, n in list(cnt.items())[:4])

    def draw(self):
        g, v = self.g, self.v
        v.clamp(g)
        self.canvas.before.clear()
        with self.canvas.before:
            render.draw_world(v, g)
            render.draw_minimap(v, g, *self.minimap())
        if g.step_flash > 0:
            pass

    def minimap(self):
        w = dp(150)
        return dp(6), self.height - dp(40) - w * 2 / 3 - dp(4), w, w * 2 / 3

    # ---- tactile
    def on_touch_down(self, touch):
        if super().on_touch_down(touch):
            return True
        if not self.collide_point(*touch.pos) or not self.session_ready():
            return False
        x, y, w, h = self.minimap()
        if x <= touch.x <= x + w and y <= touch.y <= y + h:
            touch.ud['mm'] = True
            self.mm_move(touch)
            touch.grab(self)
            return True
        touch.ud.update(start=touch.pos, moved=False)
        touch.grab(self)
        if self.g.placing:
            self.v.ghost = self.v.to_world(self.g, *touch.pos)
        return True

    def session_ready(self):
        return not (self.mode == 'client' and not self.session.ready)

    def mm_move(self, touch):
        x, y, w, h = self.minimap()
        from game import MAP_W, MAP_H
        wx, wy = (touch.x - x) / w * MAP_W, (1 - (touch.y - y) / h) * MAP_H
        self.v.center(self.g, wx, wy)

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_move(touch)
        g, v = self.g, self.v
        if touch.ud.get('mm'):
            self.mm_move(touch)
            return True
        sx, sy = touch.ud['start']
        if math.hypot(touch.x - sx, touch.y - sy) > dp(10):
            touch.ud['moved'] = True
        if not touch.ud['moved']:
            return True
        if g.placing:
            v.ghost = v.to_world(g, touch.x, touch.y)
        elif self.box_mode:
            g.drag = (sx, sy, touch.x, touch.y)
        else:
            lx, ly = touch.ud.get('last', touch.ud['start'])
            g.cam[0] -= (touch.x - lx) / v.zoom
            g.cam[1] += (touch.y - ly) / v.zoom
            v.clamp(g)
        touch.ud['last'] = touch.pos
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_up(touch)
        touch.ungrab(self)
        g, v = self.g, self.v
        if touch.ud.get('mm'):
            return True
        if g.placing:
            wx, wy = v.to_world(g, touch.x, touch.y)
            if g.build_with_selected(g.placing, wx, wy):
                g.placing = None
            else:
                g.say('Emplacement invalide (près de vos bâtiments, terrain libre)')
            return True
        if g.drag:
            x0, y0, x1, y1 = g.drag
            g.drag = None
            a, b = v.to_world(g, x0, y0), v.to_world(g, x1, y1)
            g.select_rect(a[0], a[1], b[0], b[1])
            self.box_mode = False
            return True
        if not touch.ud.get('moved'):
            self.tap(touch.x, touch.y)
        return True

    def tap(self, sx, sy):
        g, v = self.g, self.v
        wx, wy = v.to_world(g, sx, sy)
        e = g.pick(wx, wy)
        now = time.time()
        double = now - self.last_tap[0] < 0.4
        self.last_tap = (now, 0)
        own_units = [s for s in g.sel if s.team == g.me and not s.b]
        own_prod = [s for s in g.sel if s.team == g.me and s.b and s.d['makes']]
        if e is not None and e.team == g.me:
            if e in g.sel and e.b and len(g.sel) == 1:
                g.sel = []
            elif double and not e.b:      # double tap : tous les mêmes à l'écran
                x0, y0 = v.to_world(g, 0, v.h)
                x1, y1 = v.to_world(g, v.w, 0)
                g.select_kind(e.kind, x0, y0, x1, y1)
            else:
                g.sel = [e]
        elif own_units or own_prod:
            g.command(wx, wy)
        elif e is not None:
            g.sel = [e]
        else:
            g.sel = []

    # ---- fin de partie
    def end_popup(self):
        g = self.g
        win = g.winner == g.me
        p = Popup(title=g.over, size_hint=(.7, .55), auto_dismiss=False)
        box = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        box.add_widget(label(g.reason or '', 20))
        row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(56))
        mi = self.mission_info
        if mi and win:
            self.app.complete_mission(self.fac, mi['id'])
            if mi['id'] < len(campaign.missions(self.fac)):
                row.add_widget(btn('Mission suivante', lambda: (p.dismiss(), self.leave(False), self.app.start_mission(self.fac, mi['id'] + 1)), (0.2, 0.5, 0.3, 1)))
        elif mi:
            row.add_widget(btn('Rejouer', lambda: (p.dismiss(), self.leave(False), self.app.start_mission(self.fac, mi['id'])), (0.5, 0.4, 0.15, 1)))
        row.add_widget(btn('Menu', lambda: (p.dismiss(), self.leave()), (0.3, 0.3, 0.5, 1)))
        box.add_widget(row)
        p.content = box
        p.open()

    def leave(self, menu=True):
        self.ev.cancel()
        if self.session:
            self.session.close()
        if menu:
            self.app.show_menu()


# ================================================================ application
class RTSApp(App):
    def build(self):
        Window.clearcolor = BG
        self.root_w = FloatLayout()
        self.prog = campaign.load_progress(self.user_data_dir)
        Window.bind(on_keyboard=self.on_key)
        Clock.schedule_once(lambda dt: self.show(Intro(self.show_menu)), 0)
        return self.root_w

    def show(self, w):
        self.root_w.clear_widgets()
        self.root_w.add_widget(w)
        self.cur = w

    def on_key(self, win, key, *a):
        if key == 27:
            if isinstance(self.cur, GameView):
                self.cur.quit_ask()
            elif getattr(self, 'is_menu', False):
                return False
            else:
                self.show_menu()
            return True
        return False

    def page(self, title, widgets, back=True):
        self.is_menu = False
        root = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        root.add_widget(label(title, 30, size_hint_y=None, height=dp(56), bold=True, color=(1, .9, .5, 1)))
        for w in widgets:
            root.add_widget(w)
        if back:
            root.add_widget(btn('← Retour', self.show_menu, (0.3, 0.3, 0.35, 1), size_hint_y=None, height=dp(48)))
        self.show(root)
        return root

    def show_menu(self):
        def row(text, cb, col=(0.2, 0.3, 0.5, 1)):
            return btn(text, cb, col, 22, size_hint_y=None, height=dp(58))
        self.page('MINI RTS', [row('Escarmouche', self.show_skirmish, (0.2, 0.45, 0.3, 1)), row('Campagne', self.show_campaign),
                               row('Tutoriel', self.show_tutorial), row('Multijoueur (Wi-Fi)', self.show_mp),
                               row('Quitter', self.stop, (0.5, 0.2, 0.2, 1)), Widget()], back=False)
        self.is_menu = True

    # ---- escarmouche
    def show_skirmish(self):
        me = Chooser(fac_options(), 'kingdom')
        foe = Chooser(fac_options(), 'horde')
        dif = Chooser([(i, n, c) for i, (n, c) in enumerate(zip(DIFF_NAMES, [(0.2, 0.5, 0.3, 1), (0.6, 0.5, 0.15, 1), (0.6, 0.2, 0.2, 1)]))], 1)
        info = label('', 14, size_hint_y=None, height=dp(60))

        def upd(*_):
            info.text = FACTIONS[me.value]['trait']
        for b in me.bs.values():
            b.bind(on_release=upd)
        upd()
        self.page('Escarmouche', [label('Votre faction', 16, size_hint_y=None, height=dp(24)), me, info,
                                  label('Faction ennemie', 16, size_hint_y=None, height=dp(24)), foe,
                                  label('Difficulté', 16, size_hint_y=None, height=dp(24)), dif,
                                  btn('Lancer la partie', lambda: self.start_skirmish(me.value, foe.value, dif.value), (0.2, 0.5, 0.3, 1), 22,
                                      size_hint_y=None, height=dp(60)), Widget()])

    def new_game(self, f0, f1, diff, setup=None, **kw):
        g = Game()
        g.diff = diff
        g.reset(f0, f1, setup=setup, **kw)
        return g

    def start_skirmish(self, f0, f1, diff):
        g = self.new_game(f0, f1, diff)
        self.show(GameView(self, g, 'skirmish'))

    # ---- tutoriel
    def show_tutorial(self):
        ch = Chooser(fac_options(), 'kingdom')
        self.page('Tutoriel', [label('Apprenez à jouer avec la faction de votre choix : économie, armée, recherches et capacité.', 16),
                               ch, btn('Commencer', lambda: self.start_tutorial(ch.value), (0.2, 0.5, 0.3, 1), 22, size_hint_y=None, height=dp(60)), Widget()])

    def start_tutorial(self, fac):
        g = self.new_game(fac, campaign.ENEMY[fac], 0, setup=campaign.tutorial_setup())
        self.show(GameView(self, g, 'tuto', tut=campaign.Tutorial(g)))

    # ---- campagne
    def show_campaign(self):
        ch = [btn('%s\n%s' % (FACTIONS[f]['name'], campaign.STORY[f][0]), lambda f=f: self.show_missions(f), FAC_COL[f], 18,
                  size_hint_y=None, height=dp(84)) for f in FAC_ORDER]
        self.page('Campagne', ch + [Widget()])

    def show_missions(self, fac):
        done = campaign.unlocked(self.prog, fac)
        ms = campaign.missions(fac)
        ws = [label(campaign.STORY[fac][1], 14, size_hint_y=None, height=dp(66))]
        for m in ms:
            open_ = m['id'] <= done + 1
            txt = '%d. %s  -  %s%s' % (m['id'], m['name'], DIFF_NAMES[m['diff']], '   [OK]' if m['id'] <= done else '')
            ws.append(btn(txt if open_ else '%d. (verrouillée)' % m['id'],
                          (lambda m=m: self.brief(fac, m)) if open_ else (lambda: None),
                          FAC_COL[fac] if open_ else (0.25, 0.25, 0.28, 1), 17, size_hint_y=None, height=dp(52)))
        ws.append(Widget())
        root = self.page(FACTIONS[fac]['name'], ws, back=False)
        root.add_widget(btn('← Retour', self.show_campaign, (0.3, 0.3, 0.35, 1), size_hint_y=None, height=dp(48)))

    def brief(self, fac, m):
        p = Popup(title='Mission %d — %s' % (m['id'], m['name']), size_hint=(.8, .6))
        box = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        box.add_widget(label(m['brief'] + '\n\nEnnemi : %s' % FACTIONS[m['enemy']]['name'], 17))
        row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(54))
        row.add_widget(btn('Annuler', p.dismiss, (0.4, 0.4, 0.45, 1)))
        row.add_widget(btn('Commencer', lambda: (p.dismiss(), self.start_mission(fac, m['id'])), (0.2, 0.5, 0.3, 1)))
        box.add_widget(row)
        p.content = box
        p.open()

    def start_mission(self, fac, mid):
        m = campaign.missions(fac)[mid - 1]
        g = self.new_game(fac, m['enemy'], m['diff'], setup=m['setup'], seed=mid * 17 + 3)
        self.show(GameView(self, g, 'camp', mission=m, fac=fac))

    def complete_mission(self, fac, mid):
        if mid > self.prog.get(fac, 0):
            self.prog[fac] = mid
            campaign.save_progress(self.user_data_dir, self.prog)

    # ---- multijoueur
    def show_mp(self):
        me = Chooser(fac_options(), 'kingdom')
        foe = Chooser(fac_options(), 'horde')
        ip = TextInput(hint_text='IP de l\'hôte (ex. 192.168.1.20)', multiline=False, size_hint_y=None, height=dp(48), font_size=sp(18))
        err = label('', 14, size_hint_y=None, height=dp(30), color=(1, .5, .4, 1))

        def join():
            g = Game()
            s = net.ClientSession(g)
            if s.connect(ip.text):
                self.show(GameView(self, g, 'client', session=s))
            else:
                err.text = 'Connexion impossible : %s' % s.err

        def host():
            g = self.new_game(me.value, foe.value, 1, me=0, ai_teams=())
            g.record_fx = True
            self.show(GameView(self, g, 'host', session=net.HostSession(g)))
        self.page('Multijoueur', [label('Héberger : choisissez votre faction (haut) et celle de l\'adversaire (bas)', 15, size_hint_y=None, height=dp(40)),
                                  me, foe, btn('Héberger une partie', host, (0.2, 0.5, 0.3, 1), 20, size_hint_y=None, height=dp(54)),
                                  label('— ou —', 14, size_hint_y=None, height=dp(22)), ip,
                                  btn('Rejoindre', join, (0.2, 0.35, 0.6, 1), 20, size_hint_y=None, height=dp(54)), err, Widget()])


if __name__ == '__main__':
    RTSApp().run()
