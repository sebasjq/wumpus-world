# Interfaz gráfica

La interfaz de Wumpus World está construida con Pygame-CE y mantiene una
separación clara entre la presentación y las reglas del juego. `Game` sigue
siendo la única fuente de verdad: el modo manual usa `Game.act()` y el modo
agente usa `Game.step()` de forma incremental dentro del bucle principal.

## Estructura

| Ruta | Responsabilidad |
| --- | --- |
| `app.py` | Punto de entrada compatible para `python -m interface.app`; reexporta `App` y `main`. |
| `application.py` | Estado de la aplicación, navegación entre pantallas, eventos, ciclo principal y escenas. |
| `rendering.py` | Paleta, constantes, tipografías, cachés, carga de imágenes y primitivas de dibujo. |
| `widgets.py` | `Button` y pequeños controles visuales reutilizables. |
| `audio.py` | `SoundManager`, música, efectos y tonos sintetizados de respaldo. |
| `assets/images/` | Fondos, logo e iconos grandes usados por la interfaz. |
| `assets/icons/` | Iconos pequeños y sprites direccionales. |
| `assets/audio/` | Música y efectos de sonido. |

Esta división evita que los recursos, los widgets y el audio queden mezclados
con la navegación de las pantallas. Para añadir una pantalla se trabaja en
`application.py`; para añadir una primitiva visual se trabaja en
`rendering.py`; y para un nuevo efecto se actualizan `SoundManager` y
`assets/audio/`.

## Recursos

Los recursos son opcionales en tiempo de ejecución siempre que exista un
reemplazo implementado. Si falta una fuente, Pygame usa una fuente del sistema;
si falta un mezclador compatible, la partida continúa sin audio. Los iconos
solicitados por la interfaz, en cambio, producen un error explícito si están
ausentes para evitar una pantalla aparentemente incompleta.

- `assets/images/Fondo.png`: fondo común de las escenas.
- `assets/images/Logo.png`: logotipo del menú y de la barra del juego.
- `assets/images/*_icon.png`: ilustraciones grandes de oro, pozos, Wumpus,
  flechas, cofres y vidas.
- `assets/icons/`: iconos de controles, percepciones, navegación y los cuatro
  sprites `explorer_N/E/S/W.png`.
- `assets/audio/`: música de menú (`Fondo1.mp3`, `Fondo2.mp3`), música de
  partida (`Partida.mp3`) y efectos de acciones y percepciones.

Los nombres de archivo se mantienen iguales dentro de cada categoría porque
forman parte del catálogo que consume `rendering.py` o `audio.py`.

## Ejecución

Desde la raíz del proyecto:

```bash
python main.py
python -m interface.app
```

Los cuatro mapas de `data/` aparecen en la selección. En una partida manual
se puede usar el teclado (flechas, `G`, espacio y `C`) o los botones visibles.
`ESC` pausa; en modo agente también se puede avanzar un paso con `PASO`.

La configuración se guarda en `settings.json`. Se pueden activar o desactivar
por separado la música, los efectos, la pantalla completa, las notas del mapa
y las coordenadas.
