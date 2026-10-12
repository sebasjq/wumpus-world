"""Interfaz Pygame del Mundo de Wumpus.

La vista usa ``Game`` como única fuente de verdad. El modo manual llama a
``Game.act`` y el modo agente avanza con ``Game.step`` mediante un temporizador,
por lo que el bucle de Pygame nunca queda bloqueado.
"""

from pathlib import Path
import sys

import pygame

from logic.game import Game

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MAPS = [
    ("board_4x4.json", "Mapa 4 x 4", "Ejemplo pequeño con un oro, un Wumpus y tres pozos."),
    ("board_16x16.json", "Mapa 16 x 16", "Cueva grande con 37 oros, nueve Wumpus y 11 pozos."),
    ("board_shoot_test.json", "Mapa de disparo", "Prueba de flecha: el oro comparte casilla con el Wumpus."),
    ("board_no_safe_path_test.json", "Mapa sin salida segura", "Prueba de retirada con peligros junto a la entrada."),
]

BG = (16, 23, 42)
PANEL = (28, 39, 66)
PANEL_2 = (35, 48, 82)
BORDER = (65, 82, 137)
PRIMARY = (255, 191, 63)
SECONDARY = (82, 104, 217)
DANGER = (240, 68, 82)
SUCCESS = (32, 185, 150)
TEXT = (244, 245, 250)
MUTED = (170, 183, 208)
CELL = (31, 46, 79)
CELL_ALT = (36, 52, 88)


def font(size, bold=False):
    """Devuelve una fuente del sistema sin depender de recursos externos."""
    return pygame.font.SysFont("Trebuchet MS", size, bold=bold)


def text(surface, value, pos, size=20, color=TEXT, bold=False, center=False):
    image = font(size, bold).render(str(value), True, color)
    rect = image.get_rect(center=pos) if center else image.get_rect(topleft=pos)
    surface.blit(image, rect)
    return rect


def panel(surface, rect, fill=PANEL, radius=14):
    pygame.draw.rect(surface, (8, 13, 28), rect.move(0, 5), border_radius=radius)
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, BORDER, rect, 1, border_radius=radius)


class Button:
    """Botón reutilizable con estados normal, hover y deshabilitado."""

    def __init__(self, rect, label, callback, kind="secondary", enabled=True):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.callback = callback
        self.kind = kind
        self.enabled = enabled

    def draw(self, surface):
        hover = self.enabled and self.rect.collidepoint(pygame.mouse.get_pos())
        colors = {"primary": PRIMARY, "danger": DANGER, "secondary": SECONDARY,
                  "tertiary": (54, 66, 112)}
        fill = colors.get(self.kind, SECONDARY) if self.enabled else (62, 70, 95)
        if hover:
            fill = tuple(min(255, c + 18) for c in fill)
        pygame.draw.rect(surface, (8, 13, 28), self.rect.move(0, 4), border_radius=10)
        pygame.draw.rect(surface, fill, self.rect, border_radius=10)
        color = (25, 29, 42) if self.kind == "primary" and self.enabled else TEXT
        text(surface, self.label, self.rect.center, 18, color, True, True)

    def click(self, event):
        if self.enabled and event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()
                return True
        return False


