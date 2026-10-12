import logging

import pygame

from .asset_loader import AssetLoader

LOGGER = logging.getLogger(__name__)


class AudioManager:
    def __init__(self, assets: AssetLoader):
        self.assets = assets
        self.muted = False
        self.enabled = False
        try:
            pygame.mixer.init()
            self.enabled = True
        except pygame.error as error:
            LOGGER.warning("Audio unavailable: %s", error)

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        return self.muted

    def play(self, relative: str) -> None:
        if self.enabled and not self.muted:
            sound = self.assets.sound(relative)
            if sound:
                sound.play()

    def stop(self) -> None:
        if self.enabled:
            pygame.mixer.stop()
