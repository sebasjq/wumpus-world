import pygame

from ..config import ASSET_ROOT, AUTO_DELAY, BOARD_AREA, COLORS, MAX_AUTO_DELAY, MIN_AUTO_DELAY, PANEL_AREA
from ..core.animation import AnimationQueue
from ..core.asset_loader import AssetLoader
from ..core.scene import Scene
from ..render.board_renderer import BoardRenderer
from ..ui.hud import draw_hud
from ..ui.knowledge_panel import draw_knowledge
from ..ui.theme import draw_panel, label


class GameAdapter:
    """Connects the UI to the existing Game controller without game rules."""

    def __init__(self, game):
        self.game = game
        self.state = game.get_state()

    def automatic_step(self):
        previous = self.state
        self.state = self.game.step()
        return previous, self.state

    def manual_action(self, action):
        if self.state["status"] != "running":
            return self.state, self.state
        previous = self.state
        self.game.last_action = action
        self.game.environment.execute_action(self.game.agent, action)
        self.game.update_perception()
        if not self.game.agent.alive:
            self.game.status = "dead"
        elif self.game.agent.exited:
            self.game.status = (
                "success"
                if self.game.agent.collected_gold == self.game.agent.total_gold
                else "retreated"
            )
        self.state = self.game.get_state()
        return previous, self.state

    def reset(self):
        self.state = self.game.reset()


class GameScene(Scene):
    def __init__(self, manager, adapter, automatic, show_result, assets=None):
        super().__init__(manager)
        self.adapter = adapter
        self.automatic = automatic
        self.paused = False
        self.auto_delay = AUTO_DELAY
        self.elapsed = 0.0
        self.queue = AnimationQueue()
        self.renderer = BoardRenderer(BOARD_AREA, assets or AssetLoader(ASSET_ROOT))
        self.font = pygame.font.Font(None, 30)
        self.small = pygame.font.Font(None, 22)
        self.show_result = show_result

    def _events(self, previous, current):
        events = []
        action = current.get("last_action")
        if action == "FORWARD":
            events.append("move")
        elif action in ("TURN_LEFT", "TURN_RIGHT"):
            events.append("turn")
        elif action == "SHOOT":
            events.extend(("shoot", "scream") if current["perception"] and current["perception"].get("scream") else ("shoot",))
        if previous["agent"]["alive"] and not current["agent"]["alive"]:
            events.append("death")
        if previous["agent"]["collected_gold"] < current["agent"]["collected_gold"]:
            events.append("gold")
        return events

    def _advance(self):
        if self.queue.busy or self.paused or self.adapter.state["status"] != "running":
            return
        previous, current = (
            self.adapter.automatic_step() if self.automatic
            else self.adapter.manual_action("FORWARD")
        )
        self.queue.enqueue(self._events(previous, current))
        if current["status"] != "running" and not self.queue.busy:
            self.show_result(current)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.paused = not self.paused
            elif event.key == pygame.K_r:
                self.adapter.reset()
                self.queue.items.clear()
            elif event.key == pygame.K_m:
                self.automatic = not self.automatic
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.auto_delay = min(MAX_AUTO_DELAY, self.auto_delay + 0.1)
            elif event.key in (pygame.K_EQUALS, pygame.K_KP_PLUS):
                self.auto_delay = max(MIN_AUTO_DELAY, self.auto_delay - 0.1)
            elif not self.automatic and not self.queue.busy and event.key in {
                pygame.K_LEFT: "TURN_LEFT", pygame.K_RIGHT: "TURN_RIGHT",
                pygame.K_UP: "FORWARD", pygame.K_g: "GRAB",
                pygame.K_f: "SHOOT", pygame.K_c: "CLIMB",
            }:
                previous, current = self.adapter.manual_action({
                    pygame.K_LEFT: "TURN_LEFT", pygame.K_RIGHT: "TURN_RIGHT",
                    pygame.K_UP: "FORWARD", pygame.K_g: "GRAB",
                    pygame.K_f: "SHOOT", pygame.K_c: "CLIMB",
                }[event.key])
                self.queue.enqueue(self._events(previous, current))

    def update(self, delta):
        self.queue.update(delta)
        if self.queue.busy:
            return
        self.elapsed += delta
        if self.automatic and self.elapsed >= self.auto_delay:
            self.elapsed = 0
            self._advance()
        elif self.adapter.state["status"] != "running":
            self.show_result(self.adapter.state)

    def draw(self, screen):
        screen.fill(COLORS["background"])
        draw_panel(screen, pygame.Rect(12, 8, 1256, 52))
        draw_hud(screen, self.adapter.state, self.font, self.small, "SPACE pausa | M modo | R reinicia | +/- velocidad | Mute: F1")
        self.renderer.draw(screen, self.adapter.state)
        draw_knowledge(screen, self.adapter.state, PANEL_AREA, self.font, self.small)
        if self.paused:
            screen.blit(label(self.font, "PAUSA"), (BOARD_AREA.centerx - 45, BOARD_AREA.centery))
        if self.queue.current:
            screen.blit(label(self.small, f"Animación: {self.queue.current}"), (PANEL_AREA.x + 15, PANEL_AREA.bottom - 34))
