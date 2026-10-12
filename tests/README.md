# Pruebas y simulaciones

| Archivo | Qué verifica |
|---|---|
| `tests_logic.py` | Reglas del entorno, conocimiento, BFS, acciones, peligros y puntuación. |
| `test_game.py` | Respuestas de `Game`, estados finales, reinicio, opciones y compatibilidad con JSON. |

Desde la raíz:

```bash
python -m unittest discover -s tests -p '*.py' -v
```

El  comando ejecuta 28 pruebas. El patrón `*.py` incluye ambos archivos de pruebas.

En cada simulación se comprueban puntuación, munición, conservación del oro, percepciones, límites y veracidad de las casillas seguras y peligros confirmados. También se comprueba que consultar no avance, que reiniciar reponga el estado y que una partida terminada no ejecute más acciones.

Una muerte con riesgo activado o una retirada con oro pendiente pueden ser resultados correctos. Pasar las comprobaciones significa que la lógica respetó las reglas durante esos casos; no garantiza ganar cualquier tablero ni verifica una interfaz gráfica todavía inexistente.