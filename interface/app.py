import logging
import json
from pathlib import Path

import pygame

from .config import ASSET_ROOT, BOARD_AREA, DATA_ROOT, FPS, SCREEN_SIZE, TITLE
from .core.asset_loader import AssetLoader
from .core.audio_manager import AudioManager
from .render.board_renderer import BoardRenderer

logging.basicConfig(level=logging.WARNING)


class Application:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.assets = AssetLoader(ASSET_ROOT)
        self.audio = AudioManager(self.assets)
        self.renderer = BoardRenderer(BOARD_AREA, self.assets)
        board = self._load_preview_board()
        self.state = {
            "board_size": [16, 16],
            "floor_specials": {
                "wumpus": board["wumpus"],
                "pits": board["pits"],
            },
            "knowledge": {
                "visited": [],
                "safe_cells": [],
                "possible_pits": [],
                "possible_wumpus": [],
            },
            "world": {
                "gold": [],
                "pits": [],
                "live_wumpus": [],
                "dead_wumpus": [],
            },
            "agent": {"position": [1, 1], "direction": "E"},
        }

    @staticmethod
    def _load_preview_board():
        with (DATA_ROOT / "board_16x16.json").open(encoding="utf-8") as file:
            return json.load(file)

    def run(self):
        running = True
        while running:
            delta = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
                    self.audio.toggle_mute()
            self.screen.fill((0, 0, 0))
            self.renderer.draw(self.screen, self.state)
            pygame.display.flip()
        self.audio.stop()
        pygame.quit()


def main():
    Application().run()


if __name__ == "__main__":
    main()
