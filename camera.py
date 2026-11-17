"""Captura de imagem pela webcam (OpenCV) e preparo da imagem para o LLM."""

import base64
import os
import sys
from datetime import datetime
from pathlib import Path

import cv2

# Evita avisos do Qt embutido no opencv-python no Linux (só afeta este processo):
# - o Qt dele não suporta Wayland e avisa ao cair para X11/XWayland;
# - o cv2 aponta QT_QPA_FONTDIR para uma pasta que não existe no pacote,
#   então usamos as fontes do sistema. Precisa vir depois do "import cv2".
if sys.platform.startswith("linux"):
    if os.environ.get("XDG_SESSION_TYPE") == "wayland":
        os.environ["XDG_SESSION_TYPE"] = "x11"
    _FONTES = Path("/usr/share/fonts/truetype/dejavu")
    if _FONTES.is_dir():
        os.environ["QT_QPA_FONTDIR"] = str(_FONTES)

TITULO_JANELA = "Hortifruti Vision - ESPACO captura | ESC cancela"


def capturar(indice: int, pasta_destino: Path) -> Path | None:
    """Abre a webcam com pré-visualização; ESPAÇO salva a foto, ESC cancela."""
    cap = cv2.VideoCapture(indice)
    if not cap.isOpened():
        raise RuntimeError(f"Não foi possível abrir a câmera {indice}. "
                           "Ajuste CAMERA_INDICE no .env ou use a opção de arquivo.")
    pasta_destino = Path(pasta_destino)
    pasta_destino.mkdir(parents=True, exist_ok=True)
    caminho = None
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError("Falha ao ler imagem da câmera.")
            tela = frame.copy()
            h, w = tela.shape[:2]
            # moldura indicando a "área da balança"
            cv2.rectangle(tela, (w // 6, h // 6), (5 * w // 6, 5 * h // 6), (0, 200, 0), 2)
            cv2.putText(tela, "Posicione o produto na area verde", (20, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 0), 2)
            cv2.putText(tela, "ESPACO = capturar   ESC = cancelar", (20, h - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.imshow(TITULO_JANELA, tela)
            tecla = cv2.waitKey(1) & 0xFF
            if tecla == 32:  # espaço
                caminho = pasta_destino / f"captura_{datetime.now():%Y%m%d_%H%M%S}.jpg"
                cv2.imwrite(str(caminho), frame)
                break
            if tecla == 27:  # ESC
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        cv2.waitKey(1)
    return caminho


def imagem_para_data_url(caminho: Path, lado_max: int = 768) -> str:
    """Redimensiona (economiza tokens) e converte a imagem em data URL base64."""
    img = cv2.imread(str(caminho))
    if img is None:
        raise ValueError(f"Não foi possível ler a imagem: {caminho}")
    h, w = img.shape[:2]
    escala = lado_max / max(h, w)
    if escala < 1:
        img = cv2.resize(img, (int(w * escala), int(h * escala)), interpolation=cv2.INTER_AREA)
    ok, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise ValueError("Falha ao codificar a imagem.")
    return "data:image/jpeg;base64," + base64.b64encode(buffer.tobytes()).decode()
