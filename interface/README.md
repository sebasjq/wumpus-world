# Interfaz gráfica

La interfaz se implementa con Pygame-CE. Usa `Fondo.png` como fondo común de
todas las escenas y `Logo.png` como logotipo del menú; ambas imágenes deben
estar en este directorio. `Game` sigue siendo la fuente de verdad: el modo manual utiliza
`Game.act()` y el modo agente utiliza `Game.step()` de forma incremental dentro
del bucle principal.

La vista de juego utiliza también `Pozo_icon.png`, `Wumpus_icon.png`,
`Oro_icon.png`, `Flecha_icon.png`, `Cofre_icon.png` y `Corazon_icon.png`.
El explorador cuenta con cuatro sprites direccionales en
`assets/icons/explorer_N.png`, `explorer_E.png`, `explorer_S.png` y
`explorer_W.png`.

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

Los efectos de juego se cargan desde los MP3 de este directorio: `Turn.mp3`,
`Move.mp3`, `Gold.mp3`, `Shoot.mp3`, `Arrow_hit.mp3`, `Pit_fall.mp3`,
`Wumpus_growl.mp3`, `Wumpus_death.mp3`, `Breeze.mp3`, `Stench.mp3`,
`Scream.mp3`, `Bump.mp3`, `Win.mp3` y `Lose.mp3`.

`Fondo1.mp3` se reproduce durante los menús antes de iniciar una partida.
`Partida.mp3` reemplaza esa música al comenzar el juego. El botón de la
interfaz utiliza `Botón.mp3`.
