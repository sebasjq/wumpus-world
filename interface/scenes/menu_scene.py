from pathlib import Path

import pygame

from ..config import COLORS, DATA_ROOT, SCREEN_SIZE
from ..core.scene import Scene
from ..ui.button import Button
from ..ui.theme import draw_panel, label


class MenuScene(Scene):
    def __init__(self, manager, start_game):
        super().__init__(manager)
        self.start_game = start_game
        self.font = pygame.font.Font(None, 42)
        self.small = pygame.font.Font(None, 28)
        self.boards = sorted(DATA_ROOT.glob("board_*.json"))
        self.index = 0
        self.auto = True
        self.button = Button((430, 500, 420, 60), "Iniciar partida", self.small, self.begin)

    def begin(self):
        if self.boards:
            self.start_game(self.boards[self.index], self.auto)

    def handle_event(self, event):
        if self.button.handle_event(event):
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_RIGHT) and self.boards:
                self.index = (self.index + (1 if event.key == pygame.K_RIGHT else -1)) % len(self.boards)
            elif event.key == pygame.K_m:
                self.auto = not self.auto
            elif event.key == pygame.K_RETURN:
                self.begin()

    def update(self, delta):
        pass

    def draw(self, screen):
        screen.fill(COLORS["background"])
        panel = pygame.Rect(280, 120, 720, 520)
        draw_panel(screen, panel)
        screen.blit(label(self.font, "Mundo de Wumpus"), (420, 190))
        board = self.boards[self.index].name if self.boards else "No hay tableros"
        screen.blit(label(self.small, f"Tablero: {board} (←/→)"), (430, 300))
        screen.blit(label(self.small, f"Modo: {'Agente automático' if self.auto else 'Manual'} (M)"), (430, 350))
        self.button.draw(screen)
