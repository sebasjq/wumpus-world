import logging
from pathlib import Path

import pygame

LOGGER = logging.getLogger(__name__)


class AssetLoader:
    """Loads optional assets and returns safe placeholders when absent."""

    def __init__(self, root: Path):
        self.root = root
        self.images = {}
        self.sounds = {}
        self.fonts = {}

    def image(self, relative: str, size: tuple[int, int], color=(120, 85, 48)) -> pygame.Surface:
        key = (relative, size)
        if key in self.images:
            return self.images[key]
        path = self.root / relative
        try:
            surface = pygame.image.load(path)
            if pygame.display.get_surface() is not None:
                surface = surface.convert_alpha()
            surface = pygame.transform.smoothscale(surface, size)
        except (FileNotFoundError, pygame.error, OSError) as error:
            LOGGER.warning("Could not load image %s: %s; using placeholder", path, error)
            surface = pygame.Surface(size, pygame.SRCALPHA)
            surface.fill(color)
            pygame.draw.rect(surface, (30, 20, 15), surface.get_rect(), 2)
        self.images[key] = surface
        return surface

    def sound(self, relative: str) -> pygame.mixer.Sound | None:
        if relative in self.sounds:
            return self.sounds[relative]
        try:
            sound = pygame.mixer.Sound(self.root / relative)
        except (FileNotFoundError, pygame.error, OSError) as error:
            LOGGER.warning("Could not load sound %s: %s; sound disabled: %s", self.root / relative, error)
            sound = None
        self.sounds[relative] = sound
        return sound

    def font(self, relative: str | None, size: int) -> pygame.font.Font:
        key = (relative, size)
        if key in self.fonts:
            return self.fonts[key]
        try:
            font = pygame.font.Font(self.root / relative, size) if relative else pygame.font.Font(None, size)
        except (FileNotFoundError, pygame.error, OSError) as error:
            LOGGER.warning("Could not load font %s: %s; using system font: %s", relative, error)
            font = pygame.font.Font(None, size)
        self.fonts[key] = font
        return font

    def spritesheet(self, relative: str, frame_size: tuple[int, int], count: int) -> list[pygame.Surface]:
        sheet = self.image(relative, (frame_size[0] * count, frame_size[1]))
        return [sheet.subsurface((index * frame_size[0], 0, *frame_size)).copy() for index in range(count)]
