from pathlib import Path
from logic.environment import Environment
from logic.agent import Agent

board_path = Path(__file__).resolve().parent / "data" / "board_4x4.json"

environment = Environment(board_path)

pedro = Agent(
    initial_position=environment.initial_position,
    total_gold=environment.total_gold,
    board_size=environment.board_size,
    direction=environment.initial_direction
)

print("Tamaño:", environment.board_size)
print("Oro:", environment.gold)
print("Wumpus:", environment.wumpus)
print("Hoyos:", environment.pits)
print("Posición de Pedro:", pedro.position)