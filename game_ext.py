"""Extensions de game.py : recherches (techs), capacités de faction, soigneurs,
régénération, bâtiments avancés et IA de recherche.
Importer ce module AVANT de créer Game() : il se branche tout seul (install())."""
import math
import random

import game
from game import Game, TECH_ORDER, ABILITY, MIL, BUILD_REQ, tech_info, dist

# multiplicateurs de la capacité de faction pendant qu'elle est active
AB_FX = {
    'kingdom': dict(dmg=1.3, atk=1.0, spd=1.15),
    'horde': dict(dmg=1.0, atk=1.5, spd=1.2),
    'sylvan': dict(dmg=1.0, atk=1.0, spd=1.0),
}


# ---------------------------------------------------------------- technologies
def tech_state(self, team, tid):
    """'done' | 'busy' | 'locked' | 'nobld' | 'poor' | 'ok'"""
    if tid in self.techs[team]:
        return 'done'
    if any(r[0] == tid for r in self.rsch[team].values()):
        return 'busy'
    info = tech_info(self.fac[team], tid)
    if any(r not in self.techs[team] for r in info['req']):
        return 'locked'
    if self.research_building(team, info['b']) is None:
        return 'nobld'
    return 'ok' if self.affordable(team, info['cost']) else 'poor'


def research_building(self, team, kind):
    for e in self.ents:
        if e.team == team and e.b and e.built and not e.dead and e.kind == kind and e.id not in self.rsch[team]:
            return e
    return None


def start_research(self, team, tid):
    if tid not in game.TECHS or self.tech_state(team, tid) != 'ok':
        return False
    info = tech_info(self.fac[team], tid)
    b = self.research_building(team, info['b'])
    st = self.stock[team]
    st['wood'] -= info['cost'][0]
    st['ore'] -= info['cost'][1]
    self.rsch[team][b.id] = [tid, float(info['time'])]
    return True


def apply_tech(self, team, tid):
    if tid in self.techs[team]:
        return
    self.techs[team].add(tid)
    for fx in tech_info(self.fac[team], tid)['fx']:
        if fx[0] == 'gather':
            self.gmult[team] += fx[1]
        elif fx[0] == 'ab_cd':
            self.abmult[team] = max(0.4, self.abmult[team] - fx[1])
        elif fx[0] == 'bhp':
            for d in self.bst[team].values():
                d['hp'] = int(d['hp'] * (1 + fx[1]))
            for e in self.ents:
                if e.team == team and e.b and e.maxhp:
                    old = e.maxhp
                    e.maxhp = e.d['hp']
                    e.hp = min(e.maxhp, e.hp * e.maxhp / old)
        elif fx[0] == 'u':
            _, kinds, stat, val = fx
            for k in (MIL if kinds == 'mil' else kinds):
                d = self.ust[team][k]
                if stat == 'hp%':
                    d['hp'] = int(d['hp'] * (1 + val))
                    for e in self.ents:
                        if e.team == team and e.kind == k and not e.b:
                            old = e.maxhp
                            e.maxhp = d['hp']
                            e.hp = min(e.maxhp, e.hp * e.maxhp / old)
                elif stat == 'speed%':
                    d['speed'] *= (1 + val)
                else:
                    d[stat] = d.get(stat, 0) + val


def research(self, tid):
    """Commande du joueur local (passe par le réseau si besoin)."""
    if self.tech_state(self.me, tid) in ('ok',) or self.remote:
        self.cmd(dict(k='tech', id=tid))
    else:
        self.say({'poor': 'Ressources insuffisantes', 'locked': 'Recherche préalable requise',
                  'nobld': 'Bâtiment de recherche manquant ou occupé', 'busy': 'Déjà en cours',
                  'done': 'Déjà acquise'}.get(self.tech_state(self.me, tid), ''))


# ---------------------------------------------------------------- capacité de faction
def ab_factor(self, team):
    if self.ab_t[team] > 0:
        return AB_FX[self.fac[team]]
    return None


def use_ability(self, team):
    if self.ab_cd[team] > 0 or self.ab_t[team] > 0:
        return False
    ab = ABILITY[self.fac[team]]
    self.ab_t[team] = float(ab['dur'])
    self.ab_cd[team] = ab['cd'] * self.abmult[team]
    if self.fac[team] == 'sylvan':
        for e in self.ents:
            if e.team == team and not e.b and not e.dead:
                e.hp = min(e.maxhp, e.hp + 0.45 * e.maxhp)
                self.puff(e.x, e.y, (0.4, 1, 0.5), 5, 40, 0.8, 3)
    else:
        for e in self.mil(team):
            self.puff(e.x, e.y, (1, 0.85, 0.3) if self.fac[team] == 'kingdom' else (1, 0.2, 0.2), 4, 50, 0.6, 3)
    self.events.append(('ability', 0, 0, team))
    return True


