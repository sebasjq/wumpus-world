import pygame

from ..config import ASSET_ROOT, COLORS
from ..core.asset_loader import AssetLoader


class BoardRenderer:
    """Builds the board background from the 16x16 tile assets."""

    def __init__(self, area: pygame.Rect, assets: AssetLoader | None = None):
        self.area = area
        self.assets = assets or AssetLoader(ASSET_ROOT)

    def geometry(self, board_size: tuple[int, int]) -> tuple[int, int, int, int]:
        width, height = board_size
        cell = max(1, min(self.area.width // width, self.area.height // height))
        origin_x = self.area.centerx - cell * width // 2
        origin_y = self.area.centery - cell * height // 2
        return origin_x, origin_y, cell, cell

    def cell_rect(self, position, board_size) -> pygame.Rect:
        x, y, cell_w, cell_h = self.geometry(board_size)
        col, row = position[0] - 1, board_size[1] - position[1]
        return pygame.Rect(x + col * cell_w, y + row * cell_h, cell_w, cell_h)

    def draw(self, surface, state) -> None:
        board_size = tuple(state["board_size"])
        for x in range(1, board_size[0] + 1):
            for y in range(1, board_size[1] + 1):
                rect = self.cell_rect((x, y), board_size)
                pygame.draw.rect(surface, COLORS["background"], rect)
                wall_path = self._wall_tile(x, y, board_size)
                if wall_path:
                    self._draw_tile(surface, wall_path, rect)

    def _draw_tile(self, surface, path: str, rect: pygame.Rect) -> None:
        tile = self.assets.image(path, rect.size, COLORS["parchment_dark"])
        surface.blit(tile, rect)

    def _wall_tile(self, x: int, y: int, board_size) -> str | None:
        width, height = board_size
        if y == height and x == 1:
            return "images/tiles/wall/corners/top-left.png"
        if y == height and x == width:
            return "images/tiles/wall/corners/top-right.png"
        if y == height:
            variants = ("top-1.png", "top-2.png", "top-3.png", "top-4.png", "top-5.png")
            return f"images/tiles/wall/edges/{variants[(x - 2) % len(variants)]}"
        if y == 1 and x == 1:
            return "images/tiles/wall/corners/bottom-left.png"
        if y == 1 and x == width:
            return "images/tiles/wall/corners/bottom-right.png"
        if y == 1:
            variants = ("bottom-1.png", "bottom-2.png", "bottom-3.png", "bottom-4.png")
            return f"images/tiles/wall/edges/{variants[(x - 2) % len(variants)]}"
        if x == 1:
            return "images/tiles/wall/edges/left.png"
        if x == width:
            return "images/tiles/wall/edges/right.png"
        return None
