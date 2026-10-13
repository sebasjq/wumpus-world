'Aplicación y navegación de la interfaz Pygame.'

import json
import math
import os

import pygame

from logic.game import Game

from .audio import SoundManager
from .rendering import *
from .widgets import Button, chip, keycap


class App:
    """Controla navegación, renderizado e integración incremental con ``Game``."""

    HELP_PAGES = ["Tu misión", "Peligros", "Percepciones", "Controles", "Modalidades"]

    def __init__(self):
        # SDL usa este filtro al ampliar la superficie lógica de SCALED.
        # Debe configurarse antes de inicializar Pygame para que el renderer
        # de la ventana lo tome en cuenta.
        os.environ["SDL_RENDER_SCALE_QUALITY"] = "2"
        pygame.init()
        pygame.display.set_caption("Wumpus World", "Wumpus World")
        flags = pygame.SCALED | pygame.RESIZABLE
        try:
            self.screen = pygame.display.set_mode((W, H), flags, vsync=1)
        except (TypeError, pygame.error):
            # Algunas versiones/ventanas de Pygame no admiten vsync con
            # SCALED; se conserva el renderizado suavizado como fallback.
            self.screen = pygame.display.set_mode((W, H), flags)
        window_icon = logo(64, 64)
        if window_icon:
            pygame.display.set_icon(window_icon)
        self.clock = pygame.time.Clock()
        self.settings = self.load_settings()
        self.audio = SoundManager(self.settings["music"], self.settings["effects"])
        self.audio.play_music("pregame")
        if self.settings["fullscreen"]:
            self.apply_fullscreen()
        self.t = 0.0
        self.fade = 1.0
        self.mouse = (0, 0)
        self.state = "menu"
        self.mode = None
        self.map_index = 0
        self.game = None
        self.paused = False
        self.finished = False
        self.result_hidden = False
        self.auto_agent = True
        self.agent_timer = 0.0
        self.help_page = 0
        self.settings_from = "menu"
        self.settings_scroll = 0
        self.settings_max_scroll = 200
        self.error = ""
        self.message = "Explora la cueva y encuentra todo el oro."
        self.notes = {}
        self.max_arrows = 1
        self.max_lives = 0
        self.vis_pos = None
        self.hand_cursor = False
        self.buttons = []

    # ----------------------------------------------------------- ajustes --
    @staticmethod
    def load_settings():
        data = dict(DEFAULT_SETTINGS)
        try:
            data.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
        data["speed"] = max(0, min(len(SPEEDS) - 1, int(data.get("speed", 1))))
        if "sound" in data:
            data.setdefault("music", data["sound"])
            data.setdefault("effects", data["sound"])
        data["music"] = bool(data.get("music", True))
        data["effects"] = bool(data.get("effects", True))
        return data

    def save_settings(self):
        try:
            SETTINGS_FILE.write_text(json.dumps(self.settings, indent=2), encoding="utf-8")
        except OSError:
            pass

    def apply_fullscreen(self):
        try:
            if bool(pygame.display.get_surface().get_flags() & pygame.FULLSCREEN) != \
                    self.settings["fullscreen"]:
                pygame.display.toggle_fullscreen()
        except pygame.error:
            pass

    def toggle_setting(self, key):
        self.settings[key] = not self.settings[key]
        if key == "music":
            self.audio.set_music_enabled(self.settings[key])
        elif key == "effects":
            self.audio.set_effects_enabled(self.settings[key])
            if self.settings[key]:
                self.audio.play("click")
        if key == "fullscreen":
            self.apply_fullscreen()
        self.save_settings()

    def set_speed(self, index):
        self.settings["speed"] = max(0, min(len(SPEEDS) - 1, index))
        self.save_settings()

    # -------------------------------------------------------- navegación --
    def set_state(self, state):
        self.state = state
        self.buttons = []
        self.fade = 1.0
        self.error = ""

    def go_menu(self):
        self.paused = False
        self.finished = False
        self.audio.play_music("pregame")
        self.set_state("menu")

    def show_help(self):
        self.help_page = 0
        self.set_state("help")

    def show_settings(self, origin):
        self.settings_from = origin
        self.settings_scroll = 0
        self.set_state("settings")

    def back_from_settings(self):
        self.set_state(self.settings_from)

    def back(self):
        """Acción de la tecla ESC en las pantallas de menú."""
        target = {"mode": "menu", "maps": "mode", "setup": "maps", "help": "menu"}
        if self.state in target:
            self.set_state(target[self.state])
        elif self.state == "settings":
            self.back_from_settings()

    # ------------------------------------------------------ bucle y juego --
    def run(self):
        """Ejecuta el bucle principal hasta que el usuario cierre la ventana."""
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            self.t += dt
            self.fade = max(0.0, self.fade - dt * 4.5)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    self.key(event)
                elif event.type == pygame.MOUSEWHEEL and self.state == "settings":
                    self.settings_scroll = max(0, min(self.settings_max_scroll,
                                                      self.settings_scroll - event.y * 38))
                elif event.type == pygame.MOUSEBUTTONUP:
                    for button in list(self.buttons):
                        if button.click(event):
                            self.audio.play("click")
                            break
            self.update(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()

    def update(self, dt):
        """Avanza al agente con un temporizador (sin bloquear el bucle)."""
        self.audio.update()
        if (self.state == "game" and self.mode == "agent" and self.auto_agent
                and not self.paused and not self.finished and self.game):
            self.agent_timer += dt
            if self.agent_timer >= SPEEDS[self.settings["speed"]][1] / 1000.0:
                self.agent_timer = 0.0
                self.agent_step()

    def key(self, event):
        if event.key == pygame.K_ESCAPE:
            if self.state == "game":
                if not self.finished:
                    self.paused = not self.paused
            else:
                self.back()
            return
        if self.state != "game" or self.paused or self.finished:
            return
        if self.mode == "manual":
            actions = {pygame.K_LEFT: "TURN_LEFT", pygame.K_RIGHT: "TURN_RIGHT",
                       pygame.K_UP: "FORWARD", pygame.K_g: "GRAB",
                       pygame.K_SPACE: "SHOOT", pygame.K_c: "CLIMB"}
            if event.key in actions:
                self.perform(actions[event.key])
        elif self.mode == "agent":
            if event.key == pygame.K_SPACE:
                self.auto_agent = not self.auto_agent
            elif event.key == pygame.K_n:
                self.agent_step()

    def perform(self, action):
        if self.game and not self.paused and not self.finished:
            self.event_message(self.game.act(action))

    def agent_step(self):
        if self.mode == "agent" and self.game and not self.paused and not self.finished:
            self.event_message(self.game.step())

    def toggle_risk(self):
        if self.mode == "agent" and self.game and not self.finished:
            self.game.set_risk(not self.game.agent.allow_risk)
            self.message = (
                "Riesgo activado: el agente puede explorar casillas inciertas."
                if self.game.agent.allow_risk
                else "Riesgo desactivado: el agente solo explorará casillas seguras."
            )

    def event_message(self, state):
        action = state.get("last_action")
        labels = {"TURN_LEFT": "Giraste a la izquierda.", "TURN_RIGHT": "Giraste a la derecha.",
                  "FORWARD": "Avanzaste.", "GRAB": "Recogiste el oro.",
                  "SHOOT": "Disparaste una flecha.", "CLIMB": "Intentaste salir."}
        msg = labels.get(action, action or self.message)
        action_sounds = {
            "TURN_LEFT": "turn", "TURN_RIGHT": "turn", "FORWARD": "move",
            "GRAB": "gold", "SHOOT": "shoot",
        }
        if action in action_sounds:
            self.audio.play(action_sounds[action])
        perception = state.get("perception") or {}
        for key, _, _, _ in SENSES:
            if perception.get(key):
                self.audio.play(PERCEPTION_SOUNDS[key])
        if perception.get("bump"):
            self.audio.play("bump")
            msg += " ¡Chocaste con un muro!"
        if perception.get("scream"):
            self.audio.play("arrow_hit")
            self.audio.play("wumpus_death")
            msg += " Se oyó un grito."
        self.message = msg
        if state["status"] != "running":
            self.finished = True
            self.result_hidden = False
            if state["status"] == "success":
                self.audio.play("win")
            else:
                position = tuple(state["agent"]["position"])
                pits = {tuple(cell) for cell in state["world"]["pits"]}
                live_wumpus = {tuple(cell) for cell in state["world"]["live_wumpus"]}
                self.audio.play("pit_fall" if position in pits else
                                "wumpus_growl" if position in live_wumpus else "lose")
                self.audio.play("lose")

    def start(self):
        try:
            self.game = Game(DATA / MAPS[self.map_index][0],
                             allow_risk=self.mode == "agent", arrows=1)
            state = self.game.get_state()
        except Exception as exc:  # el mapa puede faltar o estar mal formado
            self.error = f"No se pudo cargar el mapa: {exc}"
            return
        agent = state["agent"]
        self.paused = False
        self.finished = False
        self.result_hidden = False
        self.auto_agent = self.mode == "agent"
        self.agent_timer = 0.0
        self.notes = {}
        self.vis_pos = None
        self.max_arrows = max(1, agent.get("arrows", 1))
        self.max_lives = self.life_value(agent) or 0
        self.message = "Pedro empezará a explorar." if self.mode == "agent" else \
            "Usa las flechas del teclado o los botones."
        self.audio.stop_music()
        self.set_state("game")

    @staticmethod
    def life_value(agent):
        for key in ("lives", "life", "health", "hp"):
            if key in agent and isinstance(agent[key], (int, float)):
                return int(agent[key])
        return None

    # ----------------------------------------------------------- dibujo --
    def add(self, rect, label, callback, kind="secondary", enabled=True, icon_name=None,
            stack=False, size=20, native=False):
        button = Button(rect, label, callback, kind, enabled, icon_name, stack, size, native)
        self.buttons.append(button)
        return button

    def hit(self, rect, callback):
        self.buttons.append(Button(rect, "", callback, "ghost"))

    def flush_buttons(self, disabled=False, clear=True):
        """Dibuja los botones acumulados.

        Antes de un modal se llama con ``clear=True``: los botones del HUD se pintan
        deshabilitados y se descartan para que no reciban clics. Al final del
        fotograma se llama con ``clear=False``: los botones siguen disponibles para
        el manejo de eventos del siguiente ciclo.
        """
        down = pygame.mouse.get_pressed()[0]
        for button in self.buttons:
            button.draw(self.screen, self.mouse, down, force_disabled=disabled)
        if clear:
            self.buttons = []

    def draw(self):
        self.buttons = []
        self.mouse = pygame.mouse.get_pos()
        self.screen.blit(background(), (0, 0))
        {"menu": self.draw_menu, "mode": self.draw_mode, "maps": self.draw_maps,
         "setup": self.draw_setup, "help": self.draw_help, "settings": self.draw_settings,
         "game": self.draw_game}[self.state]()
        self.update_cursor()
        self.flush_buttons(clear=False)
        if self.fade > 0:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((6, 7, 24, int(255 * self.fade)))
            self.screen.blit(veil, (0, 0))

    def update_cursor(self):
        over = any(b.enabled and b.rect.collidepoint(self.mouse) for b in self.buttons)
        if over == self.hand_cursor:
            return
        self.hand_cursor = over
        try:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if over else pygame.SYSTEM_CURSOR_ARROW)
        except (pygame.error, AttributeError, TypeError):
            pass

    def heading(self, title, subtitle=""):
        img = logo(190, 110)
        if img:
            self.screen.blit(img, (64, 28))
        else:
            draw_text(self.screen, "WUMPUS", (64, 28), 38, TEXT, anchor="topleft",
                      title=True, outline=INK, outline_w=3)
        draw_text(self.screen, title, (W // 2, 38), 44, TEXT, anchor="midtop", title=True,
                  outline=INK, outline_w=3)
        if subtitle:
            draw_text(self.screen, subtitle, (W // 2, 94), 17, MUTED, True, "midtop")

    def nav(self, back_cb, next_cb=None, next_label="Continuar", next_enabled=True,
            next_icon="arrow_right"):
        self.add((60, H - 86, 190, 56), "Volver", back_cb, "tertiary", icon_name="arrow_left")
        if next_cb:
            self.add((W - 290, H - 86, 230, 56), next_label, next_cb, "primary",
                     next_enabled, next_icon)

    def card(self, rect, selected, callback):
        hover = rect.collidepoint(self.mouse)
        fill = PANEL_2 if selected or hover else PANEL
        border = PRIMARY if selected else BORDER_HI if hover else BORDER
        self.screen.blit(panel_surf(rect.w, rect.h, fill, border, 22), rect.topleft)
        if selected:
            c = (rect.right - 30, rect.y + 30)
            pygame.draw.circle(self.screen, SUCCESS, c, 17)
            self.screen.blit(icon("check", 22, TEXT), (c[0] - 11, c[1] - 11))
        self.hit(rect, callback)

    # ------------------------------------------------------------- menú --
    def draw_menu(self):
        img = logo(460, 250)
        if img:
            self.screen.blit(img, img.get_rect(midtop=(W // 2, 20)))
        else:
            self.screen.blit(icon("wumpus", 128), (W // 2 - 64, 14))
            draw_text(self.screen, "WUMPUS", (W // 2, 196), 108, TEXT, anchor="center",
                      title=True, outline=INK, outline_w=7)
        credit = pygame.Rect(W // 2 - 275, H - 58, 550, 42)
        self.screen.blit(panel_surf(credit.w, credit.h, PRIMARY, darken(PRIMARY, .2), 18),
                         credit.topleft)
        draw_text(self.screen, "Realizado por Sebastián Sánchez y Simón Paipa",
                  credit.center, 18, PRIMARY_INK, True, "center")
        bx = W // 2 - 160
        self.add((bx, 300, 320, 62), "Jugar", lambda: self.set_state("mode"), "primary",
                 icon_name="menu_play", size=26)
        self.add((bx, 376, 320, 62), "Configuración", lambda: self.show_settings("menu"),
                 icon_name="menu_settings", size=24)
        self.add((bx, 452, 320, 62), "Cómo jugar", self.show_help,
                 icon_name="menu_book", size=24)
        self.add((bx, 528, 320, 62), "Salir",
                 lambda: pygame.event.post(pygame.event.Event(pygame.QUIT)),
                 "danger", icon_name="menu_exit", size=24)

    # ------------------------------------------------- ayuda / tutorial --
    def draw_help(self):
        self.heading("Cómo jugar", f"Tutorial  ·  {self.help_page + 1} de {len(self.HELP_PAGES)}")
        panel_rect = pygame.Rect(70, 130, W - 140, 466)
        self.screen.blit(panel_surf(panel_rect.w, panel_rect.h, PANEL, BORDER, 24), panel_rect.topleft)
        draw_text(self.screen, self.HELP_PAGES[self.help_page], (panel_rect.x + 40, panel_rect.y + 24),
                  38, PRIMARY, title=True)
        [self.help_mission, self.help_dangers, self.help_senses, self.help_controls,
         self.help_modes][self.help_page](panel_rect)
        for i in range(len(self.HELP_PAGES)):
            col = PRIMARY if i == self.help_page else BORDER
            pygame.draw.circle(self.screen, col, (W // 2 - 40 + i * 20, H - 58), 6)
        last = self.help_page == len(self.HELP_PAGES) - 1
        self.add((70, H - 86, 160, 56), "Menú", self.go_menu, "tertiary", icon_name="home")
        self.add((700, H - 86, 160, 56), "Anterior",
                 lambda: setattr(self, "help_page", self.help_page - 1), "tertiary",
                 self.help_page > 0, "arrow_left")
        if last:
            self.add((870, H - 86, 160, 56), "Entendido", self.go_menu, "primary",
                     icon_name="check")
        else:
            self.add((870, H - 86, 160, 56), "Siguiente",
                     lambda: setattr(self, "help_page", self.help_page + 1), "primary",
                     icon_name="arrow_right")

    def help_mission(self, box):
        side = 96
        x0, y0 = box.x + 50, box.y + 88
        for row in range(3):
            for col in range(4):
                known = (col, row) in ((0, 2), (3, 0))
                self.screen.blit(tile(side - 4, known, (row * 4 + col) % 4),
                                 (x0 + col * side, y0 + row * side))
        self.screen.blit(entrance_overlay(side - 4), (x0, y0 + 2 * side))
        self.screen.blit(icon("pedro", 78), (x0 + 9, y0 + 2 * side + 6))
        self.screen.blit(icon("help_gold", 62), (x0 + 3 * side + 16, y0 + 16))
        tx, tw = box.x + 500, box.w - 560
        text_block(self.screen, "Pedro entra en una cueva oscura donde no ve nada. Tu objetivo es "
                   "encontrar todo el oro y volver a la casilla de entrada para salir.",
                   (tx, box.y + 88), tw, 21, TEXT, line_h=30)
        for i, (ico, msg) in enumerate([
                ("glitter", "Las casillas que visitas se iluminan en el mapa."),
                ("compass", "Usa las percepciones para deducir dónde hay peligro."),
                ("exit", "Recoge el oro y pulsa C en la entrada para salir.")]):
            y = box.y + 215 + i * 56
            self.screen.blit(icon(ico, 38), (tx, y))
            text_block(self.screen, msg, (tx + 56, y + 4), tw - 56, 18, MUTED, True, max_lines=2)

    def help_dangers(self, box):
        cards = [("help_pit", "Pozo", "Si caes en un pozo, pierdes la partida. Se anuncia con una brisa."),
                 ("help_wumpus", "Wumpus", "Si entras en la casilla de un Wumpus vivo, te devora. Se anuncia con hedor."),
                 ("help_arrow", "Flecha", "Dispara en la dirección en la que miras para matar a un Wumpus. Tu munición es limitada.")]
        cw = (box.w - 80 - 40) // 3
        for i, (ico, title, desc) in enumerate(cards):
            r = pygame.Rect(box.x + 40 + i * (cw + 20), box.y + 82, cw, 350)
            self.screen.blit(panel_surf(r.w, r.h, PANEL_2, BORDER, 20), r.topleft)
            self.screen.blit(icon(ico, 118), (r.centerx - 59, r.y + 24))
            draw_text(self.screen, title, (r.centerx, r.y + 172), 30, TEXT, anchor="midtop", title=True)
            text_block(self.screen, desc, (r.x + 22, r.y + 224), r.w - 44, 17, MUTED, True, center=True)

    def help_senses(self, box):
        rows = [("breeze", "Brisa", "Hay un pozo en una casilla vecina."),
                ("stench", "Hedor", "Hay un Wumpus en una casilla vecina."),
                ("glitter", "Brillo", "Hay oro en tu casilla: pulsa G para recogerlo."),
                ("bump", "Golpe", "Has chocado contra un muro."),
                ("scream", "Grito", "Tu flecha ha matado a un Wumpus.")]
        for i, (ico, name, desc) in enumerate(rows):
            y = box.y + 90 + i * 68
            r = pygame.Rect(box.x + 40, y, box.w - 80, 62)
            self.screen.blit(panel_surf(r.w, r.h, PANEL_2, BORDER, 16, False), r.topleft)
            self.screen.blit(icon(ico, 44, SENSES[i][3]), (r.x + 18, r.y + 9))
            draw_text(self.screen, name, (r.x + 88, r.centery), 26, SENSES[i][3], anchor="midleft", title=True)
            draw_text(self.screen, desc, (r.x + 250, r.centery), 19, TEXT, True, "midleft")

    def help_controls(self, box):
        arrows = [("arrow_left", "Girar a la izquierda"), ("arrow_up", "Avanzar"),
                  ("arrow_right", "Girar a la derecha")]
        for i, (ico, cap) in enumerate(arrows):
            r = pygame.Rect(box.x + 120 + i * 280, box.y + 88, 72, 66)
            keycap(self.screen, r, icon_name=ico)
            text_block(self.screen, cap, (r.centerx - 100, r.bottom + 18), 200, 16, MUTED, True, center=True)
        keys = [("G", "Recoger el oro"), ("ESPACIO", "Disparar la flecha"),
                ("C", "Salir por la entrada"), ("ESC", "Pausar el juego")]
        for i, (label, cap) in enumerate(keys):
            r = pygame.Rect(box.x + 120 + (i % 2) * 440, box.y + 232 + (i // 2) * 78,
                            150 if len(label) > 2 else 72, 62)
            keycap(self.screen, r, label)
            draw_text(self.screen, cap, (r.right + 22, r.centery), 19, TEXT, True, "midleft")

    def help_modes(self, box):
        cards = [("pedro", "Explorador", ["Tú tomas cada decisión.", "Usa el teclado o los botones.",
                                               "Descubre la cueva paso a paso."]),
                 ("bot", "Observar al agente", ["Pedro deduce y actúa solo.", "Puedes pausar, ir paso a paso",
                                                  "y cambiar la velocidad."])]
        cw = (box.w - 80 - 30) // 2
        for i, (ico, title, lines) in enumerate(cards):
            r = pygame.Rect(box.x + 40 + i * (cw + 30), box.y + 100, cw, 300)
            self.screen.blit(panel_surf(r.w, r.h, PANEL_2, BORDER, 20), r.topleft)
            self.screen.blit(icon(ico, 96), (r.centerx - 48, r.y + 20))
            draw_text(self.screen, title, (r.centerx, r.y + 130), 30, TEXT, anchor="midtop", title=True)
            for j, line in enumerate(lines):
                draw_text(self.screen, line, (r.centerx, r.y + 186 + j * 30), 18, MUTED, True, "midtop")
        draw_text(self.screen, "Elegirás la modalidad cuando pulses Jugar en el menú principal.",
                  (box.x + 230, box.bottom - 52), 17, MUTED, True)

    # ------------------------------------------------- selección de partida --
    def draw_mode(self):
        self.heading("Elige tu modalidad", "Las dos modalidades usan el mismo mundo y las mismas reglas.")
        cards = [("manual", "pedro", "Explorador", "Toma cada decisión y descubre la cueva.",
                  "Teclado + botones"),
                 ("agent", "bot", "Observar al agente", "Pedro deduce, actúa y vuelve a la entrada.",
                  "Pausa, paso a paso y velocidad")]
        for i, (kind, ico, title, desc, hint) in enumerate(cards):
            r = pygame.Rect(60 + i * (CARD_W + 30), 170, CARD_W, 380)
            self.card(r, self.mode == kind, lambda k=kind: setattr(self, "mode", k))
            self.screen.blit(icon(ico, 180), (r.centerx - 90, r.y + 14))
            draw_text(self.screen, title, (r.centerx, r.y + 194), 34, TEXT, anchor="midtop", title=True)
            text_block(self.screen, desc, (r.x + 40, r.y + 250), r.w - 80, 19, MUTED, True, center=True)
            draw_text(self.screen, hint, (r.centerx, r.y + 320), 16, PRIMARY, True, "midtop")
        self.nav(lambda: self.set_state("menu"), lambda: self.set_state("maps"),
                 next_enabled=self.mode is not None)

    def draw_maps(self):
        self.heading("Selecciona el mapa")
        for i, (filename, name, desc) in enumerate(MAPS):
            col, row = i % 2, i // 2
            r = pygame.Rect(60 + col * (CARD_W + 30), 180 + row * 215, CARD_W, 195)
            self.card(r, i == self.map_index, lambda index=i: setattr(self, "map_index", index))
            self.mini_board(pygame.Rect(r.x + 24, r.y + 28, 138, 138), *map_dims(filename))
            draw_text(self.screen, name, (r.x + 186, r.y + 28), 25, TEXT, title=True)
            text_block(self.screen, desc, (r.x + 186, r.y + 70), r.w - 186 - 28, 16, MUTED, True, max_lines=3)
            w, h = map_dims(filename)
            chip(self.screen, (r.x + 186, r.bottom - 54), "compass", f"{w} x {h}", BORDER_HI)
        self.nav(lambda: self.set_state("mode"), self.start, "Iniciar partida", True, "play")

    def mini_board(self, rect, cols, rows):
        cell = max(2, min(rect.w // cols, rect.h // rows))
        gap = 1 if cell > 7 else 0
        ox = rect.x + (rect.w - cell * cols) // 2
        oy = rect.y + (rect.h - cell * rows) // 2
        pygame.draw.rect(self.screen, INK, pygame.Rect(ox - 4, oy - 4, cell * cols + 8, cell * rows + 8),
                         border_radius=8)
        for r in range(rows):
            for c in range(cols):
                color = PRIMARY if (r, c) == (rows - 1, 0) else (46, 54, 114) if (r + c) % 2 else (38, 45, 98)
                pygame.draw.rect(self.screen, color,
                                 (ox + c * cell, oy + r * cell, cell - gap, cell - gap))

    def draw_setup(self):
        self.heading("Prepara la partida", "Revisa la selección antes de entrar en la cueva.")
        filename, name, desc = MAPS[self.map_index]
        left = pygame.Rect(60, 140, CARD_W, 300)
        right = pygame.Rect(60 + CARD_W + 30, 140, CARD_W, 300)
        for r in (left, right):
            self.screen.blit(panel_surf(r.w, r.h, PANEL, BORDER, 22), r.topleft)
        manual = self.mode == "manual"
        draw_text(self.screen, "MODALIDAD", (left.x + 30, left.y + 24), 15, MUTED, True)
        self.screen.blit(icon("pedro" if manual else "bot", 120), (left.x + 18, left.y + 58))
        draw_text(self.screen, "Explorador" if manual else "Observar al agente",
                  (left.x + 150, left.y + 92), 28, TEXT, title=True)
        text_block(self.screen, "Controlas a Pedro con el teclado o los botones." if manual else
                   "Pedro explora solo; tú puedes pausar o avanzar paso a paso.",
                   (left.x + 150, left.y + 134), left.w - 180, 16, MUTED, True, max_lines=3)
        draw_text(self.screen, "MAPA", (right.x + 30, right.y + 24), 15, MUTED, True)
        self.mini_board(pygame.Rect(right.x + 30, right.y + 64, 120, 120), *map_dims(filename))
        draw_text(self.screen, name, (right.x + 176, right.y + 82), 24, TEXT, title=True)
        text_block(self.screen, desc, (right.x + 176, right.y + 124), right.w - 206, 16, MUTED, True, max_lines=4)
        strip = pygame.Rect(60, 470, W - 120, 70)
        self.screen.blit(panel_surf(strip.w, strip.h, PANEL, BORDER, 18, False), strip.topleft)
        tip = ("Flechas: girar/avanzar  ·  G: recoger  ·  Espacio: disparar  ·  C: salir  ·  Esc: pausa"
               if manual else "Espacio: auto  ·  N: un paso  ·  Esc: pausa  ·  La velocidad se cambia en el panel")
        self.screen.blit(icon("gear", 30, MUTED), (strip.x + 24, strip.y + 20))
        draw_text(self.screen, tip, (strip.x + 72, strip.centery), 17, TEXT, True, "midleft")
        self.nav(lambda: self.set_state("maps"), self.start, "Iniciar partida", True, "play")
        if self.error:
            draw_text(self.screen, self.error, (W // 2, 580), 16, DANGER, True, "center")

    def draw_settings(self):
        self.heading("Configuración", "Los cambios se guardan automáticamente.")
        box = pygame.Rect(60, 138, W - 120, 470)
        self.screen.blit(panel_surf(box.w, box.h, PANEL, BORDER, 24), box.topleft)
        viewport = box.inflate(-24, -24)
        content_y = viewport.y + 18 - self.settings_scroll
        self.screen.set_clip(viewport)

        def section(title, y, icon_name):
            self.screen.blit(icon(icon_name, 26, PRIMARY), (viewport.x + 8, y))
            draw_text(self.screen, title, (viewport.x + 46, y + 3), 22, PRIMARY, title=True)
            pygame.draw.line(self.screen, BORDER, (viewport.x + 8, y + 36),
                             (viewport.right - 8, y + 36), 1)

        def setting_row(title, desc, y, key, icon_name):
            draw_text(self.screen, title, (viewport.x + 18, y), 21, TEXT, title=True)
            draw_text(self.screen, desc, (viewport.x + 18, y + 29), 14, MUTED, True)
            on = self.settings[key]
            rect = pygame.Rect(viewport.right - 158, y + 4, 132, 46)
            if viewport.contains(rect):
                self.add(rect, "Sí" if on else "No", lambda k=key: self.toggle_setting(k),
                         "success" if on else "tertiary",
                         icon_name="check" if on else "close", size=18)

        section("Audio", content_y, "play")
        setting_row("Música de fondo", "Canciones de menús y partida.", content_y + 52,
                    "music", "play")
        setting_row("Efectos de sonido", "Botones, acciones y percepciones.", content_y + 122,
                    "effects", "glitter")

        general_y = content_y + 212
        section("Interfaz", general_y, "gear")
        setting_row("Pantalla completa", "Alterna el modo de visualización.", general_y + 52,
                    "fullscreen", "gear")
        setting_row("Percepciones en el mapa", "Conserva brisa y hedor en casillas visitadas.",
                    general_y + 122, "notes", "compass")
        setting_row("Coordenadas del tablero", "Muestra filas y columnas alrededor del mapa.",
                    general_y + 192, "coords", "compass")

        speed_y = content_y + 452
        section("Agente", speed_y, "bot")
        draw_text(self.screen, "Velocidad de avance", (viewport.x + 18, speed_y + 52),
                  21, TEXT, title=True)
        draw_text(self.screen, "Tiempo entre pasos en la modalidad agente.",
                  (viewport.x + 18, speed_y + 81), 14, MUTED, True)
        for j, (label, _) in enumerate(SPEEDS):
            rect = pygame.Rect(viewport.x + 18 + j * 123, speed_y + 112, 112, 44)
            if viewport.contains(rect):
                self.add(rect, label, lambda idx=j: self.set_speed(idx),
                         "primary" if self.settings["speed"] == j else "tertiary", size=17)

        self.screen.set_clip(None)
        track = pygame.Rect(box.right - 14, viewport.y, 4, viewport.h)
        pygame.draw.rect(self.screen, TERTIARY, track, border_radius=2)
        thumb_h = max(48, int(viewport.h * viewport.h / (viewport.h + self.settings_max_scroll)))
        thumb_y = viewport.y + int((viewport.h - thumb_h) *
                                    self.settings_scroll / self.settings_max_scroll)
        pygame.draw.rect(self.screen, BORDER_HI, (track.x, thumb_y, track.w, thumb_h), border_radius=2)
        self.add((60, H - 86, 190, 56), "Volver", self.back_from_settings, "primary",
                 icon_name="arrow_left")

    # ------------------------------------------------------------ juego --
    def draw_game(self):
        state = self.game.get_state()
        self.update_notes(state)
        self.draw_topbar()
        self.draw_board(state)
        self.draw_sidebar(state)
        if self.finished and not self.result_hidden:
            self.flush_buttons(disabled=True)
            self.draw_result(state)
        elif self.finished:
            self.flush_buttons(disabled=True)
            self.draw_reveal_bar()
        elif self.paused:
            self.flush_buttons(disabled=True)
            self.draw_pause()

    def update_notes(self, state):
        pos = tuple(state["agent"]["position"])
        senses = {key for key, *_ in SENSES if (state.get("perception") or {}).get(key)}
        self.notes.setdefault(pos, set()).update(senses & {"breeze", "stench"})

    def draw_topbar(self):
        # En la vista de juego el tablero comienza más arriba que en los menús.
        img = logo(132, 68)
        if img:
            self.screen.blit(img, (40, 8))
        else:
            draw_text(self.screen, "WUMPUS", (40, 8), 30, TEXT, anchor="topleft", title=True,
                      outline=INK, outline_w=3)
        manual = self.mode == "manual"
        r = chip(self.screen, (190, 25), "pedro" if manual else "bot",
                 "Explorador" if manual else "Agente", SECONDARY)
        chip(self.screen, (r.right + 12, 25), "compass", MAPS[self.map_index][1], BORDER_HI)
        self.add((W - 76, 14, 52, 52), "", lambda: setattr(self, "paused", True), "secondary",
                 icon_name="pause")

    def board_geometry(self, state):
        width, height = state["board_size"]
        area = pygame.Rect(24, 84, SX - 36, 612)
        side = max(10, min((area.w - 36) // width, (area.h - 36) // height, 140))
        rect = pygame.Rect(0, 0, side * width, side * height)
        rect.center = area.center
        return rect, side

    def draw_board(self, state):
        width, height = state["board_size"]
        rect, side = self.board_geometry(state)
        frame = rect.inflate(30, 30)
        self.screen.blit(panel_surf(frame.w, frame.h, (9, 11, 34), BORDER, 24), frame.topleft)
        visited = set(map(tuple, state["knowledge"]["visited"]))
        start = tuple(state["initial_position"])
        reveal = self.finished
        world = state["world"]
        pits = {tuple(p) for p in world["pits"]}
        gold = {tuple(p) for p in world["gold"]}
        wumpus = {tuple(p) for p in world["live_wumpus"]}
        show_notes = self.settings["notes"] and side >= 36
        layers = ((pits, "pit", .78), (gold, "gold", .62), (wumpus, "wumpus", .8))
        for y in range(1, height + 1):
            for x in range(1, width + 1):
                cx, cy = rect.x + (x - 1) * side, rect.bottom - y * side
                known = (x, y) in visited or (x, y) == start or reveal
                self.screen.blit(tile(side - 3, known, (x * 7 + y * 13) % 4), (cx + 1, cy + 1))
                if (x, y) == start:
                    self.screen.blit(entrance_overlay(side - 3), (cx + 1, cy + 1))
                if not known:
                    continue
                for cells, name, frac in layers:
                    if (x, y) in cells:
                        img = icon(name, int(side * frac))
                        self.screen.blit(img, img.get_rect(center=(cx + side // 2, cy + side // 2)))
                if show_notes and (x, y) in self.notes:
                    for n, key in enumerate(sorted(self.notes[(x, y)])):
                        small = icon(key, int(side * .28))
                        self.screen.blit(small, (cx + 5 + n * (small.get_width() + 1), cy + side - small.get_height() - 5))
        if state["status"] != "success":
            self.draw_explorer(state, rect, side)
        # Solo se destaca el oro de la casilla que ocupa el explorador. El resto
        # se muestra únicamente después de haber sido descubierto.
        agent_position = tuple(state["agent"]["position"])
        if agent_position in gold:
            x, y = agent_position
            cx, cy = rect.x + (x - .5) * side, rect.bottom - (y - .5) * side
            gold_size = max(12, int(side * .42))
            gold_img = icon("gold", gold_size)
            self.screen.blit(gold_img, gold_img.get_rect(
                center=(round(cx + side * .28), round(cy - side * .28))))
        if self.settings["coords"] and side >= 24:
            for x in range(1, width + 1):
                draw_text(self.screen, x, (rect.x + (x - .5) * side, rect.bottom + 9), 12, MUTED, True, "center")
            for y in range(1, height + 1):
                draw_text(self.screen, y, (rect.x - 10, rect.bottom - (y - .5) * side), 12, MUTED, True, "center")

    def draw_explorer(self, state, rect, side):
        agent = state["agent"]
        x, y = agent["position"]
        target = (rect.x + (x - .5) * side, rect.bottom - (y - .5) * side)
        if self.vis_pos is None:
            self.vis_pos = list(target)
        else:
            k = min(1.0, 16 * (1 / 60))
            self.vis_pos[0] += (target[0] - self.vis_pos[0]) * k
            self.vis_pos[1] += (target[1] - self.vis_pos[1]) * k
        facing = norm_dir(agent["direction"])
        px, py = self.vis_pos
        py += math.sin(self.t * 5) * side * .02
        g = glow(int(side * .8), PRIMARY)
        self.screen.blit(g, g.get_rect(center=(px, py)))
        img = icon("pedro" if self.mode == "manual" else "bot", int(side * .88))
        self.screen.blit(img, img.get_rect(center=(px, py - side * .03)))
        if side >= 30:
            vx, vy = DIR_VEC[facing]
            tipx, tipy = px + vx * side * .45, py + vy * side * .45
            nx, ny = -vy, vx
            pygame.draw.polygon(self.screen, PRIMARY, [
                (tipx, tipy), (tipx - vx * side * .14 + nx * side * .1, tipy - vy * side * .14 + ny * side * .1),
                (tipx - vx * side * .14 - nx * side * .1, tipy - vy * side * .14 - ny * side * .1)])

    def stat_tile(self, rect, icon_name, label, value=None, extra=None):
        self.screen.blit(panel_surf(rect.w, rect.h, (20, 23, 64), None, 12, False), rect.topleft)
        self.screen.blit(icon(icon_name, 32), (rect.x + 10, rect.centery - 16))
        draw_text(self.screen, label, (rect.x + 50, rect.y + 5), 10, MUTED, True)
        if extra:
            extra(rect)
        else:
            draw_text(self.screen, value, (rect.x + 50, rect.y + 19), 19, TEXT, True)

    def draw_sidebar(self, state):
        agent = state["agent"]
        sx, sw = SX, SB_W
        # --- estadísticas ---
        lives = self.life_value(agent)
        world = state["world"]

        def hearts_extra(rect):
            for i in range(max(self.max_lives, lives or 0)):
                col = None if i < (lives or 0) else (70, 76, 120)
                self.screen.blit(icon("heart", 20, col), (rect.x + 50 + i * 22, rect.y + 22))

        tiles = [("gold", "ORO", f"{agent['collected_gold']}/{agent['total_gold']}", None),
                 ("arrow", "FLECHAS", f"x{agent['arrows']}", None),
                 ("pit", "POZOS", len(world["pits"]), None),
                 ("wumpus", "WUMPUS", len(world["live_wumpus"]), None)]
        if lives is not None:
            tiles.append(("heart", "VIDA", None, hearts_extra))
        tiles.append(("glitter", "PUNTOS", agent["score"], None))
        rows = (len(tiles) + 1) // 2
        panel = pygame.Rect(sx, 84, sw, 22 + rows * 48)
        self.screen.blit(panel_surf(panel.w, panel.h, PANEL, BORDER, 18), panel.topleft)
        for i, (ico, label, value, extra) in enumerate(tiles):
            full = i == len(tiles) - 1 and len(tiles) % 2 == 1
            tw = panel.w - 24 if full else (panel.w - 32) // 2
            tx = panel.x + 12 + (0 if full else (i % 2) * (tw + 8))
            self.stat_tile(pygame.Rect(tx, panel.y + 10 + (i // 2) * 48, tw, 42), ico, label, value, extra)
        y = panel.bottom + 10
        # --- brújula ---
        facing = norm_dir(agent["direction"])
        comp = pygame.Rect(sx, y, sw, 94)
        self.screen.blit(panel_surf(comp.w, comp.h, PANEL, BORDER, 18), comp.topleft)
        img = compass_surf(31, facing)
        self.screen.blit(img, img.get_rect(center=(comp.x + 60, comp.centery)))
        px, py = agent["position"]
        draw_text(self.screen, f"({px}, {py})", (comp.x + 120, comp.centery), 21, TEXT, True, "midleft")
        draw_text(self.screen, DIR_NAMES[facing], (comp.right - 18, comp.centery), 19, PRIMARY, True, "midright")
        y = comp.bottom + 10
        # --- percepción ---
        p = state.get("perception") or {}
        active = [s for s in SENSES if p.get(s[0])]
        per = pygame.Rect(sx, y, sw, 92)
        self.screen.blit(panel_surf(per.w, per.h, PANEL, BORDER, 18), per.topleft)
        draw_text(self.screen, "SEÑALES", (per.x + 18, per.y + 10), 10, MUTED, True)
        if not active:
            draw_text(self.screen, "—", (per.centerx, per.centery + 8), 22, MUTED, True, "center")
        else:
            signal_size = 38
            total_width = len(active) * signal_size + (len(active) - 1) * 8
            cx = per.centerx - total_width // 2
            cy = per.y + 42
            for key, _, ico, color in active:
                chip_rect = pygame.Rect(cx, cy, signal_size, signal_size)
                self.screen.blit(panel_surf(signal_size, signal_size, mix(color, PANEL, .78),
                                            color, 12, False), chip_rect.topleft)
                self.screen.blit(icon(ico, 28), icon(ico, 28).get_rect(center=chip_rect.center))
                self.hit(chip_rect, lambda sound=PERCEPTION_SOUNDS[key]: self.audio.play(sound))
                cx += signal_size + 8
        # --- acciones ---
        y = per.bottom + 12
        if self.mode == "manual":
            action_height = 696 - y
        else:
            action_height = 14 + 50 + 18 + 44 + 12 + 48 + 14
        act = pygame.Rect(sx, y, sw, action_height)
        self.screen.blit(panel_surf(act.w, act.h, PANEL, BORDER, 18), act.topleft)
        if self.mode == "manual":
            pad, gap = 14, 8
            bw = (act.w - pad * 2 - gap) // 2
            items = [("Girar izq.", "turn_left", "secondary", "TURN_LEFT"),
                     ("Girar der.", "turn_right", "secondary", "TURN_RIGHT"),
                     ("Avanzar", "arrow_up", "secondary", "FORWARD"),
                     ("Recoger", "gold", "primary", "GRAB"),
                     ("Disparar", "arrow", "danger", "SHOOT"),
                     ("Salir", "exit", "tertiary", "CLIMB")]
            bh = max(52, (act.h - pad * 2 - gap * 2) // 3)
            for i, (label, ico, kind, action) in enumerate(items):
                self.add((act.x + pad + (i % 2) * (bw + gap),
                          act.y + pad + (i // 2) * (bh + gap), bw, bh), label,
                         lambda a=action: self.perform(a), kind, icon_name=ico, stack=True, size=14)
        else:
            pad, gap = 14, 10
            bw = (act.w - pad * 2 - gap) // 2
            running = self.auto_agent
            control_h = 50
            control_y = act.y + pad
            self.add((act.x + pad, control_y, bw, control_h), "Detener" if running else "Reanudar",
                     lambda: setattr(self, "auto_agent", not self.auto_agent),
                     "tertiary" if running else "primary", icon_name="pause" if running else "play",
                     stack=True, size=14)
            self.add((act.x + pad + bw + gap, control_y, bw, control_h), "Paso", self.agent_step,
                     "secondary", icon_name="arrow_right", stack=True, size=14)
            speed_y = control_y + control_h + 18
            sp = self.settings["speed"]
            speed_button = 44
            self.add((act.x + pad, speed_y, speed_button, speed_button), "",
                     lambda: self.set_speed(sp - 1), "tertiary", sp > 0, "minus")
            self.add((act.right - pad - speed_button, speed_y, speed_button, speed_button), "",
                     lambda: self.set_speed(sp + 1), "tertiary",
                     sp < len(SPEEDS) - 1, "plus")
            draw_text(self.screen, "VELOCIDAD", (act.centerx, speed_y + 2), 11, MUTED, True, "midtop")
            draw_text(self.screen, SPEEDS[sp][0], (act.centerx, speed_y + 23), 21, PRIMARY,
                      anchor="center", title=True)
            risk_y = speed_y + speed_button + 12
            risk_enabled = state["allow_risk"]
            self.add((act.x + pad, risk_y, act.w - pad * 2, 48),
                     "Riesgo: Activado" if risk_enabled else "Riesgo: Desactivado",
                     self.toggle_risk, "success" if risk_enabled else "tertiary",
                     icon_name="check" if risk_enabled else "close", size=15)

    # --------------------------------------------------------- modales --
    def dim(self, alpha=185):
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((4, 6, 22, alpha))
        self.screen.blit(veil, (0, 0))

    def draw_pause(self):
        self.dim()
        box = pygame.Rect(0, 0, 480, 470)
        box.center = (W // 2, H // 2)
        self.screen.blit(panel_surf(box.w, box.h, PANEL, BORDER, 26), box.topleft)
        draw_text(self.screen, "En pausa", (box.centerx, box.y + 62), 52, TEXT, anchor="center",
                  title=True, outline=INK, outline_w=4)
        bx, bw = box.x + 50, box.w - 100
        self.add((bx, box.y + 118, bw, 60), "Continuar", lambda: setattr(self, "paused", False),
                 "primary", icon_name="play", size=24)
        self.add((bx, box.y + 192, bw, 60), "Configuración", lambda: self.show_settings("game"),
                 icon_name="gear", size=22)
        self.add((bx, box.y + 266, bw, 60), "Reiniciar", self.start, "tertiary",
                 icon_name="retry", size=22)
        self.add((bx, box.y + 340, bw, 60), "Menú principal", self.go_menu, "tertiary",
                 icon_name="home", size=22)
        self.add((box.right - 58, box.y + 14, 40, 40), "", lambda: setattr(self, "paused", False),
                 "tertiary", icon_name="close")

    def outcome(self, state):
        status = str(state["status"]).lower()
        agent = state["agent"]
        if status == "success":
            return "win", "¡Ganaste!", "Has encontrado el tesoro y escapado.", "chest"
        if any(word in status for word in DEATH_WORDS):
            if "pit" in status or "pozo" in status:
                reason = "Caíste en un pozo sin fondo…"
            elif "wumpus" in status:
                reason = "El Wumpus te ha comido…"
            else:
                reason = "Pedro no sobrevivió a la cueva…"
            return "lose", "¡Game Over!", reason, "wumpus"
        return "end", "Fin de la partida", \
            f"Saliste con {agent['collected_gold']} de {agent['total_gold']} oros.", "gold"

    def draw_result(self, state):
        kind, title, sub, ico = self.outcome(state)
        self.dim(200)
        box = pygame.Rect(0, 0, 540, 540)
        box.center = (W // 2, H // 2)
        self.screen.blit(panel_surf(box.w, box.h, PANEL, BORDER, 28), box.topleft)
        color = {"win": PRIMARY, "lose": DANGER, "end": TEXT}[kind]
        if kind == "win":
            for i in range(6):
                a = self.t * 1.2 + i * math.pi / 3
                r = 104 + 8 * math.sin(self.t * 3 + i)
                s = int(26 + 8 * math.sin(self.t * 4 + i * 2))
                self.screen.blit(icon("glitter", s), icon("glitter", s).get_rect(
                    center=(box.centerx + math.cos(a) * r, box.y + 112 + math.sin(a) * r * .62)))
        bob = math.sin(self.t * 2.4) * 4
        self.screen.blit(icon(ico, 144), (box.centerx - 72, box.y + 40 + bob))
        draw_text(self.screen, title, (box.centerx, box.y + 218), 52, color, anchor="center",
                  title=True, outline=INK, outline_w=4)
        text_block(self.screen, sub, (box.x + 50, box.y + 252), box.w - 100, 20, TEXT, True, center=True)
        agent = state["agent"]
        draw_text(self.screen, f"Oro {agent['collected_gold']}/{agent['total_gold']}   ·   Puntos {agent['score']}",
                  (box.centerx, box.y + 296), 17, MUTED, True, "center")
        bx, bw = box.x + 60, box.w - 120
        self.add((bx, box.y + 340, bw, 58), "Jugar de nuevo", self.start, "primary",
                 icon_name="retry", size=23)
        self.add((bx, box.y + 410, (bw - 12) // 2, 54), "Ver cueva",
                 lambda: setattr(self, "result_hidden", True), "secondary", icon_name="compass", size=19)
        self.add((bx + (bw - 12) // 2 + 12, box.y + 410, (bw - 12) // 2, 54), "Menú",
                 self.go_menu, "tertiary", icon_name="home", size=19)

    def draw_reveal_bar(self):
        # Ocupa toda la zona vertical del menú de acciones del lateral.
        bar = pygame.Rect(SX, 470, SB_W, H - 470 - 24)
        self.screen.blit(panel_surf(bar.w, bar.h, PANEL, BORDER, 20), bar.topleft)
        draw_text(self.screen, "Cueva revelada", (bar.centerx, bar.y + 24), 21, TEXT,
                  anchor="midtop", title=True)
        button_h = 54
        self.add((bar.x + 18, bar.y + 72, bar.w - 36, button_h), "Ver resultado",
                 lambda: setattr(self, "result_hidden", False), "primary",
                 icon_name="check", size=18)
        self.add((bar.x + 18, bar.y + 72 + button_h + 14, bar.w - 36, button_h), "Menú", self.go_menu,
                 "tertiary", icon_name="home", size=18)


def main():
    """Punto de entrada de la aplicación gráfica."""
    App().run()


if __name__ == "__main__":
    main()
