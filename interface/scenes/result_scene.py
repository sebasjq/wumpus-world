import pygame

from ..config import COLORS
from ..core.scene import Scene
from ..ui.button import Button
from ..ui.theme import draw_panel, label


class ResultScene(Scene):
    def __init__(self, manager, state, restart):
        super().__init__(manager)
        self.state = state
        self.font = pygame.font.Font(None, 52)
        self.small = pygame.font.Font(None, 30)
        self.restart = Button((430, 520, 420, 60), "Volver al menú", self.small, restart)

    def handle_event(self, event):
        self.restart.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.restart.callback()

    def update(self, delta):
        pass

    def draw(self, screen):
        screen.fill(COLORS["background"])
        panel = pygame.Rect(280, 140, 720, 460)
        draw_panel(screen, panel)
        state = self.state
        screen.blit(label(self.font, state["status"].upper()), (500, 220))
        screen.blit(label(self.small, f"Puntaje: {state['agent']['score']}"), (500, 330))
        screen.blit(label(self.small, f"Oro: {state['agent']['collected_gold']}/{state['agent']['total_gold']}"), (500, 380))
        self.restart.draw(screen)
