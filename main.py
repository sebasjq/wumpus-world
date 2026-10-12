from pathlib import Path
from logic.environment import Environment
from logic.agent import Agent

board_path = (
    Path(__file__).resolve().parent 
    / "data" 
    / "board_16x16.json")

environment = Environment(board_path)

pedro = Agent(
    initial_position=environment.initial_position,
    total_gold=environment.total_gold,
    board_size=environment.board_size,
    direction=environment.initial_direction,
    arrows=1,
    allow_risk=False  # Permitir que Pedro tome riesgos al moverse hacia celdas inciertas
)

while True:

    # Percibir y actualizar el conocimiento
    if pedro.alive and not pedro.exited:
        neighbors = pedro.get_neighbors(pedro.position)
        perception = environment.get_perception(pedro.position, neighbors)
        pedro.perceive(perception)

        print(
            f"\nPosición: {pedro.position} | "
            f"Dirección: {pedro.direction}"
        )
        print("Percepción:", perception)

    # Elegir la siguiente acción
    action = pedro.decide()
    print("Acción:", action)

    # Estos estados no son acciones del entorno
    if action == "DEAD":
        print("Pedro ha muerto.")
        break

    if action == "NO_SAFE_PATH":
        print("Pedro no encuentra una ruta segura de regreso.")
        break

    if action == "EXITED":
        print("Pedro ya ha salido de la cueva.")
        break

    # Ejecutar una sola vez y mostrar el resultado
    environment.execute_action(pedro, action)

    print(
        f"Flechas: {pedro.arrows} | "
        f"Oro: {pedro.collected_gold}/{pedro.total_gold} | "
        f"Puntuación: {pedro.score}"
    )

    if pedro.exited:
        if pedro.collected_gold == pedro.total_gold:
            print("Pedro ha salido con todo el oro.")
        else:
            print("Pedro se ha retirado con oro pendiente.")
        break

    if not pedro.alive:
        print(f"Pedro ha muerto en {pedro.position}.")
        break

# Resumen final
print("\nResultado final")
print("Posición:", pedro.position)
print(f"Oro recolectado: {pedro.collected_gold}/{pedro.total_gold}")
print("Oro pendiente:", pedro.total_gold - pedro.collected_gold)
print("¿Pedro sigue vivo?:", pedro.alive)
print("¿Pedro salió?:", pedro.exited)
print("Flechas restantes:", pedro.arrows)
print("Acciones ejecutadas:", pedro.action_count)
print("Disparos realizados:", pedro.shots_fired)
print("Puntuación:", pedro.score)