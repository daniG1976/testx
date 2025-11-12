#!/bin/bash
# Startet Flet über die garantierte Umgebungsvariable $VIRTUAL_ENV, um den Pfadfehler zu vermeiden.
$VIRTUAL_ENV/bin/flet run --host 0.0.0.0 --port $PORT testx.py