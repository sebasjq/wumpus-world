'Widgets reutilizables de la interfaz Pygame.'

import pygame

from .rendering import (BUTTON_COLORS, INK, PANEL, TEXT, font, button_surf, draw_text, icon, mix, panel_surf)
class Button:
    """Botón con icono opcional y estados normal, hover, pulsado y deshabilitado.

    ``kind='ghost'`` crea una zona clicable invisible (para tarjetas).
    """

    def __init__(self, rect, label, callback, kind="secondary", enabled=True, icon_name=None,
                 stack=False, size=20, native=False):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.callback = callback
        self.kind = kind
        self.enabled = enabled
        self.icon_name = icon_name
        self.stack = stack
        self.size = size
        self.native = native

    def draw(self, surface, mouse, down, force_disabled=False):
        if self.kind == "ghost":
            return
        enabled = self.enabled and not force_disabled
        hover = enabled and self.rect.collidepoint(mouse)
        state = "disabled" if not enabled else "pressed" if hover and down else \
            "hover" if hover else "normal"
        w, h = self.rect.size
        surface.blit(button_surf(w, h, self.kind, state), self.rect.topleft)
        ink = BUTTON_COLORS.get(self.kind, BUTTON_COLORS["secondary"])[1]
        if not enabled:
            ink = (140, 148, 180)
        dy = 4 if state == "pressed" else 0
        cx, cy = self.rect.centerx, self.rect.centery + dy
        icon_color = None if self.native and enabled else ink
        if self.icon_name and self.stack:
            isz = int(h * .42)
            surface.blit(icon(self.icon_name, isz, icon_color), (cx - isz // 2, self.rect.y + dy + 6))
            draw_text(surface, self.label, (cx, self.rect.bottom - 8 + dy), self.size, ink,
                      anchor="midbottom", title=True)
        elif self.icon_name:
            isz = int(min(h * .56, 34))
            lw = font(self.size, False, True).size(self.label)[0] if self.label else 0
            total = isz + (12 + lw if self.label else 0)
            x0 = cx - total // 2
            surface.blit(icon(self.icon_name, isz, icon_color), (x0, cy - isz // 2))
            if self.label:
                draw_text(surface, self.label, (x0 + isz + 12, cy), self.size, ink,
                          anchor="midleft", title=True)
        else:
            draw_text(surface, self.label, (cx, cy), self.size, ink, anchor="center", title=True)

    def click(self, event):
        if self.enabled and event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()
                return True
        return False


def chip(surface, pos, icon_name, label, color, size=14):
    """Etiqueta redondeada con icono. Devuelve su rect."""
    f = font(size, True)
    w = 14 + 22 + 8 + f.size(label)[0] + 14
    rect = pygame.Rect(pos[0], pos[1], w, 30)
    surface.blit(panel_surf(rect.w, rect.h, mix(color, PANEL, .78), color, 15, False), rect.topleft)
    surface.blit(icon(icon_name, 22), (rect.x + 10, rect.y + 4))
    draw_text(surface, label, (rect.x + 40, rect.centery), size, TEXT, True, "midleft")
    return rect


def keycap(surface, rect, label=None, icon_name=None):
    pygame.draw.rect(surface, INK, rect.move(0, 6), border_radius=12)
    pygame.draw.rect(surface, (62, 72, 150), rect, border_radius=12)
    face = rect.inflate(-8, -12).move(0, -2)
    pygame.draw.rect(surface, (92, 104, 200), face, border_radius=10)
    if icon_name:
        isz = int(rect.h * .5)
        surface.blit(icon(icon_name, isz), icon(icon_name, isz).get_rect(center=face.center))
    else:
        draw_text(surface, label, face.center, 22, TEXT, anchor="center", title=True)


# --------------------------------------------------------------------------- #
# Aplicación
# --------------------------------------------------------------------------- #
