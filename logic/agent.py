class Agent:
    def __init__(self, initial_position, total_gold, direction='E'):
        self.position = initial_position
        self.direction = direction
        self.alive = True

        self.collected_gold = 0
        self.total_gold = total_gold

        self.visited = set() # Conjunto de posiciones visitadas
        self.safe_cells = {initial_position} # Conjunto de celdas seguras
        self.perceptions = {} # Diccionario para almacenar percepciones para cada posición

    def perceive(self, perception):
        # Guarda lo que recibe del entorno...
        self.visited.add(self.position) # Marca la posición actual como visitada...
        self.perceptions[self.position] = perception # Guarda la percepción asociada a la posición actual...

    def decide(self):
        pass
