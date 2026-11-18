class Agent:

    # Constructor del agente, inicializa la posición, dirección, tamaño del tablero, 
    # estado de vida, oro recolectado y total de oro, celdas visitadas y seguras, y percepciones.
    def __init__(self, initial_position, total_gold, board_size, direction='E', arrows=1, allow_risk=False):
        self.position = initial_position # Cambia
        self.initial_position = initial_position # Permanece igual
        self.direction = direction
        self.board_size = board_size # Tamaño del tablero (ancho, alto) / (16, 16) por ejemplo

        self.alive = True
        self.returning_home = False # Recuerda que Pedro decidio retirarse, para que no vuelva a explorar durante el regreso

        self.collected_gold = 0
        self.arrows = arrows
        self.total_gold = total_gold

        self.allow_risk = allow_risk # Permite al agente tomar riesgos si no hay celdas seguras conocidas

        self.visited = set() # Conjunto de posiciones visitadas
        self.safe_cells = {initial_position} # Conjunto de celdas seguras / La posición inicial siempre es segura...
        self.perceptions = {} # Diccionario para almacenar percepciones para cada posición
        self.parents = {initial_position: None} # Recuerda por dónde se entró a cada casilla visitada
        self.last_position = initial_position

        # Ampliación del conocimiento del agente
        self.no_pit_cells = {initial_position} # Conjunto de celdas sin pozos 
        self.no_wumpus_cells = {initial_position} # Conjunto de celdas sin Wumpus

        # Conjuntos para almacenar posibles y confirmadas posiciones de pozos y Wumpus
        self.possible_pits = set() 
        self.confirmed_pits = set()

        self.possible_wumpus = set()
        self.confirmed_wumpus = set()

        self.known_dead_wumpus = set() # Wumpus que Pedro sabe que murieron
        self.possible_dead_cells = set() # Celdas que podrían tener un Wumpus muerto, pero no se sabe con certeza
        self.last_shot_path = [] # Casillar recorridas por el ultimo disparo, en orden

        # Variables para el seguimiento del estado del agente y su desempeño
        self.exited = False # Indica si el agente ha salido del tablero (subido por la entrada)
        self.action_count = 0 # Contador de acciones ejecutadas por el agente
        self.shots_fired = 0 # Contador de disparos realizados por el agente
        self.score = 0 # Puntuación del agente, que se actualiza según las acciones realizadas y los eventos ocurridos en el entorno

    # Método para recibir percepciones del entorno y actualizar el conocimiento del agente.
    def perceive(self, perception):

        if not self.alive or self.exited:
            return  # Si el agente no está vivo, no puede percibir nada

        if self.position != self.last_position:
            if self.position not in self.parents:
                self.parents[self.position] = self.last_position
            self.last_position = self.position

        if perception["scream"] and self.last_shot_path:
            self.possible_dead_cells.update(self.last_shot_path)  # Actualiza las celdas que podrían tener un Wumpus muerto

            # Conserva el orden de las casillas en la trayectoria de la flecha
            candidates = [
                cell
                for cell in self.last_shot_path
                if cell not in self.no_wumpus_cells
                and cell not in self.known_dead_wumpus
            ]

            if candidates:
                first_candidate = candidates[0]  

                # Si el primer candidato es un Wumpus confirmado,
                # la flecha lo alcanzó antes de cualquier otro.
                # Si solo hay un candidato, el grito identifica su posición

                if (first_candidate in self.confirmed_wumpus or len(candidates) == 1):
                    self.known_dead_wumpus.add(first_candidate)  # Marca al Wumpus como muerto

        # La respuesta al ultimo disparo ya fue recibida
        self.last_shot_path = []  # Reinicia la trayectoria de la flecha después de recibir la respuesta del entorno

        # Guarda lo que recibe del entorno...
        self.visited.add(self.position) # Marca la posición actual como visitada...
        # Al ejecutar pedro.visited --> {(1, 1)}

        self.perceptions[self.position] = perception # Guarda la percepción asociada a la posición actual...
        # Al ejecutar pedro.perceptions --> {(1, 1): {"breeze": False, "stench": False, "glitter": False, "bump": False, "scream": False}}

        self.update_knowledge() # Actualiza el conocimiento del agente basado en la percepción actual...

    # Método para decidir la acción a tomar basado en las percepciones y 
    # el conocimiento del agente / Consulta cúales de las casillas seguras quedan por explorar...
    def decide(self):

        if not self.alive: # Si el agente no está vivo, no puede tomar decisiones...
            return "DEAD"

        if self.exited:
            return "EXITED"  # Si el agente ha salido del tablero, no puede tomar decisiones...

        if self.returning_home or self.collected_gold == self.total_gold: # Si el agente ha recolectado todo el oro, no necesita seguir buscando...
            return self.return_action()
        
        perception = self.perceptions[self.position] # Obtiene la percepción actual del agente en su posición actual...

        if perception["glitter"]:
            return "GRAB" # Si hay brillo, decide agarrar el oro...

        # Casillas seguras que todavía no han sido visitadas...
        # Ejemplo: Si safe_cells = {(1, 1), (1, 2), (2, 1)} y visited = {(1, 1)}, entonces unvisited_safe_cells = {(1, 2), (2, 1)}
        unvisited_safe_cells = self.safe_cells - self.visited

        if unvisited_safe_cells:
            # Solo entra en casillas cuya seguridad ya fue deducida.
            destination = min(unvisited_safe_cells, key=lambda cell: (self.tree_distance(cell), cell))
            next_position = self.next_known_step(destination)
            if next_position is not None:
                return self.move_action(next_position)

        if not unvisited_safe_cells:

            # Intenta disparar cuando no puede seguir explorando
            action = self.shoot_action()

            if action is not None:
                return action # Si hay una acción de disparo disponible, la devuelve...

            # Si está permitido tomar riesgos, intenta moverse hacia una celda incierta
            action = self.risk_action()

            if action is not None:
                return action # Si hay una acción de riesgo disponible, la devuelve...

            # No encuentra como continuar: decide retirarse
            self.returning_home = True
            return self.return_action()
        
        self.returning_home = True
        return self.return_action()

    def known_ancestors(self, position):
        # La secuencia guardada al visitar casillas conduce hasta la entrada.
        ancestors = []
        while position is not None:
            ancestors.append(position)
            position = self.parents.get(position)
        return ancestors

    def next_known_step(self, destination):
        # El destino puede ser una casilla segura adyacente todavía sin visitar.
        if destination == self.position:
            return None
        if destination in self.get_neighbors(self.position) and destination in self.safe_cells:
            return destination
        if destination not in self.parents:
            known_neighbors = [cell for cell in self.get_neighbors(destination) if cell in self.parents]
            if not known_neighbors:
                return None
            departure = min(known_neighbors, key=lambda cell: (self.tree_distance(cell), cell))
            return self.next_known_step(departure)

        current_ancestors = self.known_ancestors(self.position)
        destination_ancestors = self.known_ancestors(destination)
        if self.position in destination_ancestors:
            return destination_ancestors[destination_ancestors.index(self.position) - 1]
        for ancestor in current_ancestors:
            if ancestor in destination_ancestors:
                return self.parents[self.position]
        return None

    def tree_distance(self, destination):
        # Prioriza menos pasos sobre casillas conocidas, sin explorar el tablero.
        if destination not in self.parents:
            known_neighbors = [cell for cell in self.get_neighbors(destination) if cell in self.parents]
            return 1 + min((self.tree_distance(cell) for cell in known_neighbors), default=1000000)
        current = self.known_ancestors(self.position)
        target = self.known_ancestors(destination)
        common = next((cell for cell in current if cell in target), None)
        return current.index(common) + target.index(common) if common is not None else 1000000

    # Método para obtener las celdas vecinas de una posición dada.
    def get_neighbors(self, position):
        x, y = position
        width, height = self.board_size
        neighbors = [] # Lista para almacenar las celdas vecinas de la posición dada...

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

        if not self.alive:
            return  # Si el agente no está vivo, no se puede actualizar el conocimiento

        # Sobrevivir demuestra que no hay pozo
        self.no_pit_cells.update(self.visited)

        # Una visita descarta los Wumpus, excepto donde pudo querdar uno muerto. 
        self.no_wumpus_cells.update(self.visited - self.possible_dead_cells)

        # Primero reúne la información que descarta los peligros
        for position, perception in self.perceptions.items(): # Itera sobre las percepciones almacenadas para cada posición visitada por el agente...
            neighbors = set(self.get_neighbors(position)) # Obtiene los vecinos de la posición visitada por el agente...

            # Si no hay brisa, los vecinos no tienen pozos
            if not perception["breeze"]:
                self.no_pit_cells.update(neighbors)

            # Los muertos tambien huelen:
            # sin hedor, no hay Wumpus vivo ni muerto cerca.
            if perception["stench"] is False:
                # Si no hay hedor, los vecinos no tienen Wumpus vivos ni muertos
                self.no_wumpus_cells.update(neighbors | {position})


        # Limpieza de los conjuntos de posibles pozos y Wumpus antes de recalcularlos
        self.possible_pits.clear() 
        self.possible_wumpus.clear()

        # Una muerte identificada tambien confirma su ubicacion
        self.confirmed_wumpus.update(self.known_dead_wumpus) # Actualiza el conjunto de Wumpus confirmados con los Wumpus que el agente sabe que están muertos...


        for position, perception in self.perceptions.items():

            neighbors = set(self.get_neighbors(position))

            if perception["breeze"]:
                candidates = neighbors - self.no_pit_cells # Vecinos que podrían tener pozos

                self.possible_pits.update(candidates) # Agrega los candidatos a posibles pozos

                # Si queda un solo candidato, lo confirmamos como pozo
                if len(candidates) == 1:
                    self.confirmed_pits.update(candidates) # Confirma la posición como pozo

            if perception["stench"] is True:

                # El hedor tambien puede proceder de la propia casilla
                candidates = (
                    neighbors | {position} # Incluye la posición actual como posible fuente de hedor
                ) - self.no_wumpus_cells # Elimina los vecinos que se sabe que no tienen Wumpus vivos ni muertos
                
                self.possible_wumpus.update(candidates) # Agrega los candidatos a posibles Wumpus

                # Si queda un solo candidato, lo confirmamos como Wumpus
                if len(candidates) == 1:
                    self.confirmed_wumpus.update(candidates) # Confirma la posición como Wumpus

        # Si visitó una ubicación confirmada y sobrevivio,
        # el wumpus de esa casilla esta muerto
        self.known_dead_wumpus.update(self.confirmed_wumpus & self.visited)

        # Elimina los pozos y Wumpus confirmados de los posibles 
        # para mantener la consistencia del conocimiento del agente
        self.possible_pits -= self.confirmed_pits # Elimina los pozos confirmados de los posibles pozos
        self.possible_wumpus -= self.confirmed_wumpus # Elimina los Wumpus confirmados de los posibles Wumpus

        # Las visitadas son seguras porque Pedro sobrevivió
        self.safe_cells.update(self.visited) # Actualiza el conjunto de celdas seguras con las posiciones visitadas por el agente...

        # También son seguras las casillas sin pozo donde no hay wumpus o se sabe que 
        # está muerto
        self.safe_cells.update(self.no_pit_cells & (self.no_wumpus_cells | self.known_dead_wumpus))

    # Método para determinar la acción necesaria para moverse hacia la siguiente posición en el camino.
    # Ya sea girando a la izquierda, girando a la derecha o avanzando hacia adelante, según la orientación actual del agente y la posición objetivo.
    # NO EJECUTA EL MOVIMIENTO, SOLO DEVUELVE LA ACCIÓN NECESARIA PARA LLEGAR A LA SIGUIENTE CELDA EN EL CAMINO.
    def move_action(self, next_position):
        x, y = self.position
        next_x, next_y = next_position

        # Determina hacia dónde debe mirar para alcanzar la siguiente celda
        if next_x > x:
            target_direction = 'E'  # Este / Derecha
        elif next_x < x:
            target_direction = 'W'  # Oeste / Izquierda
        elif next_y > y:
            target_direction = 'N'  # Norte / Arriba
        else:
            target_direction = 'S'  # Sur / Abajo

        if self.direction == target_direction:
            return "FORWARD"  # Si ya está mirando en la dirección correcta, avanza hacia adelante

        directions = ['N', 'E', 'S', 'W']  # Orden de las direcciones para determinar giros
        current_index = directions.index(self.direction) # Obtiene el índice de la dirección actual del agente en la lista de direcciones
        target_index = directions.index(target_direction) # Obtiene el índice de la dirección objetivo en la lista de direcciones

        difference = (target_index - current_index) % 4 # Calcula la diferencia entre la dirección objetivo y la dirección actual

        if difference == 3:
            return "TURN_LEFT"  # Si la diferencia es 3, gira a la izquierda

        return "TURN_RIGHT"  # De lo contrario, gira a la derecha

    # Metodo para decidir si disparar al Wumpus confirmado, buscando una celda 
    # segura desde donde disparar y determinando la acción necesaria para llegar 
    # a esa celda o disparar si ya está en posición.
    # NO EJECUTA EL DISPARO, SOLO DEVUELVE LA ACCIÓN NECESARIA PARA 
    # LLEGAR A LA CELDA DESDE DONDE DISPARAR O PARA DISPARAR SI YA ESTÁ EN POSICIÓN.
    def shoot_action(self):

        live_targets = self.confirmed_wumpus - self.known_dead_wumpus # Conjunto de Wumpus confirmados que aún están vivos...

        if self.arrows <= 0 or not live_targets:  # Si no hay flechas disponibles o no hay Wumpus confirmado para disparar...
            return None # No hay flechas disponibles o no hay Wumpus confirmado para disparar...

        best_position = None
        best_target = None
        best_distance = float('inf') # Inicializa la mejor distancia como infinito para encontrar la mínima...

        # Busca una casilla segura desde donde apuntar a un Wumpus confirmado...
        for target in sorted(live_targets):
            target_x, target_y = target

            for shooting_position in sorted(self.safe_cells):
                shooting_x, shooting_y = shooting_position

                # Deben estar alineados horizontal o verticalmente para disparar
                if shooting_x != target_x and shooting_y != target_y:
                    continue

                if shooting_position not in self.parents:
                    continue
                distance = self.tree_distance(shooting_position)
                if distance < best_distance:
                    best_position = shooting_position
                    best_target = target
                    best_distance = distance

        # Si no se encontró ningún camino hacia una celda segura desde donde disparar 
        # al Wumpus confirmado...
        if best_position is None:
            return None

        # Si todavia no llegó, decide como avanzar hacia ella
        if best_position != self.position:
            next_position = self.next_known_step(best_position)
            return self.move_action(next_position) # Llama al método move_action para determinar la acción necesaria para moverse hacia la siguiente posición...

        # Si ya llegó a la posición desde donde disparar, decide disparar.
        # Determina hacia donde debe apuntar
        x, y = self.position
        target_x, target_y = best_target

        if target_x > x:
            target_direction = 'E'  # Este / Derecha
        elif target_x < x:
            target_direction = 'W'  # Oeste / Izquierda
        elif target_y > y:
            target_direction = 'N'  # Norte / Arriba
        else:
            target_direction = 'S'  # Sur / Abajo

        if self.direction == target_direction:
            self.last_shot_path = self.get_shot_path() # Guarda el camino que recorrería la flecha disparada por el agente
            return "SHOOT"  # Si ya está mirando en la dirección correcta, dispara

        # Si no está mirando en la dirección correcta, gira hacia la dirección objetivo
        return self.move_action(best_target) # Llama al método move_action para determinar la acción necesaria para girar hacia la dirección objetivo antes de disparar...

    # Método para obtener el camino que recorrería la flecha disparada 
    # por el agente,
    def get_shot_path(self):
        movements = {
            'N': (0, 1),  # Movimiento hacia el norte / arriba
            'E': (1, 0),  # Movimiento hacia el este / derecha
            'S': (0, -1), # Movimiento hacia el sur / abajo
            'W': (-1, 0)  # Movimiento hacia el oeste / izquierda
        }

        x, y = self.position
        dx, dy = movements[self.direction]
        width, height = self.board_size

        path = []

        # Comienza en la casilla delante de Pedro
        x = x + dx
        y = y + dy

        while 1 <= x <= width and 1 <= y <= height:  # Mientras la flecha esté dentro del tablero
            path.append((x, y))  # Agrega la posición actual al camino de la flecha

            x = x + dx
            y = y + dy

        return path

    # Método para decidir si tomar un riesgo y moverse hacia una celda incierta, 
    # buscando una celda segura desde donde entrar a la incierta y determinando la 
    # acción necesaria para llegar a esa celda o moverse hacia la incierta si ya 
    # está en posición.
    def risk_action(self):

        if not self.allow_risk:
            return None  # Si no se permite tomar riesgos, no se puede decidir una acción de riesgo

        best_departure = None
        best_target = None
        best_distance = float('inf') 

        # Combina los conjuntos de pozos y Wumpus confirmados para obtener 
        # un conjunto de peligros confirmados...
        confirmed_dangers = (
            self.confirmed_pits | (self.confirmed_wumpus - self.known_dead_wumpus))

        # Busca una casilla segura desde donde entrar a una incierta
        # departure es la casilla segura desde la que Pedro dará el último paso
        # hacia una casilla incierta, y target es la casilla incierta a la que Pedro quiere entrar.
        for departure in sorted(self.safe_cells):

            if departure not in self.parents:
                continue
            distance = self.tree_distance(departure)

            for target in sorted(self.get_neighbors(departure)):

                # Solo considera casillas inciertas y no visitadas
                if target in self.safe_cells or target in self.visited:
                    continue

                # Nunca elige un peligro confirmado
                if target in confirmed_dangers:
                    continue

                # Incluye el ultima paso hacia la casilla incierta en la distancia total
                total_distance = distance + 1

                if total_distance < best_distance: # Si la distancia total encontrada es menor que la mejor distancia conocida...
                    best_departure = departure
                    best_target = target # Actualiza el mejor objetivo (casilla incierta) encontrado...
                    best_distance = total_distance # Actualiza la mejor distancia encontrada...

        if best_departure is None:
            return None  # Si no se encontró ningún camino hacia una celda segura desde donde entrar a una incierta, no se puede decidir una acción de riesgo

        # Primero recorre únicamente las casillas seguras
        if best_departure != self.position:
            return self.move_action(self.next_known_step(best_departure))

        # Ya está junto a la candidata: gira o avanza hacia ella
        return self.move_action(best_target)

    # Método para decidir cómo regresar a la posición inicial del agente (entrada)
    # buscando una ruta segura conocida y determinando la acción necesaria para
    # llegar a la siguiente celda en el camino de regreso a la entrada.
    def return_action(self):

        # Si ya esta en la entrada, puede salir
        if self.position == self.initial_position:
            return "CLIMB"

        # Retrocede por las casillas que ya recorrió y comprobó seguras.
        next_position = self.next_known_step(self.initial_position)
        if next_position is None:
            return "NO_SAFE_PATH"  # No hay ruta segura conocida hasta la entrada
        return self.move_action(next_position)
            


        
