# Interfaz gráfica

La interfaz se implementa con Pygame-CE. Usa `Fondo.png` como fondo común de
todas las escenas y `Logo.png` como logotipo del menú; ambas imágenes deben
estar en este directorio. `Game` sigue siendo la fuente de verdad: el modo manual utiliza
`Game.act()` y el modo agente utiliza `Game.step()` de forma incremental dentro
del bucle principal.

Ejecuta desde la raíz del proyecto:

```bash
python main.py
```

Los cuatro mapas de `data/` aparecen en la pantalla de selección. En una
partida manual se puede usar el teclado (flechas, `G`, espacio y `C`) o los
botones visibles. `ESC` pausa; en modo agente también se puede avanzar un
paso con `PASO`.

La interfaz incluye efectos de sonido sintetizados para los botones, acciones
del explorador y percepciones: brisa, hedor, brillo, golpe y grito. Se pueden
activar o desactivar desde **Configuración > Sonidos**; si el dispositivo no
dispone de un mezclador compatible, el juego continúa funcionando sin audio.
Cada percepción activa del panel lateral funciona además como un botón para
escuchar nuevamente su sonido.

`Fondo1.mp3` se reproduce durante los menús antes de iniciar una partida.
`Partida.mp3` reemplaza esa música al comenzar el juego. El botón de la
interfaz utiliza `Botón.mp3`.
