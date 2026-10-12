import pygame

from .theme import label


def draw_hud(surface, state, font, small_font, controls: str) -> None:
    agent = state["agent"]
    lines = [
        f"Estado: {state['status']}",
        f"Posición: {tuple(agent['position'])}  Dirección: {agent['direction']}",
        f"Oro: {agent['collected_gold']}/{agent['total_gold']}  Flechas: {agent['arrows']}",
        f"Puntaje: {agent['score']}  Acciones: {agent['action_count']}",
        f"Percepción: {state['perception'] or '—'}",
        controls,
    ]
    for index, text in enumerate(lines):
        surface.blit(label(small_font if index else font, text), (24, 12 + index * 22))
