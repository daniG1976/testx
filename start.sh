#!/bin/bash
# Startet Flet über den vollen Pfad in der virtuellen Umgebung, um Fehler 127 zu vermeiden.
.venv/bin/flet run --host 0.0.0.0 --port $PORT testx.py