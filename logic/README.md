# Lógica del juego

Esta carpeta separa lo que realmente hay en la cueva de lo que Pedro conoce.

| Archivo | Qué hace |
|---|---|
| `environment.py` | Carga y valida el JSON, produce las percepciones y ejecuta acciones. Actualiza oro, flechas, muerte, salida y puntuación. |
| `agent.py` | Guarda percepciones, casillas visitadas y peligros posibles o confirmados. Decide qué acción realizar usando ese conocimiento. |
| `search.py` | Implementa BFS: devuelve `(camino, distancia)` entre casillas seguras. Devuelve `None` si están desconectadas y rechaza extremos que no sean seguros. |
| `game.py` | Coordina entorno y agente, ejecuta un paso y entrega el estado para la interfaz. |
| `__init__.py` | Identifica la carpeta como un paquete de Python. |

## Cómo decide Pedro

`perceive()` registra la percepción y llama a `update_knowledge()`. Si no hay brisa, los vecinos no tienen pozos. Si no hay hedor, no hay Wumpus en la casilla ni en sus vecinos. Una casilla solo se deduce segura al descartar ambos peligros o saber que el Wumpus murió y no existe pozo.

Ejemplo: si en `[1,1]` no hay brisa ni hedor, `[1,2]` y `[2,1]` son seguras. Si hay brisa y únicamente un vecino sigue siendo candidato, ese vecino se confirma como pozo.

`decide()` prioriza regresar si terminó de recoger oro o decidió retirarse. En los demás casos: recoge oro visible, explora la casilla segura pendiente más cercana, intenta disparar, considera un riesgo y, si no puede seguir, regresa.

`move_action()` convierte el destino en un giro o avance; `shoot_action()` busca desde dónde apuntar; `get_shot_path()` calcula la trayectoria; `risk_action()` evita peligros confirmados; `return_action()` busca el camino a la entrada. Estos métodos eligen acciones; el entorno las ejecuta.

## Uso de Game

```python
from logic.game import Game

game = Game('data/board_shoot_test.json', allow_risk=False, arrows=2)
state = game.get_state()  # Consulta sin avanzar.
state = game.step()       # Ejecuta una acción y actualiza percepciones.
state = game.set_risk(True)
state = game.reset()      # Repone tablero y flechas iniciales.
```

`arrows=0` desactiva los disparos. Los detalles de cada dato y de los estados finales están en [GAME_API.md](../docs/GAME_API.md).
