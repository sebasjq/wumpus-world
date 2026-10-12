# Interfaz Pygame-CE

Desde la raíz del proyecto:

```bash
pip install -r requirements.txt
python -m interface.app
```

Actualmente `interface.app` es una vista previa estática del mapa 16×16. La
ventana es cuadrada, tiene fondo negro y centra el mapa sin paneles laterales.
No importa ni ejecuta `logic`, no crea una partida y no procesa acciones del
juego. `F1` únicamente silencia o reactiva el audio de la vista previa.

El interior del mapa queda completamente negro. El perímetro usa los recursos necesarios de `images/tiles/wall/`, organizados
en `corners/` y `edges/`. Los bordes superior e inferior conservan sus
variantes originales y se alternan para mantener el diseño de la cueva. Los
tiles de piso no se usan en esta versión.

`core/` contiene la carga tolerante de recursos, audio, escenas y animaciones.
`render/` separa coordenadas del tablero de coordenadas de pantalla.
`scenes/` contiene las escenas preparadas para una futura conexión, pero no se
usan durante esta vista previa.
