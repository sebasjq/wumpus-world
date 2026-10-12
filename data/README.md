# Tableros

Cada JSON describe el mundo real. Pedro conoce el tamaño, la entrada, su dirección y el total de oro, pero deduce la ubicación de los peligros mediante percepciones.

| Archivo | Para qué sirve |
|---|---|
| `board_4x4.json` | Ejemplo pequeño: un oro, un Wumpus y tres pozos. |
| `board_16x16.json` | Ejemplo grande: 37 oros, nueve Wumpus y 11 pozos. |
| `board_shoot_test.json` | Oro en la casilla del Wumpus: permite comprobar el disparo y la recogida posterior. |
| `board_no_safe_path_test.json` | Pozos en ambos vecinos de la entrada: permite comprobar retirada o muerte con riesgo. El nombre no significa que produzca el estado `blocked`. |

## Formato

```json
{
  "board_size": [3, 2],
  "initial_position": [1, 1],
  "direction": "E",
  "gold": [[3, 2]],
  "wumpus": [[2, 2]],
  "pits": [[3, 1]]
}
```

`board_size` es `[ancho, alto]`. Las posiciones son `[x,y]` con enteros desde 1. Las direcciones válidas iniciales del agente son `N`, `E`, `S` y `W`. Las listas pueden estar vacías y no admiten posiciones repetidas dentro de una misma lista.

La entrada no puede contener peligros. Sí se permiten elementos distintos en la misma casilla: matar un Wumpus no elimina un pozo que también esté allí. Un tablero válido puede ser imposible de resolver; la validación comprueba el formato, no garantiza alcanzar todo el oro.

Las flechas y el riesgo se configuran en `Game`, no en el JSON.
