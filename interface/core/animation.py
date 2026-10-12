from dataclasses import dataclass


@dataclass
class Animation:
    name: str
    duration: float
    elapsed: float = 0.0

    @property
    def finished(self) -> bool:
        return self.elapsed >= self.duration

    def update(self, delta: float) -> None:
        self.elapsed += delta


class AnimationQueue:
    """Runs visual event names in order before allowing another turn."""

    def __init__(self):
        self.items: list[Animation] = []

    @property
    def busy(self) -> bool:
        return bool(self.items)

    def enqueue(self, names: list[str]) -> None:
        self.items.extend(Animation(name, 0.22) for name in names)

    def update(self, delta: float) -> None:
        if not self.items:
            return
        self.items[0].update(delta)
        if self.items[0].finished:
            self.items.pop(0)

    @property
    def current(self) -> str | None:
        return self.items[0].name if self.items else None
