# Interfaz gráfica

La interfaz se implementa con Pygame-CE y no necesita imágenes ni fuentes
externas. `Game` sigue siendo la fuente de verdad: el modo manual utiliza
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
