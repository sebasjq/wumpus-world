'Audio de la interfaz: música, efectos y tonos de respaldo.'

from array import array
import math
from pathlib import Path

import pygame

ASSETS = Path(__file__).resolve().parent / "assets"


class SoundManager:
    """Gestiona efectos sintetizados y música opcional de la interfaz."""

    SAMPLE_RATE = 44100
    MUSIC_FADE_MS = 700
    MUSIC_FILES = {
        "pregame": ("Fondo1.mp3", "Fondo2.mp3"),
        "game": ("Partida.mp3",),
    }
    MUSIC_VOLUMES = {
        "pregame": 0.65,
        "game": 0.35,
    }
    SOUND_FILES = {
        "click": "Botón.mp3",
        "turn": "Turn.mp3",
        "move": "Move.mp3",
        "gold": "Gold.mp3",
        "shoot": "Shoot.mp3",
        "arrow_hit": "Arrow_hit.mp3",
        "pit_fall": "Pit_fall.mp3",
        "wumpus_growl": "Wumpus_growl.mp3",
        "wumpus_death": "Wumpus_death.mp3",
        "breeze": "Breeze.mp3",
        "stench": "Stench.mp3",
        "glitter": "Gold.mp3",
        "scream": "Scream.mp3",
        "bump": "Bump.mp3",
        "win": "Win.mp3",
        "lose": "Lose.mp3",
    }

    def __init__(self, music_enabled=True, effects_enabled=True):
        self.music_enabled = music_enabled
        self.effects_enabled = effects_enabled
        self.sounds = {}
        self.music_mode = None
        self.music_index = -1
        self.pending_music_mode = None
        self.mixer_ready = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=self.SAMPLE_RATE, size=-16, channels=1)
            self.mixer_ready = True
            fallback = {
                "click": self._tone(920, 1120, .065),
                "turn": self._tone(230, 180, .09),
                "move": self._tone(180, 280, .11),
                "gold": self._tone(520, 1040, .22),
                "shoot": self._tone(640, 120, .28),
                "arrow_hit": self._tone(180, 90, .18),
                "pit_fall": self._tone(240, 45, .7),
                "wumpus_growl": self._tone(115, 55, .65, harmonics=3),
                "wumpus_death": self._tone(420, 120, .5, harmonics=4),
                "breeze": self._tone(300, 520, .32, harmonics=2),
                "stench": self._tone(115, 75, .4, harmonics=3),
                "glitter": self._tone(880, 1320, .18),
                "scream": self._tone(420, 120, .5, harmonics=4),
                "bump": self._tone(90, 55, .16, harmonics=3),
                "win": self._tone(660, 1320, .5, harmonics=2),
                "lose": self._tone(180, 60, .55, harmonics=3),
            }
            self.sounds = {
                name: self._load_sound(filename) or fallback[name]
                for name, filename in self.SOUND_FILES.items()
            }
        except pygame.error:
            self.sounds = {}

    @staticmethod
    def _load_sound(filename):
        path = ASSETS / "audio" / filename
        if not path.exists():
            return None
        try:
            return pygame.mixer.Sound(str(path))
        except pygame.error:
            return None

    def _music_path(self, mode, index):
        files = self.MUSIC_FILES[mode]
        path = ASSETS / "audio" / files[index]
        return path if path.exists() else None

    def play_music(self, mode):
        """Cambia la música con fundido y volumen apropiado para cada escena."""
        if not self.mixer_ready or mode not in self.MUSIC_FILES:
            return
        if self.music_mode != mode and pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(self.MUSIC_FADE_MS)
            self.pending_music_mode = mode
            return
        self._start_music(mode)

    def _start_music(self, mode):
        self.pending_music_mode = None
        self.music_mode = mode
        self.music_index = -1
        self._next_music()

    def _next_music(self):
        if not self.mixer_ready:
            return
        if not self.music_enabled or self.music_mode is None:
            pygame.mixer.music.stop()
            return
        files = self.MUSIC_FILES[self.music_mode]
        for _ in range(len(files)):
            self.music_index = (self.music_index + 1) % len(files)
            path = self._music_path(self.music_mode, self.music_index)
            if path:
                try:
                    pygame.mixer.music.load(str(path))
                    pygame.mixer.music.set_volume(self.MUSIC_VOLUMES[self.music_mode])
                    pygame.mixer.music.play(fade_ms=self.MUSIC_FADE_MS)
                    return
                except pygame.error:
                    continue
        pygame.mixer.music.stop()

    def update(self):
        if (self.mixer_ready and self.pending_music_mode
                and not pygame.mixer.music.get_busy()):
            self._start_music(self.pending_music_mode)
        if (self.mixer_ready and self.music_enabled and self.music_mode
                and not pygame.mixer.music.get_busy()):
            self._next_music()

    def _tone(self, start, end, duration, harmonics=1):
        samples = int(self.SAMPLE_RATE * duration)
        audio = array("h")
        for i in range(samples):
            progress = i / max(1, samples - 1)
            frequency = start + (end - start) * progress
            envelope = min(1.0, i / (self.SAMPLE_RATE * .012))
            envelope *= min(1.0, (samples - i) / (self.SAMPLE_RATE * .035))
            value = sum(math.sin(2 * math.pi * frequency * harmonic * i / self.SAMPLE_RATE)
                        / harmonic for harmonic in range(1, harmonics + 1))
            audio.append(max(-32767, min(32767, int(value * 10500 * envelope / harmonics))))
        return pygame.mixer.Sound(buffer=audio.tobytes())

    def play(self, name):
        if self.effects_enabled and name in self.sounds:
            self.sounds[name].play()

    def set_music_enabled(self, enabled):
        self.music_enabled = enabled
        if not self.mixer_ready:
            return
        if enabled:
            if self.pending_music_mode:
                self._start_music(self.pending_music_mode)
            if self.music_mode:
                self._next_music()
        else:
            self.pending_music_mode = None
            pygame.mixer.music.fadeout(self.MUSIC_FADE_MS)

    def stop_music(self):
        """Detiene la música activa con una transición suave."""
        self.pending_music_mode = None
        self.music_mode = None
        if self.mixer_ready:
            pygame.mixer.music.fadeout(self.MUSIC_FADE_MS)

    def set_effects_enabled(self, enabled):
        self.effects_enabled = enabled

