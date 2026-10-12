# Game para la interfaz

`Game` controla una partida automática. Sus métodos devuelven un diccionario compatible con JSON. No inicia un servidor ni conecta JavaScript por sí solo.

## Métodos

| Método | Uso |
|---|---|
| `Game(board_path, allow_risk=False, arrows=1)` | Crear partida y recibir la percepción inicial. |
| `get_state()` | Consultar sin ejecutar acciones ni borrar eventos. |
| `step()` | Pedir una decisión, ejecutar una acción y devolver el estado actualizado. Si terminó, devuelve el estado final sin avanzar. |
| `set_risk(True/False)` | Cambiar riesgo sin ejecutar una acción. Conserva la opción al reiniciar. |
| `reset()` | Volver a cargar el JSON y reponer agente, oro, Wumpus, flechas y contadores. |

`arrows` debe ser un entero no negativo; `allow_risk`, un booleano. Para cambiar el tablero o la cantidad inicial de flechas, crear otra instancia. No existe un método para editar la munición durante la partida.

Ejemplo desde la raíz, dentro de Python:

```python
from logic.game import Game

enabled = False
amount = 3
risk = True

game = Game('data/board_4x4.json',
            allow_risk=risk, arrows=amount if enabled else 0)
state = game.get_state()
while state['status'] == 'running':
    state = game.step()
    # Enviar cada state a la interfaz mediante la conexión elegida.
```

## Datos para dibujar

| Campo | Qué permite mostrar |
|---|---|
| `board_size`, `initial_position` | Dimensiones y entrada. |
| `status`, `last_action`, `allow_risk` | Resultado, última acción y opción de riesgo. |
| `agent.position`, `agent.direction` | Casilla y orientación: N arriba, E derecha, S abajo, W izquierda. |
| `agent.alive`, `agent.exited`, `agent.returning_home` | Vida, salida y decisión de regresar. |
| `agent.arrows`, `agent.shots_fired` | Munición disponible y disparos realizados. |
| `agent.collected_gold`, `agent.total_gold`, `agent.remaining_gold` | Oro recogido, total y pendiente. |
| `agent.score`, `agent.action_count` | Puntuación y acciones ejecutadas, incluidos giros. |
| `perception` | `breeze`, `stench`, `glitter`, `bump` y `scream` de la posición actual. |
| `knowledge.visited`, `knowledge.safe_cells` | Casillas visitadas y seguras conocidas. |
| `knowledge.possible_pits`, `knowledge.confirmed_pits` | Pozos sospechados y confirmados. |
| `knowledge.possible_wumpus`, `knowledge.confirmed_wumpus` | Wumpus sospechados y confirmados; los confirmados pueden incluir muertos. |
| `knowledge.known_dead_wumpus` | Muertos cuya ubicación Pedro pudo deducir. |
| `world.gold`, `world.pits` | Oro restante y pozos reales. |
| `world.live_wumpus`, `world.dead_wumpus` | Wumpus reales separados por estado de vida. |

Las coordenadas son listas `[x,y]`, desde 1. Para una cuadrícula HTML con filas desde arriba: `columna=x-1` y `fila=alto-y`.

`perception` es `None` al morir o salir. El grito y el golpe duran hasta la siguiente acción; consultar no los borra. Leer `last_action` permite animar un giro aunque la posición siga igual. No se entrega un historial de acciones ni de percepciones por casilla: si se desea, la interfaz debe guardar las respuestas.

Para mostrar brisa y hedor en todo el tablero, derivarlos de `world`: brisa en vecinos directos de pozos; hedor en la casilla y vecinos de todos los Wumpus, incluidos muertos. El brillo corresponde al oro restante. Golpe y grito son eventos, no marcas permanentes del mapa.

## Finales y opciones

| `status` | Interpretación |
|---|---|
| `running` | Continúa. |
| `success` | Salió vivo con todo el oro. |
| `retreated` | Salió vivo con oro pendiente. |
| `dead` | Murió en un pozo o ante un Wumpus vivo. |
| `blocked` | No encuentra ruta segura de regreso. |

No existe `death_cause`: para mostrar la causa, comparar `agent.position` con `world.pits` y `world.live_wumpus`; pueden coincidir ambos peligros.

Activar riesgo permite considerar casillas inciertas; no garantiza sobrevivir. Si Pedro ya decidió retirarse (`returning_home=True`), cambiar riesgo no cancela el regreso. Después de un final, reiniciar o crear otra partida para jugar de nuevo.