#!/usr/bin/env bash
# Gera o .zip de entrega (inclui o .env com a chave de teste; exclui ambiente e caches)
set -e
cd "$(dirname "$0")/.."
rm -f hortifruti_vision.zip
zip -r hortifruti_vision.zip hortifruti_vision \
  -x "hortifruti_vision/.venv/*" "hortifruti_vision/.chroma/*" "*/__pycache__/*" \
     "hortifruti_vision/capturas/*.jpg" "hortifruti_vision/cupons/*.csv" "hortifruti_vision/gerar_zip.sh"
echo "Gerado: $(pwd)/hortifruti_vision.zip"
