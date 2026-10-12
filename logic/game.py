from pathlib import Path

from logic.agent import Agent
from logic.environment import Environment


class Game:
    def __init__(self, board_path, allow_risk=False, arrows=1):
        self.board_path = Path(board_path)
        self.allow_risk = allow_risk
        self.initial_arrows = arrows

        self.reset()

    def reset(self):
        # Crea nuevamente el entorno y el agente
        self.environment = Environment(self.board_path)

        self.agent = Agent(
            initial_position=self.environment.initial_position,
            total_gold=self.environment.total_gold,
            board_size=self.environment.board_size,
            direction=self.environment.initial_direction,
            arrows=self.initial_arrows,
            allow_risk=self.allow_risk
        )

        self.status = "running"
        self.last_action = None

        self.update_perception()

        return self.get_state()

    def update_perception(self):
        # Obtiene lo que Pedro percibe en su posición actual
        neighbors = self.agent.get_neighbors(self.agent.position)

        self.perception = self.environment.get_perception(
            self.agent.position,
            neighbors
        )

        if self.agent.alive and not self.agent.exited:
            self.agent.perceive(self.perception.copy())

    def step(self):
        # Si terminó, conserva el estado final
        if self.status != "running":
            return self.get_state()

        # Pedro decide usando el conocimiento que ya recibió
        self.last_action = self.agent.decide()

        if self.last_action == "NO_SAFE_PATH":
            self.status = "blocked"

        elif self.last_action == "DEAD":
            self.status = "dead"

        elif self.last_action == "EXITED":
            if self.agent.collected_gold == self.agent.total_gold:
                self.status = "success"
            else:
                self.status = "retreated"

        else:
            # Ejecuta una sola acción
            self.environment.execute_action(
                self.agent,
                self.last_action
            )

            # Actualiza la percepción después de actuar
            self.update_perception()

            if not self.agent.alive:
                self.status = "dead"

            elif self.agent.exited:
                if self.agent.collected_gold == self.agent.total_gold:
                    self.status = "success"
                else:
                    self.status = "retreated"

        return self.get_state()

    def get_state(self):
        # Convierte conjuntos de coordenadas en listas para JSON
        def positions(cells):
            return [list(cell) for cell in sorted(cells)]

        return {
            "status": self.status,
            "last_action": self.last_action,
            "board_size": list(self.environment.board_size),
            "initial_position": list(self.environment.initial_position),
            "allow_risk": self.agent.allow_risk,

            "agent": {
                "position": list(self.agent.position),
                "direction": self.agent.direction,
                "alive": self.agent.alive,
                "exited": self.agent.exited,
                "returning_home": self.agent.returning_home,
                "arrows": self.agent.arrows,
                "collected_gold": self.agent.collected_gold,
                "total_gold": self.agent.total_gold,
                "remaining_gold": (
                    self.agent.total_gold - self.agent.collected_gold
                ),
                "action_count": self.agent.action_count,
                "shots_fired": self.agent.shots_fired,
                "score": self.agent.score
            },

            "perception": (
                self.perception.copy()
                if self.agent.alive and not self.agent.exited
                else None
            ),

            "knowledge": {
                "visited": positions(self.agent.visited),
                "safe_cells": positions(self.agent.safe_cells),
                "possible_pits": positions(self.agent.possible_pits),
                "confirmed_pits": positions(self.agent.confirmed_pits),
                "possible_wumpus": positions(self.agent.possible_wumpus),
                "confirmed_wumpus": positions(self.agent.confirmed_wumpus),
                "known_dead_wumpus": positions(self.agent.known_dead_wumpus)
            },

            # Posiciones reales para que la interfaz dibuje el tablero
            "world": {
                "gold": positions(self.environment.gold),
                "pits": positions(self.environment.pits),
                "live_wumpus": positions(self.environment.wumpus - self.environment.dead_wumpus),
                "dead_wumpus": positions(self.environment.dead_wumpus)
            }
        }