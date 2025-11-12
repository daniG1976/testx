#!/bin/bash
# Startet Flet, indem der Python-Interpreter direkt das installierte Flet-Modul ausführt.
$VIRTUAL_ENV/bin/python -m flet run --host 0.0.0.0 --port $PORT testx.py