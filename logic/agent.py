from logic.search import bfs # Importa la función bfs desde el módulo logic.search para realizar búsquedas en anchura (BFS) en el entorno del agente.

class Agent:
    # Constructor del agente, inicializa la posición, dirección, tamaño del tablero, 
    # estado de vida, oro recolectado y total de oro, celdas visitadas y seguras, y percepciones.
    def __init__(self, initial_position, total_gold, board_size, direction='E'):
        self.position = initial_position
        self.direction = direction
        self.board_size = board_size # Tamaño del tablero (ancho, alto) / (16, 16) por ejemplo

        self.alive = True

        self.collected_gold = 0
        self.total_gold = total_gold

        self.visited = set() # Conjunto de posiciones visitadas
        self.safe_cells = {initial_position} # Conjunto de celdas seguras
        self.perceptions = {} # Diccionario para almacenar percepciones para cada posición

    # Método para recibir percepciones del entorno y actualizar el conocimiento del agente.
    def perceive(self, perception):

        # Guarda lo que recibe del entorno...
        self.visited.add(self.position) # Marca la posición actual como visitada...
        # Al ejecutar pedro.visited --> {(1, 1)}

        self.perceptions[self.position] = perception # Guarda la percepción asociada a la posición actual...
        # Al ejecutar pedro.perceptions --> {(1, 1): {"breeze": False, "stench": False, "glitter": False, "bump": False, "scream": False}}

        self.update_knowledge() # Actualiza el conocimiento del agente basado en la percepción actual...

    # Método para decidir la acción a tomar basado en las percepciones y 
    # el conocimiento del agente / Consulta cúales de las casillas seguras quedan por explorar...
    def decide(self):
        # Comprobar primero si el agente completó el objetivo. En ese caso, se detiene...
        if self.collected_gold == self.total_gold:
            return "STOP"
    
        perception = self.perceptions[self.position] # Obtiene la percepción actual del agente en su posición actual...

        if perception["glitter"]:
            return "GRAB" # Si hay brillo, decide agarrar el oro...

        # Casillas seguras que todavía no han sido visitadas...
        # Ejemplo: Si safe_cells = {(1, 1), (1, 2), (2, 1)} y visited = {(1, 1)}, entonces unvisited_safe_cells = {(1, 2), (2, 1)}
        unvisited_safe_cells = self.safe_cells - self.visited

        # Implementar la búsqueda en anchura (BFS) para encontrar un camino hacia una celda segura no visitada...
        best_path = None
        best_distance = float('inf') # Inicializa la mejor distancia como infinito para encontrar la mínima...

        for destination in sorted(unvisited_safe_cells): # Ordena las celdas seguras no visitadas para garantizar consistencia en la búsqueda...
            result = bfs(
                self.safe_cells,
                self.position, 
                destination, 
                self.get_neighbors) # Llama a la función bfs para encontrar un camino hacia un conjunto de celdas seguras no visitadas...

            # Posteriormente, se toma el resultado de la búsqueda y se compara la distancia encontrada 
            # con la mejor distancia conocida. Si se encuentra un camino más corto, se actualiza el mejor camino y la mejor distancia, para luego avanzar hacia ella...
            if result is not None:
                path, distance = result # Desempaqueta el resultado de bfs en camino y distancia...

                if distance < best_distance: # Si la distancia encontrada es menor que la mejor distancia conocida...
                    best_path = path # Actualiza el mejor camino encontrado...
                    best_distance = distance # Actualiza la mejor distancia encontrada...

        if best_path is None: # Si no se encontró ningún camino hacia una celda segura no visitada...
            return "NO_SAFE_PATH" # Indica que no hay un camino seguro hacia una celda segura no visitada...
        
        # Avanzar hacia la siguiente celda en el mejor camino encontrado...
        next_position = best_path[1] # Obtiene la siguiente posición en el mejor camino encontrado...

        # Llama al método move_towards para determinar la acción necesaria para moverse hacia la siguiente posición...
        # Hasta este momento Pedro ya selecciona una ruta hacia la casilla segura pendiente más cercana. Posteriormente se convierte next_position
        # en una acción según su orientación...
        return self.move_action(next_position) 

    # Método para obtener las celdas vecinas de una posición dada.
    def get_neighbors(self, position):
        x, y = position
        width, height = self.board_size
        neighbors = []

        if x > 1:
            neighbors.append((x - 1, y))  # Celda a la izquierda / Oeste

        if x < width:
            neighbors.append((x + 1, y))  # Celda a la derecha / Este

        if y > 1:
            neighbors.append((x, y - 1))  # Celda abajo / Sur

        if y < height:
            neighbors.append((x, y + 1))  # Celda arriba / Norte

        # Si por ejemplo la posición es (1, 1) y el tamaño del tablero 
        # es (4, 4), los vecinos serían [(2, 1), (1, 2)].

        return neighbors

    # Método para actualizar el conocimiento del agente basado en las percepciones 
    # actuales y las celdas vecinas / Agrega las casillas que deduce como seguras...
    def update_knowledge(self):

        perception = self.perceptions[self.position] # Obtiene la percepción actual del agente en su posición actual...
        neighbors = self.get_neighbors(self.position) # Obtiene los vecinos de la posición actual del agente...

        if not perception["breeze"] and not perception["stench"]:

            # Si no hay brisa ni hedor, todas las celdas vecinas son seguras...
            for neighbor in neighbors:
                self.safe_cells.add(neighbor) # Agrega las celdas vecinas al conjunto de celdas seguras...

        
