#!/bin/bash
# Double-clic sur Mac (ou : bash LANCER-mac.command dans le Terminal)
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "Installation (une seule fois)…"
  python3 -m venv .venv || { echo "Installe Python : https://www.python.org/downloads/"; read; exit 1; }
  .venv/bin/pip install -q -r requirements.txt
fi
.venv/bin/python nettoyage.py
echo; read -p "Entrée pour fermer"