class App:
    """Controla navegación, renderizado e integración incremental con ``Game``."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Wumpus World")
        self.screen = pygame.display.set_mode((1200, 760), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.state = "menu"
        self.mode = None
        self.map_index = 0
        self.game = None
        self.paused = False
        self.auto_agent = True
        self.message = "Explora la cueva y encuentra todo el oro."
        self.buttons = []

    def set_state(self, state):
        self.state = state
        self.buttons = []

    def run(self):
        """Ejecuta el bucle principal hasta que el usuario cierre la ventana."""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    self.key(event)
                for button in self.buttons:
                    button.click(event)

            if self.state == "game" and self.mode == "agent" and self.auto_agent:
                if not self.paused and self.game and self.game.status == "running":
                    if pygame.time.get_ticks() % 260 < 18:
                        state = self.game.step()
                        self.event_message(state)

            self.draw()
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()

    def key(self, event):
        if self.state != "game" or self.mode != "manual" or self.paused:
            return
        actions = {pygame.K_LEFT: "TURN_LEFT", pygame.K_RIGHT: "TURN_RIGHT",
                   pygame.K_UP: "FORWARD", pygame.K_g: "GRAB",
                   pygame.K_SPACE: "SHOOT", pygame.K_c: "CLIMB"}
        if event.key in actions:
            self.perform(actions[event.key])
        elif event.key == pygame.K_ESCAPE:
            self.paused = True

    def perform(self, action):
        if self.game and not self.paused:
            self.event_message(self.game.act(action))

    def event_message(self, state):
        action = state.get("last_action")
        labels = {"TURN_LEFT": "Giraste a la izquierda.", "TURN_RIGHT": "Giraste a la derecha.",
                  "FORWARD": "Avanzaste.", "GRAB": "Recogiste el oro.",
                  "SHOOT": "Disparaste una flecha.", "CLIMB": "Intentaste salir."}
        self.message = labels.get(action, action or self.message)
        if state["status"] != "running":
            self.set_state("result")

    def start(self):
        self.game = Game(DATA / MAPS[self.map_index][0],
                         allow_risk=self.mode == "agent", arrows=1)
        self.paused = False
        self.auto_agent = self.mode == "agent"
        self.message = "El agente comenzará a explorar." if self.mode == "agent" else \
            "Usa las flechas o los controles para explorar."
        self.set_state("game")

    def add(self, rect, label, callback, kind="secondary", enabled=True):
        self.buttons.append(Button(rect, label, callback, kind, enabled))

    def draw(self):
        self.buttons = []
        self.screen.fill(BG)
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "mode":
            self.draw_mode()
        elif self.state == "maps":
            self.draw_maps()
        elif self.state == "setup":
            self.draw_setup()
        elif self.state == "game":
            self.draw_game()
        elif self.state == "result":
            self.draw_game()
            self.draw_result()
        for button in self.buttons:
            button.draw(self.screen)

    def heading(self, title, subtitle=""):
        text(self.screen, title, (60, 45), 38, TEXT, True)
        if subtitle:
            text(self.screen, subtitle, (62, 92), 17, MUTED)

    def draw_menu(self):
        self.heading("WUMPUS", "Una aventura de deducción en la cueva")
        panel(self.screen, pygame.Rect(60, 155, 500, 490), PANEL)
        pygame.draw.circle(self.screen, (48, 60, 125), (310, 310), 105)
        pygame.draw.circle(self.screen, (20, 25, 55), (270, 295), 16)
        pygame.draw.circle(self.screen, (20, 25, 55), (350, 295), 16)
        pygame.draw.polygon(self.screen, PRIMARY, [(265, 330), (355, 330), (310, 365)])
        text(self.screen, "¡La cueva te espera!", (310, 440), 24, TEXT, True, True)
        self.add((680, 220, 360, 58), "JUGAR", lambda: self.set_state("mode"), "primary")
        self.add((680, 300, 360, 58), "CÓMO JUGAR", self.show_help)
        self.add((680, 380, 360, 58), "SALIR", lambda: pygame.event.post(pygame.event.Event(pygame.QUIT)), "tertiary")
        text(self.screen, "Flechas: mover   G: oro   Espacio: disparar   C: salir",
             (680, 510), 16, MUTED)

    def show_help(self):
        self.message = "Manual: flechas mueven o giran; G recoge, Espacio dispara y C sube."
        self.set_state("mode")

    def draw_mode(self):
        self.heading("ELIGE TU MODALIDAD", "Las dos modalidades usan el mismo mundo y las mismas reglas.")
        cards = [("manual", "EXPLORADOR", "Toma cada decisión y descubre la cueva.", "Flechas + botones"),
                 ("agent", "OBSERVAR AL AGENTE", "Pedro deduce, actúa y vuelve a la entrada.", "Ejecución paso a paso")]
        for i, (kind, title, desc, hint) in enumerate(cards):
            rect = pygame.Rect(90 + i * 520, 180, 460, 270)
            panel(self.screen, rect, PANEL_2 if self.mode == kind else PANEL)
            text(self.screen, "✦" if kind == "manual" else "◎", (rect.centerx, 230), 50,
                 PRIMARY if kind == "manual" else SUCCESS, True, True)
            text(self.screen, title, (rect.centerx, 300), 23, TEXT, True, True)
            text(self.screen, desc, (rect.centerx, 345), 16, MUTED, center=True)
            text(self.screen, hint, (rect.centerx, 380), 15, MUTED, center=True)
            self.add((rect.x + 110, 500, 240, 52), "SELECCIONAR",
                     lambda k=kind: self.choose_mode(k),
                     "primary" if self.mode == kind else "secondary")
        self.add((80, 680, 180, 48), "VOLVER", lambda: self.set_state("menu"), "tertiary")
        self.add((920, 680, 200, 48), "CONTINUAR",
                 lambda: self.set_state("maps"), "primary", self.mode is not None)

    def choose_mode(self, mode):
        self.mode = mode
        self.buttons = []

    def draw_maps(self):
        self.heading("SELECCIONA EL MAPA", "Son los cuatro tableros JSON disponibles en data/.")
        for i, (_, name, desc) in enumerate(MAPS):
            col, row = i % 2, i // 2
            rect = pygame.Rect(70 + col * 550, 145 + row * 220, 500, 190)
            selected = i == self.map_index
            panel(self.screen, rect, PANEL_2 if selected else PANEL)
            text(self.screen, name, (rect.x + 24, rect.y + 22), 22, TEXT, True)
            text(self.screen, desc, (rect.x + 24, rect.y + 63), 15, MUTED)
            self.preview(rect.x + 24, rect.y + 100, i)
            text(self.screen, "SELECCIONADO" if selected else "",
                 (rect.right - 95, rect.y + 120), 14, SUCCESS, True, True)
            self.add((rect.right - 165, rect.y + 135, 130, 40), "ELEGIR",
                     lambda index=i: self.choose_map(index),
                     "primary" if selected else "secondary")
        self.add((80, 680, 180, 48), "VOLVER", lambda: self.set_state("mode"), "tertiary")
        self.add((920, 680, 200, 48), "CONTINUAR", lambda: self.set_state("setup"), "primary")

    def choose_map(self, index):
        self.map_index = index
        self.buttons = []

    def preview(self, x, y, index):
        size = 8 if index == 1 else 13
        for row in range(size):
            for col in range(size):
                r = pygame.Rect(x + col * 12, y + row * 12, 10, 10)
                pygame.draw.rect(self.screen, CELL_ALT if (row + col) % 2 else CELL, r)
        text(self.screen, f"{MAPS[index][0]}  ·  {size} x {size}",
             (x + size * 12 + 20, y + 16), 14, MUTED)

    def draw_setup(self):
        self.heading("PREPARA LA PARTIDA", "Revisa la selección antes de entrar en la cueva.")
        panel(self.screen, pygame.Rect(250, 170, 700, 350), PANEL)
        text(self.screen, f"MODALIDAD: {'EXPLORADOR' if self.mode == 'manual' else 'OBSERVAR AL AGENTE'}",
             (320, 250), 23, TEXT, True)
        text(self.screen, f"MAPA: {MAPS[self.map_index][1]}",
             (320, 310), 23, TEXT, True)
        text(self.screen, MAPS[self.map_index][2], (320, 370), 17, MUTED)
        self.add((250, 600, 180, 52), "VOLVER", lambda: self.set_state("maps"), "tertiary")
        self.add((700, 600, 250, 52), "INICIAR PARTIDA", self.start, "primary")

    def draw_game(self):
        state = self.game.get_state()
        self.heading("WUMPUS WORLD", f"{'MANUAL' if self.mode == 'manual' else 'AGENTE'}  ·  {MAPS[self.map_index][1]}")
        board = self.board_rect(state)
        self.draw_board(board, state)
        panel(self.screen, pygame.Rect(850, 130, 300, 510), PANEL)
        agent = state["agent"]
        text(self.screen, f"Oro  {agent['collected_gold']}/{agent['total_gold']}", (880, 170), 21, PRIMARY, True)
        text(self.screen, f"Flechas  {agent['arrows']}    Puntos  {agent['score']}", (880, 210), 16, TEXT)
        text(self.screen, f"Posición  {tuple(agent['position'])}   Dirección {agent['direction']}", (880, 245), 15, MUTED)
        text(self.screen, self.message, (880, 295), 16, TEXT)
        if state["perception"]:
            p = state["perception"]
            senses = [name for name, key in (("Brisa", "breeze"), ("Hedor", "stench"),
                                               ("Brillo", "glitter"), ("Golpe", "bump"),
                                               ("Grito", "scream")) if p[key]]
            text(self.screen, "Percepción: " + (", ".join(senses) or "ninguna"),
                 (880, 350), 15, SUCCESS if senses else MUTED)
        text(self.screen, "Controles", (880, 410), 18, TEXT, True)
        text(self.screen, "← → girar   ↑ avanzar", (880, 445), 15, MUTED)
        text(self.screen, "G recoger   Espacio disparar", (880, 470), 15, MUTED)
        text(self.screen, "C salir   ESC pausar", (880, 495), 15, MUTED)
        if self.mode == "manual":
            self.add((880, 535, 75, 40), "G", lambda: self.perform("GRAB"), "secondary")
            self.add((965, 535, 75, 40), "DISP.", lambda: self.perform("SHOOT"), "danger")
            self.add((1050, 535, 75, 40), "SALIR", lambda: self.perform("CLIMB"), "tertiary")
        else:
            self.add((880, 535, 115, 40), "PAUSAR" if not self.paused else "SEGUIR",
                     lambda: setattr(self, "paused", not self.paused), "primary")
            self.add((1010, 535, 115, 40), "PASO", self.agent_step, "secondary")
        self.add((880, 585, 115, 40), "PAUSA" if not self.paused else "SEGUIR",
                 lambda: setattr(self, "paused", not self.paused), "tertiary")
        self.add((880, 635, 245, 40), "REINICIAR", self.start, "tertiary")
        self.add((880, 685, 245, 40), "MENÚ PRINCIPAL", lambda: self.set_state("menu"), "tertiary")
        if self.paused:
            self.draw_pause()

    def draw_pause(self):
        """Dibuja una capa modal que detiene tanto el modo manual como el agente."""
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((4, 8, 20, 175))
        self.screen.blit(overlay, (0, 0))
        panel(self.screen, pygame.Rect(350, 220, 500, 270), PANEL_2)
        text(self.screen, "EN PAUSA", (600, 285), 34, TEXT, True, True)
        text(self.screen, "La partida conserva su estado actual.", (600, 330),
             17, MUTED, center=True)
        self.add((405, 390, 170, 48), "CONTINUAR",
                 lambda: setattr(self, "paused", False), "primary")
        self.add((625, 390, 170, 48), "REINICIAR", self.start, "tertiary")

    def agent_step(self):
        if self.mode == "agent" and not self.paused and self.game.status == "running":
            self.event_message(self.game.step())

    def board_rect(self, state):
        width, height = state["board_size"]
        side = min(700 // width, 610 // height)
        return pygame.Rect(60, 130, side * width, side * height)

    def draw_board(self, rect, state):
        width, height = state["board_size"]
        side = rect.width // width
        visible = set(map(tuple, state["knowledge"]["visited"]))
        pos = tuple(state["agent"]["position"])
        for y in range(1, height + 1):
            for x in range(1, width + 1):
                cell = pygame.Rect(rect.x + (x - 1) * side,
                                   rect.bottom - y * side, side - 2, side - 2)
                known = (x, y) in visible or tuple(state["initial_position"]) == (x, y)
                pygame.draw.rect(self.screen, CELL_ALT if known else CELL, cell)
                pygame.draw.rect(self.screen, BORDER, cell, 1)
                if (x, y) == pos and state["status"] != "success":
                    pygame.draw.circle(self.screen, PRIMARY, cell.center, max(5, side // 4))
                    text(self.screen, "P", cell.center, max(12, side // 3), (35, 35, 45), True, True)
                if known:
                    world = state["world"]
                    if [x, y] in world["gold"]:
                        text(self.screen, "$", cell.center, max(12, side // 3), PRIMARY, True, True)
                    if [x, y] in world["pits"]:
                        text(self.screen, "X", cell.center, max(12, side // 3), DANGER, True, True)
                    if [x, y] in world["live_wumpus"]:
                        text(self.screen, "W", cell.center, max(12, side // 3), DANGER, True, True)
        text(self.screen, "N", (rect.centerx, rect.y - 22), 14, MUTED, True, True)

    def draw_result(self):
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((4, 8, 20, 190))
        self.screen.blit(overlay, (0, 0))
        status = self.game.status
        won = status == "success"
        panel(self.screen, pygame.Rect(310, 205, 580, 330), PANEL_2)
        text(self.screen, "¡GANASTE!" if won else "PARTIDA TERMINADA",
             (600, 270), 34, SUCCESS if won else DANGER, True, True)
        text(self.screen, "Pedro salió con todo el oro." if won else
             f"Resultado: {status}. Revisa la cueva y vuelve a intentarlo.",
             (600, 330), 17, TEXT, center=True)
        self.add((380, 430, 210, 52), "JUGAR DE NUEVO", self.start, "primary")
        self.add((610, 430, 210, 52), "MENÚ PRINCIPAL", lambda: self.set_state("menu"), "tertiary")


def main():
    """Punto de entrada de la aplicación gráfica."""
    App().run()


if __name__ == "__main__":
    main()