def ability_cmd(self):
    if self.ab_cd[self.me] > 0:
        self.say('Capacité en recharge (%d s)' % self.ab_cd[self.me])
    else:
        self.cmd(dict(k='ability'))


# ---------------------------------------------------------------- soigneurs
def upd_healer(self, u, dt):
    u.cd = max(0, u.cd - dt)
    u.flash = max(0, u.flash - dt)
    u.moving = u.working = False
    if u.mode in ('move', 'amove'):
        self.go(u, dt)
    elif u.mode != 'idle':
        u.mode, u.target = 'idle', None
    rng, heal = u.d['rng'], u.d.get('heal', 6)
    best, bd = None, 1e9
    for e in self.ents:
        if e.team == u.team and not e.b and not e.dead and e is not u and e.hp < e.maxhp - 0.5:
            d = dist(u.x, u.y, e.x, e.y)
            if d < bd:
                best, bd = e, d
    if best is None:
        return
    if bd <= rng:
        best.hp = min(best.maxhp, best.hp + heal * dt)
        u.working = True
        u.ang = math.atan2(best.y - u.y, best.x - u.x)
        if u.cd <= 0:
            u.cd = 0.7
            self.puff(best.x, best.y - 8, (0.5, 1, 0.6), 2, 25, 0.5, 3)
            if self.record_fx and len(self.fx_out) < 60:
                self.fx_out.append(['a', round(u.x), round(u.y), round(best.x), round(best.y), 'orb'])
            self.fx.append(dict(t='a', x=u.x, y=u.y, x1=best.x, y1=best.y, life=0.2, max=0.2, p='orb'))
    elif u.mode == 'idle' and bd < 320:
        self.step(u, best.x, best.y, dt, stop=rng * 0.7)


# ---------------------------------------------------------------- bâtiments avancés
def adv_actions(self):
    out = _actions(self)
    me = self.me
    if any(e.kind == 'worker' and e.team == me for e in self.sel):
        cancel = [a for a in out if a['kind'] == 'cancel']
        out = [a for a in out if a['kind'] != 'cancel']
        for k in ('forge', 'temple', 'sanctum'):
            if self.req_ok(me, k):
                d = self.bst[me][k]
                out.append(dict(kind=k, d=d, fn=lambda k=k: self.start_place(k), ok=self.affordable(me, d['cost'])))
        out += cancel
    return out


def req_ok(self, team, kind):
    return all(any(e.team == team and e.kind == r and e.b and e.built and not e.dead for e in self.ents)
               for r in BUILD_REQ.get(kind, []))


def can_place(self, team, kind, x, y):
    return self.req_ok(team, kind) and _can_place(self, team, kind, x, y)


# ---------------------------------------------------------------- enveloppes du moteur
def reset(self, *a, **k):
    _reset(self, *a, **k)
    self.rsch = {0: {}, 1: {}}
    self.ai_rt = {0: 0.0, 1: 0.0}
    self.ai_save = {0: None, 1: None}


def strike(self, a, t):
    f = None if a.b else self.ab_factor(a.team)
    was = t.dead
    if f:
        d = a.d
        sd, sc = d['dmg'], d['cd']
        d['dmg'], d['cd'] = sd * f['dmg'], sc / f['atk']
        try:
            _strike(self, a, t)
        finally:
            d['dmg'], d['cd'] = sd, sc
    else:
        _strike(self, a, t)
    if t.dead and not was and not t.b:
        self.kills[a.team] += 1


def step(self, u, tx, ty, dt, stop=0):
    f = None if u.b else self.ab_factor(u.team)
    if f and f['spd'] != 1:
        d = u.d
        s = d['speed']
        d['speed'] = s * f['spd']
        try:
            return _step(self, u, tx, ty, dt, stop)
        finally:
            d['speed'] = s
    return _step(self, u, tx, ty, dt, stop)


def upd_unit(self, u, dt):
    if u.kind == 'healer':
        self.upd_healer(u, dt)
        return
    _upd_unit(self, u, dt)
    rg = u.d.get('regen', 0)
    if self.fac[u.team] == 'sylvan' and self.ab_t[u.team] > 0:
        rg += 0.04 * u.maxhp
    if rg and u.hp < u.maxhp:
        u.hp = min(u.maxhp, u.hp + rg * dt)


