"""MINI RTS v6 - application Kivy (Android) : intro, menus, escarmouche, campagne, tutoriel, multijoueur."""
import math
import os
import time
import traceback

from kivy.app import App
from kivy.base import ExceptionHandler, ExceptionManager
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

IMPORT_ERR = None
try:
    import game_ext  # noqa: F401  (installe techs, capacités, soigneurs : à importer avant Game)
    import campaign
    import net
    import render
    from game import Game, FACTIONS, ABILITY, TECH_ORDER, tech_info, DIFF_NAMES, POP_MAX
except Exception:  # on affiche l'erreur à l'écran au lieu de fermer l'app
    IMPORT_ERR = traceback.format_exc()

FAC_ORDER = ['kingdom', 'horde', 'sylvan']
FAC_COL = {'kingdom': (0.2, 0.35, 0.8, 1), 'horde': (0.7, 0.2, 0.15, 1), 'sylvan': (0.2, 0.55, 0.3, 1)}
BG = (0.07, 0.09, 0.12, 1)

