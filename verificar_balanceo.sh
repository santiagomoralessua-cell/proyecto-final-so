#!/usr/bin/env bash
# Envía 30 peticiones a Nginx y cuenta qué servidor respondió cada una.
# Uso (WSL / Git Bash / Linux):  bash verificar_balanceo.sh
for i in $(seq 1 30); do curl -s localhost:8080 | grep -o "server [0-9]"; done | sort | uniq -c
