from collections import deque

def bfs(safe_cells, origin, destination, get_neighbors):

    # Se verifica que tanto el origen como el destino sean celdas seguras conocidas dentro de safe_cells. 
    # Si no lo son, se lanza un ValueError indicando que no se puede realizar la búsqueda.

    # Ejemplo: Si safe_cells = {(1, 1), (1, 2), (2, 1)} y origin = (2, 1), destination = (1, 2), entonces
    # la búsqueda es válida. Pero si origin = (3, 3), se lanzará un ValueError porque (3, 3) no está en safe_cells.

    if origin not in safe_cells or destination not in safe_cells:
        raise ValueError("Origin or destination is not a known safe cell")

    queue = deque([(0, [origin])])  # Cola FIFO con pasos y camino
    expanded = set()  # Casillas ya expandidas

    while queue:
        distance, path = queue.popleft() # Se obtiene el l
        current = path[-1]

        if current == destination: # Si el nodo actual es el destino, se retorna el camino encontrado.
            return path, distance

        if current in expanded: # Si ya se ha expandido este nodo, se omite para evitar ciclos.
            continue

        for neighbor in get_neighbors(current):

            if neighbor in safe_cells and neighbor not in expanded:

                new_path = path + [neighbor]
                new_distance = distance + 1 # Incrementos de a 1 por cada paso a un vecino seguro.

                queue.append((new_distance, new_path))

        expanded.add(current) # Se marca la casilla actual como expandida para no volver a procesarla.

    return None  # No existe una ruta entre las casillas seguras conocidas.