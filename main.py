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

while True:

    # Obtener las casillas vecinas de la posición actual del agente
    neighbors = pedro.get_neighbors(pedro.position)

    # Obtener las percepciones del entorno para la posición actual del agente
    # y actualiza el conocimiento de Pedro
    perception = environment.get_perception(pedro.position, neighbors)
    pedro.perceive(perception)

    # Decidir qué hacer usando su conocimiento
    action = pedro.decide()


    print("Posición actual:", pedro.position)
    print("Dirección:", pedro.direction)
    print("Percepción:", perception)
    print("Acción elegida:", action)
    print()

    # Comprobar si la ejecución debe terminar
    if action == "STOP":
        print("Pedro ha recolectado todo el oro y ha decidido detenerse.")
        break

    elif action == "DEAD":
        print("Pedro ha muerto. Fin de la ejecución.")
        break

    elif action == "NO_SAFE_PATH":
        print("Pedro no conoce una ruta segura para continuar. Fin de la ejecución.")
        break

    # Ejecutar la acción elegida por Pedro y actualizar el entorno
    # Vuelve a comenzar el ciclo
    environment.execute_action(pedro, action)