import json

class Environment:
    def __init__(self, board_path):
        with open(board_path, "r", encoding="utf-8") as file:
            board = json.load(file)

        self.board_size = tuple(board["board_size"])  # Tamaño del tablero (ancho, alto)
        self.initial_position = tuple(board["initial_position"])  # Posición inicial del agente
        self.initial_direction = board["direction"]  # Dirección inicial del agente

        self.gold = {tuple(position) for position in board["gold"]}  # Conjunto de posiciones de oro
        self.wumpus = {tuple(position) for position in board["wumpus"]}  # Conjunto de posiciones del Wumpus
        self.pits = {tuple(position) for position in board["pits"]}  # Conjunto de posiciones de pozos

        self.total_gold = len(self.gold)  # Total de oro en el tablero