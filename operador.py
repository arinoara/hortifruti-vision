"""Interface com o operador do caixa (terminal).

Toda a entrada/saída humana passa por esta classe. Assim, trocar o terminal
por outra interface (ex.: Gradio) exige apenas uma nova implementação destes
métodos, sem mexer no agente nem nas ferramentas.
"""

import random

# Cores ANSI para deixar o ciclo ReAct legível no vídeo
COR = {
    "pensamento": "\033[96m",  # ciano
    "acao": "\033[93m",        # amarelo
    "observacao": "\033[92m",  # verde
    "final": "\033[95m",       # magenta
    "alerta": "\033[91m",      # vermelho
    "info": "\033[94m",        # azul
    "fim": "\033[0m",
}


def colorir(texto: str, tipo: str) -> str:
    return f"{COR.get(tipo, '')}{texto}{COR['fim']}"


class OperadorTerminal:
    def mostrar(self, texto: str, tipo: str = "") -> None:
        print(colorir(texto, tipo) if tipo else texto)

    def perguntar_opcao(self, pergunta: str, opcoes: list[str]) -> str:
        print(colorir(f"\n🙋 PERGUNTA AO OPERADOR: {pergunta}", "alerta"))
        for i, opcao in enumerate(opcoes, 1):
            print(f"   [{i}] {opcao}")
        print("   [0] Nenhuma das opções / cancelar")
        while True:
            resp = input("   Escolha: ").strip()
            if resp == "0":
                return "Operador cancelou: nenhuma das opções."
            if resp.isdigit() and 1 <= int(resp) <= len(opcoes):
                return opcoes[int(resp) - 1]
            if resp and not resp.isdigit():
                return resp  # operador digitou uma resposta livre
            print("   Opção inválida.")

    def ler_peso(self) -> float:
        """Balança simulada: o operador digita o peso (ou Enter = aleatório)."""
        while True:
            resp = input(
                colorir("\n⚖️  BALANÇA SIMULADA — digite o peso em kg "
                        "(ex.: 0,532 ou 450g; Enter = peso aleatório): ", "info")
            ).strip().lower().replace(",", ".")
            try:
                if not resp:
                    peso = round(random.uniform(0.2, 1.8), 3)
                elif resp.endswith("g") and not resp.endswith("kg"):
                    peso = float(resp[:-1]) / 1000
                else:
                    peso = float(resp.removesuffix("kg"))
                if peso <= 0:
                    raise ValueError
                return round(peso, 3)
            except ValueError:
                print("   Peso inválido, tente novamente.")

    def ler_quantidade(self, sugestao: int = 1) -> int:
        while True:
            resp = input(colorir(f"\n🔢 Quantidade de unidades [Enter = {sugestao}]: ", "info")).strip()
            if not resp:
                return max(1, sugestao)
            if resp.isdigit() and int(resp) > 0:
                return int(resp)
            print("   Quantidade inválida.")
