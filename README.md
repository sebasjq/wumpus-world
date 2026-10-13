# Wumpus World

Proyecto de Inteligencia Artificial de Ingeniería en Multimedia, Universidad Militar Nueva Granada. Pedro explora una cueva, deduce cuáles casillas son seguras, recoge oro y vuelve a la entrada. Puede retirarse si no encuentra cómo continuar o morir al tomar un riesgo.

## Ejecución

Se usa Python 3.12 en la revisión. La lógica utiliza únicamente la biblioteca
estándar; la vista previa usa Pygame-CE.

Desde la raíz del repositorio:

```bash
python main.py
python -m unittest discover -s tests -p '*.py' -v
```

`main.py` inicia la interfaz gráfica. También puede iniciarse con
`python -m interface.app`.

## Organización

| Archivo o carpeta | Función |
|---|---|
| [logic/](logic/README.md) | Reglas del mundo, decisiones, búsqueda y controlador `Game`. |
| [data/](data/README.md) | Tableros en JSON. |
| [interface/](interface/README.md) | Interfaz Pygame, navegación, widgets, audio y recursos organizados por tipo. |
| [tests/](tests/README.md) | Pruebas y simulaciones reproducibles. |
| [docs/](docs/README.md) | Contrato para la interfaz e informe de revisión. |
| `main.py` | Inicia la interfaz y conecta sus acciones con `Game`. |
| `requirements.txt` | Dependencias externas de la vista previa. |
| `.gitignore` | Evita subir cachés, entornos virtuales y archivos temporales. |

## Reglas generales

Se utilizan coordenadas `[x, y]` desde 1; el norte aumenta `y`. Pedro percibe brisa, hedor, brillo, golpe y grito. Primero explora casillas seguras; después intenta disparar a Wumpus confirmados y, si está permitido, entrar a casillas inciertas. Finalmente regresa y sale por la entrada.

La puntuación es `1000 × oro - acciones - 10 × disparos - 1000 si muere`. BFS busca rutas con menos desplazamientos entre casillas conocidas, sin incluir el costo de los giros en la búsqueda.

## Integrantes

- Juan Sebastián Sánchez Quimbaya.
- Simón Tomás Paipa Bravo.
