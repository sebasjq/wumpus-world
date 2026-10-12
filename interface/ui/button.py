import pygame

from .theme import draw_panel, label


class Button:
    def __init__(self, rect, text, font, callback):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.callback = callback

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONUP and self.rect.collidepoint(event.pos):
            self.callback()
            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        draw_panel(surface, self.rect)
        text = label(self.font, self.text)
        surface.blit(text, text.get_rect(center=self.rect.center))
