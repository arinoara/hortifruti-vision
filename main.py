"""Hortifruti Vision — MVP (ELT 577)

Fluxo: câmera/arquivo → LLM multimodal (identificação) → agente ReAct
(com RAG no catálogo, balança e PDV simulados) → cupom.

Uso:
    python main.py                      # menu interativo (câmera ou arquivo)
    python main.py --imagem foto.jpg    # processa uma imagem e abre o menu
    python main.py --buscar "limão"     # testa apenas o RAG (sem custo de API)
"""

import argparse
import json
from pathlib import Path

import config
from agente import AgenteReAct
from catalogo import Catalogo
from ferramentas import Ferramentas
from operador import OperadorTerminal, colorir
from pdv import PDVSimulado

BANNER = r"""
 _   _            _    _  __            _   _   __     ___     _
| | | | ___  _ __| |_ (_)/ _|_ __ _   _| |_(_)  \ \   / (_)___(_) ___  _ __
| |_| |/ _ \| '__| __|| | |_| '__| | | | __| |   \ \ / /| / __| |/ _ \| '_ \
|  _  | (_) | |  | |_ | |  _| |  | |_| | |_| |    \ V / | \__ \ | (_) | | | |
|_| |_|\___/|_|   \__||_|_| |_|   \__,_|\__|_|     \_/  |_|___/_|\___/|_| |_|
        Identificação de hortifruti com IA  •  MVP ELT 577 (simulação)
"""

MENU = """
[1] Capturar produto pela câmera
[2] Usar arquivo de imagem
[3] Ver cupom atual
[4] Cancelar último item
[5] Finalizar venda (salvar cupom)
[0] Sair
"""


class Aplicacao:
    def __init__(self):
        from visao import identificar  # import tardio: --buscar não precisa do LLM
        self.identificar = identificar
        self.operador = OperadorTerminal()
        self.catalogo = Catalogo(config.CATALOGO_CSV, config.CHROMA_DIR)
        self.pdv = PDVSimulado(config.CUPONS_DIR)
        self.cliente = config.criar_cliente()
        self.ferramentas = Ferramentas(self.catalogo, self.pdv, self.operador)
        self.agente = AgenteReAct(self.cliente, config.MODELO, self.ferramentas,
                                  config.MAX_PASSOS_REACT, config.CONFIANCA_MINIMA)

    def processar_imagem(self, caminho: Path) -> None:
        op = self.operador
        op.mostrar(f"\n📷 Imagem: {caminho}", "info")
        op.mostrar(f"🧠 Etapa 1 — Identificação visual ({config.MODELO})...", "info")
        try:
            ident = self.identificar(self.cliente, config.MODELO, caminho)
        except Exception as e:
            op.mostrar(f"Falha na identificação visual: {e}", "alerta")
            return
        op.mostrar(json.dumps(ident, ensure_ascii=False, indent=2))

        if not ident.get("tem_produto"):
            op.mostrar("Nenhum hortifruti identificado na imagem. Tente novamente.", "alerta")
            return

        op.mostrar("\n🤖 Etapa 2 — Agente ReAct (RAG + ferramentas)", "info")
        try:
            resposta = self.agente.executar(ident)
        except Exception as e:
            op.mostrar(f"Falha no agente: {e}", "alerta")
            return
        op.mostrar(f"\n📢 {resposta}", "final")
        print(self.pdv.cupom_texto())

    def menu(self) -> None:
        while True:
            print(MENU)
            opcao = input("Opção: ").strip()
            if opcao == "1":
                try:
                    import camera
                    caminho = camera.capturar(config.CAMERA_INDICE, config.CAPTURAS_DIR)
                except RuntimeError as e:
                    self.operador.mostrar(str(e), "alerta")
                    continue
                if caminho:
                    self.processar_imagem(caminho)
                else:
                    print("Captura cancelada.")
            elif opcao == "2":
                caminho = Path(input("Caminho da imagem: ").strip().strip("'\""))
                if caminho.is_file():
                    self.processar_imagem(caminho)
                else:
                    self.operador.mostrar("Arquivo não encontrado.", "alerta")
            elif opcao == "3":
                print(self.pdv.cupom_texto())
            elif opcao == "4":
                item = self.pdv.cancelar_ultimo()
                print(f"Cancelado: {item['descricao']}" if item else "Cupom vazio.")
            elif opcao == "5":
                print(self.pdv.cupom_texto())
                arquivo = self.pdv.finalizar()
                print(f"Venda finalizada. Cupom salvo em {arquivo}" if arquivo else "Cupom vazio.")
            elif opcao == "0":
                break


def main() -> None:
    parser = argparse.ArgumentParser(description="Hortifruti Vision — MVP com LLM multimodal, RAG e ReAct")
    parser.add_argument("--imagem", type=Path, help="processa esta imagem antes de abrir o menu")
    parser.add_argument("--buscar", metavar="CONSULTA", help="testa somente a busca RAG no catálogo")
    args = parser.parse_args()

    print(colorir(BANNER, "info"))

    if args.buscar:
        catalogo = Catalogo(config.CATALOGO_CSV, config.CHROMA_DIR)
        for r in catalogo.buscar(args.buscar):
            print(f"{r['codigo']}  {r['nome']} {r['variedade']:<24} {r['unidade']:>3}  "
                  f"R$ {r['preco']:.2f}  relevância={r['pontuacao']}")
        return

    app = Aplicacao()
    if args.imagem:
        app.processar_imagem(args.imagem)
    try:
        app.menu()
    except (KeyboardInterrupt, EOFError):
        print("\nEncerrado.")


if __name__ == "__main__":
    main()
