# Recursos de la interfaz

Los recursos se agrupan por tipo para que el código no dependa de archivos
sueltos en la raíz de `interface/`:

- `images/`: `Fondo.png`, `Logo.png` e ilustraciones grandes.
- `icons/`: iconos pequeños, controles, percepciones y sprites del explorador.
- `audio/`: música y efectos en formato MP3.

`interface.rendering` resuelve imágenes en `images/` y `icons/`.
`interface.audio.SoundManager` resuelve música y efectos en `audio/`.
Al agregar un recurso debe actualizarse el catálogo correspondiente y esta
lista si cambia la convención de nombres.
