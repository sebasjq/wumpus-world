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
        
        self.validate_board(board)  # Valida la estructura y los valores del tablero cargado
        self.board_size = tuple(board["board_size"])  # Tamaño del tablero (ancho, alto)

        self.initial_position = tuple(board["initial_position"])  # Posición inicial del agente
        self.initial_direction = board["direction"]  # Dirección inicial del agente

        self.gold = {tuple(position) for position in board["gold"]}  # Conjunto de posiciones de oro
        self.wumpus = {tuple(position) for position in board["wumpus"]}  # Conjunto de posiciones del Wumpus
        self.pits = {tuple(position) for position in board["pits"]}  # Conjunto de posiciones de pozos

        self.bump = False  # Indica si el agente ha chocado con una pared
        self.scream = False  # Indica si el Wumpus ha sido asesinado

        self.total_gold = len(self.gold)  # Total de oro en el tablero

        self.dead_wumpus = set()  # Conjunto de posiciones de Wumpus muertos (inicialmente vacío)

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
            "scream": self.scream
        }

    # Método para ejecutar una acción del agente y actualizar el estado 
    # del entorno en consecuencia.
    def execute_action(self, agent, action):

         # Si el agente no está vivo o ha salido del 
         # tablero, no puede ejecutar acciones...
        if not agent.alive or agent.exited:
            return  

        valid_actions = ["TURN_LEFT", "TURN_RIGHT", "FORWARD", "GRAB", "SHOOT", "CLIMB"]

        if action not in valid_actions:
            raise ValueError(f"Invalid action: {action}")
        
        self.bump = False  # Reinicia el golpe para la nueva acción.
        self.scream = False  # Reinicia el grito para la nueva acción.

        agent.action_count += 1  # Incrementa el contador de acciones del agente
        agent.score -= 1  # Penaliza al agente por cada acción realizada

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

            if (
                next_position in self.pits 
                or (
                    next_position in self.wumpus
                    and next_position not in self.dead_wumpus
                )
            ):
                # Ahora Pedro muere si cae en un pozo, aunque tambien haya un Wumpus 
                # muerto, o si cae en un Wumpus vivo
                agent.alive = False
                agent.score -= 1000 # Penalizacion por morir

        elif action == "GRAB":
            if agent.position in self.gold:
                self.gold.remove(agent.position)  # Elimina el oro de la celda
                agent.collected_gold += 1  # Incrementa el contador de oro recolectado del agente
                agent.score += 1000  # Recompensa por recolectar oro

        elif action == "SHOOT":

            if agent.arrows <= 0:
                return  # No hay flechas para disparar

            agent.arrows -= 1  # Disminuye el número de flechas del agente
            agent.shots_fired += 1  # Incrementa el contador de disparos realizados por el agente
            agent.score -= 10  # Penaliza al agente por disparar una flecha

            movements = {
                'N': (0, 1),  # Movimiento hacia el norte / arriba
                'E': (1, 0),  # Movimiento hacia el este / derecha
                'S': (0, -1), # Movimiento hacia el sur / abajo
                'W': (-1, 0)  # Movimiento hacia el oeste / izquierda
            }

            x, y = agent.position
            dx, dy = movements[agent.direction]
            width, height = self.board_size

            # La flecha comienza en la casilla que está delante de Pedro
            x = x + dx
            y = y + dy

            while 1 <= x <= width and 1 <= y <= height:  # Mientras la flecha esté dentro del tablero

                arrow_position = (x, y)

                if (arrow_position in self.wumpus and arrow_position not in self.dead_wumpus):  # Si la flecha alcanza al Wumpus y este no está muerto
                    self.dead_wumpus.add(arrow_position)  # Marca al Wumpus como muerto
                    self.scream = True  # Indica que el Wumpus ha sido asesinado
                    break  # La flecha se detiene después de matar un Wumpus vivo

                x = x + dx
                y = y + dy

        elif action == "CLIMB":
            if agent.position == self.initial_position:
                agent.exited = True  # Indica que el agente ha salido del tablero

    def validate_board(self, board):
        if not isinstance(board, dict):
            raise ValueError("El tablero debe ser un objeto JSON.")

        required_fields = {
            "board_size", "initial_position",
            "direction", "gold", "wumpus", "pits"
        }

        missing_fields = required_fields - board.keys()

        if missing_fields:
            raise ValueError(
                f"Faltan campos: {', '.join(sorted(missing_fields))}"
            )

        # Tamaño: dos enteros positivos
        size = board["board_size"]

        if (
            not isinstance(size, list)
            or len(size) != 2
            or any(type(value) is not int or value <= 0 for value in size)
        ):
            raise ValueError(
                "board_size debe contener dos enteros positivos."
            )

        width, height = size

        if board["direction"] not in ("N", "E", "S", "W"):
            raise ValueError("direction debe ser N, E, S o W.")

        # Comprueba el formato y los límites de una coordenada
        def validate_position(position, field):
            if (
                not isinstance(position, list)
                or len(position) != 2
                or any(type(value) is not int for value in position)
            ):
                raise ValueError(
                    f"{field}: cada posición debe contener dos enteros."
                )

            x, y = position

            if not (1 <= x <= width and 1 <= y <= height):
                raise ValueError(
                    f"{field}: la posición {position} está fuera del tablero."
                )

        validate_position(board["initial_position"], "initial_position")

        for field in ("gold", "wumpus", "pits"):
            positions = board[field]

            if not isinstance(positions, list):
                raise ValueError(f"{field} debe ser una lista de posiciones.")

            seen = set()

            for position in positions:
                validate_position(position, field)
                cell = tuple(position)

                if cell in seen:
                    raise ValueError(
                        f"{field}: la posición {position} está repetida."
                    )

                seen.add(cell)

        # El agente comienza en una casilla segura
        initial_position = board["initial_position"]

        if (
            initial_position in board["pits"]
            or initial_position in board["wumpus"]
        ):
            raise ValueError(
                "La posición inicial no puede contener pozos ni Wumpus."
            )