def harvest(self, u, dt):
    ct = u.ctype
    before = self.stock[u.team].get(ct, 0) if ct else 0
    _harvest(self, u, dt)
    if ct and self.gmult[u.team] != 1.0:
        delta = self.stock[u.team][ct] - before
        if delta > 0:
            extra = int(round(delta * (self.gmult[u.team] - 1.0)))
            self.stock[u.team][ct] += extra
            self.gathered[u.team] += extra


def queue(self, b, kind):
    sv = self.ai_save.get(b.team) if b.team in self.ai_teams else None
    if sv and kind != 'worker':
        c = self.ust[b.team][kind]['cost']
        st = self.stock[b.team]
        if st['wood'] < c[0] + sv[0] or st['ore'] < c[1] + sv[1]:
            return False
    return _queue(self, b, kind)


def exec_cmd(self, team, c):
    k = c.get('k')
    if k == 'tech':
        self.start_research(team, c.get('id'))
    elif k == 'ability':
        self.use_ability(team)
    else:
        _exec_cmd(self, team, c)


def update(self, dt):
    if not self.remote:
        for t in (0, 1):
            self.ab_cd[t] = max(0.0, self.ab_cd[t] - dt)
            self.ab_t[t] = max(0.0, self.ab_t[t] - dt)
            for bid in list(self.rsch[t]):
                b = self.by_id.get(bid)
                if b is None or b.dead:
                    info = tech_info(self.fac[t], self.rsch[t][bid][0])
                    self.stock[t]['wood'] += info['cost'][0]
                    self.stock[t]['ore'] += info['cost'][1]
                    del self.rsch[t][bid]
                    continue
                self.rsch[t][bid][1] -= dt
                if self.rsch[t][bid][1] <= 0:
                    tid = self.rsch[t].pop(bid)[0]
                    self.apply_tech(t, tid)
                    self.events.append(('research', 0, 0, t))
        self.ai_extras(dt)
    _update(self, dt)


def ai_extras(self, dt):
    for t in self.ai_teams:
        self.ai_rt[t] += dt
        if self.ai_rt[t] < 8:
            continue
        self.ai_rt[t] = 0.0
        mine = [e for e in self.ents if e.team == t and not e.dead]
        hq = next((e for e in mine if e.kind == 'hq'), None)
        if not hq:
            continue
        army = [e for e in mine if not e.b and e.kind != 'worker']
        workers = [e for e in mine if e.kind == 'worker']
        have = {e.kind for e in mine if e.b and e.built}
        for kind, need, wood in (('forge', 'barracks', 280), ('temple', 'barracks', 400), ('sanctum', 'forge', 500)):
            if (kind not in {e.kind for e in mine if e.b} and need in have and len(army) >= 9
                    and self.stock[t]['wood'] >= wood and workers and all(e.built for e in mine if e.b)):
                self.ai_build(t, hq, kind, workers)
                break
        if self.time < (150, 100, 60)[self.diff]:
            continue
        opts = [tid for tid in TECH_ORDER if self.tech_state(t, tid) in ('ok', 'poor')]
        self.ai_save[t] = None
        if opts and len(army) >= 4:
            tid = min(opts, key=lambda i: sum(tech_info(self.fac[t], i)['cost']))
            if self.tech_state(t, tid) == 'ok':
                self.start_research(t, tid)
            else:
                self.ai_save[t] = tech_info(self.fac[t], tid)['cost']  # l'IA met de côté pour cette recherche
        if (self.ab_cd[t] <= 0 and len(army) >= 8
                and any(e.team != t and not e.b and dist(e.x, e.y, a.x, a.y) < 260 for a in army[:6] for e in self.ents)):
            self.use_ability(t)


# ---------------------------------------------------------------- installation
_reset, _strike, _step, _upd_unit = Game.reset, Game.strike, Game.step, Game.upd_unit
_harvest, _exec_cmd, _update = Game.harvest, Game.exec_cmd, Game.update
_actions, _can_place, _queue = Game.actions, Game.can_place, Game.queue


def install():
    if getattr(Game, '_ext_installed', False):
        return
    for fn in (tech_state, research_building, start_research, apply_tech, research, ab_factor, use_ability,
               ability_cmd, upd_healer, req_ok, ai_extras):
        setattr(Game, fn.__name__, fn)
    Game.reset, Game.strike, Game.step, Game.upd_unit = reset, strike, step, upd_unit
    Game.harvest, Game.exec_cmd, Game.update = harvest, exec_cmd, update
    Game.actions, Game.can_place, Game.queue = adv_actions, can_place, queue
    Game._ext_installed = True


install()
