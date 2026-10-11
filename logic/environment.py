import json

class Environment:

    # Método constructor de la clase Environment, que inicializa el entorno 
    # del juego a partir de un archivo JSON que describe el tablero y sus elementos.
    def __init__(self, board_path):

        # Se carga el archivo JSON que contiene la configuración del tablero, 
        # incluyendo el tamaño del tablero, la posición inicial del agente, 
        # la dirección inicial, las posiciones de oro, Wumpus y pozos.
        with open(board_path, "r", encoding="utf-8") as file:
            board = json.load(file)

        self.board_size = tuple(board["board_size"])  # Tamaño del tablero (ancho, alto)
        self.initial_position = tuple(board["initial_position"])  # Posición inicial del agente
        self.initial_direction = board["direction"]  # Dirección inicial del agente

        self.gold = {tuple(position) for position in board["gold"]}  # Conjunto de posiciones de oro
        self.wumpus = {tuple(position) for position in board["wumpus"]}  # Conjunto de posiciones del Wumpus
        self.pits = {tuple(position) for position in board["pits"]}  # Conjunto de posiciones de pozos

        self.bump = False  # Indica si el agente ha chocado con una pared

        self.total_gold = len(self.gold)  # Total de oro en el tablero

    # Método para obtener las percepciones del agente en una posición dada de acuerdo al entorno,
    # considerando las celdas vecinas y la presencia de oro, Wumpus y pozos.
    def get_perception(self, position, neighbors):

        # Se aprovecha el metodo de obtencion de vecinos para asignar 
        # las percepciones de brisa, hedor y brillo según la posición 
        # del agente y sus vecinos.
        return {
            "breeze": any(cell in self.pits for cell in neighbors),  # Hay brisa si hay un pozo en alguna celda vecina
            "stench": (
                position in self.wumpus # Hay hedor si el agente está en la misma celda que el Wumpus...
                or any(cell in self.wumpus for cell in neighbors) # ... o si hay un Wumpus en alguna celda vecina
            ),
            "glitter": position in self.gold,  # Hay brillo si el agente está en la misma celda que el oro
            "bump": self.bump,  # Indica si el agente ha chocado con una pared (se actualiza en execute_action)
            "scream": False  # Se inicializa como falso; se actualizará si el Wumpus es asesinado
        }

    # Método para ejecutar una acción del agente y actualizar el estado del entorno en consecuencia.
    def execute_action(self, agent, action):

        if not agent.alive:
            return  # Si el agente no está vivo, no se puede ejecutar ninguna acción

        self.bump = False  # Reinicia el golpe para la nueva acción.

        directions = ['N', 'E', 'S', 'W']  # Lista de direcciones en orden horario

        if action == "TURN_LEFT":
            index = directions.index(agent.direction)
            agent.direction = directions[(index - 1) % 4]  # Gira a la izquierda (sentido antihorario)

        elif action == "TURN_RIGHT":
            index = directions.index(agent.direction)
            agent.direction = directions[(index + 1) % 4]  # Gira a la derecha (sentido horario)

        elif action == "FORWARD":

            movements = {
                'N': (0, 1),  # Movimiento hacia el norte / arriba
                'E': (1, 0),  # Movimiento hacia el este / derecha
                'S': (0, -1), # Movimiento hacia el sur / abajo
                'W': (-1, 0)  # Movimiento hacia el oeste / izquierda
            }

            x, y = agent.position
            dx, dy = movements[agent.direction]
            next_position = (x + dx, y + dy) # Calcula la nueva posición del agente según su dirección actual y el movimiento correspondiente.

            width, height = self.board_size
            next_x, next_y = next_position

            if not (1 <= next_x <= width and 1 <= next_y <= height):  # Verifica si la nueva posición está dentro de los límites del tablero
                self.bump = True  
                return  # Choca y conserva su posición

            agent.position = next_position  # Actualiza la posición del agente si no choca

            if next_position in self.pits or next_position in self.wumpus:
                agent.alive = False # Muere por caer en un hoyo o entrar donde hay un Wumpus

        elif action == "GRAB":
            if agent.position in self.gold:
                self.gold.remove(agent.position)  # Elimina el oro de la celda
                agent.collected_gold += 1  # Incrementa el contador de oro recolectado del agente
