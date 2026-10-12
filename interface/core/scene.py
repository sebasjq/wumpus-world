from abc import ABC, abstractmethod

import pygame


class Scene(ABC):
    def __init__(self, manager):
        self.manager = manager

    @abstractmethod
    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    @abstractmethod
    def update(self, delta: float) -> None:
        pass

    @abstractmethod
    def draw(self, screen: pygame.Surface) -> None:
        pass


class SceneManager:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.scene: Scene | None = None

    def switch(self, scene: Scene) -> None:
        self.scene = scene

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.scene:
            self.scene.handle_event(event)

    def update(self, delta: float) -> None:
        if self.scene:
            self.scene.update(delta)

    def draw(self) -> None:
        if self.scene:
            self.scene.draw(self.screen)
