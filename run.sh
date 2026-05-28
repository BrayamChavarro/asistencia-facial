#!/bin/bash
source "$(dirname "$0")/venv/bin/activate"
HOST=$(hostname -I | awk '{print $1}')
case "${1:-web}" in
  web)
    echo "🌐 http://$HOST:8000  (no funciona cámara en otros dispositivos)"
    python main.py http
    ;;
  https)
    echo "🔒 https://$HOST:8443  (cámara funciona en otros dispositivos)"
    echo "⚠️  Acepta la advertencia de certificado no seguro en el navegador"
    python main.py https
    ;;
  cli)   python cli.py "${@:2}" ;;
  *)
    echo "Uso: ./run.sh [web|https|cli] [comando]"
    echo "  web         - Servidor HTTP (localhost únicamente)"
    echo "  https       - Servidor HTTPS (cámara desde otros dispositivos)"
    echo "  cli register  - Registrar usuario por terminal"
    echo "  cli attendance - Marcar asistencia"
    echo "  cli today      - Ver asistencias de hoy"
    echo "  cli users      - Listar usuarios" ;;
esac
