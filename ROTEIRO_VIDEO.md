# Roteiro do vídeo de demonstração (máx. 5 min)

**Meta:** ~4min30s, com margem de segurança. O enunciado pede: explicação breve,
execução em tempo real, interação e exemplo prático. **Não precisa mostrar código.**

## Preparação (antes de gravar)

**Itens físicos** (compre ou separe):
- 1 produto fácil: **banana** ou **maçã**;
- 1 produto ambíguo: **limão** (de preferência taiti) ou uma maçã que possa ser gala/fuji;
- 1 item vendido por unidade: **alface**, **abacaxi** ou **coco**;
- 1 objeto que não é hortifruti: caneca, celular, estojo;
- Fundo liso e claro (folha A4, pano ou prato branco) e boa iluminação, de frente para a janela.

**Computador:**
- Rode o programa uma vez antes, para baixar o modelo de embeddings e indexar o catálogo.
- Ensaie o roteiro completo pelo menos uma vez, para ver como o modelo responde aos seus produtos.
- Aumente a fonte do terminal (Ctrl + `+`) para ficar legível no vídeo.
- Organize a tela: **terminal à esquerda e janela da câmera à direita**.
- Feche notificações e abas com dados pessoais.
- Rode `clear` no terminal antes de começar.
- **Gravação:** OBS Studio (tela + microfone) ou o gravador do sistema (no GNOME: Ctrl+Shift+Alt+R).
- **Não mostre o `.env`** nem a chave de API na tela.

---

## Roteiro

### Cena 1 — Abertura e problema (0:00 – 0:35)
*Tela: slide 1 ou 2 do pitch, ou o banner do programa.*

> "Olá, sou [nome], e este é o MVP do **Hortifruti Vision**, o projeto que
> apresentei no pitch. No caixa de um hortifruti, o operador precisa
> reconhecer o produto e digitar o código correto no PDV. Isso é lento,
> gera erros de cobrança e exige treinamento. A proposta é: **a câmera
> reconhece, a IA identifica e o PDV recebe o código** automaticamente."

### Cena 2 — Breve explicação da funcionalidade implementada (0:35 – 1:20)
*Tela: diagrama do README (seção "Funcionalidade implementada").*

**O que foi implementado:**
> "Do produto completo, implementei a funcionalidade central: **identificar
> o hortifruti pela câmera e registrar o item no caixa sem digitar o
> código**. Neste MVP, a câmera é a webcam do notebook, e a balança e o
> PDV são simulados."

**Como funciona, passo a passo** (aponte cada bloco do diagrama):
> "O fluxo tem quatro passos:
> 1. O operador coloca o produto diante da câmera e captura a imagem.
> 2. Um **LLM multimodal**, acessado pelo OpenRouter, analisa a foto com
>    um prompt **zero-shot** e diz qual é o produto, a variedade provável e
>    a confiança da identificação.
> 3. Um **agente ReAct** recebe essa identificação e trabalha em ciclos de
>    pensamento, ação e observação. A principal ferramenta é o **RAG**: uma
>    busca semântica no catálogo da loja, indexado no ChromaDB, que traz o
>    código, o preço e se o item é vendido por quilo ou por unidade. Se
>    houver dúvida, o agente pergunta ao operador. Depois ele lê a balança
>    ou a quantidade.
> 4. Por fim, o item é enviado ao PDV e entra no cupom."

**Por que isso importa:**
> "O modelo decide *o que fazer*, mas código, preço e peso vêm sempre do
> catálogo e da balança, nunca da memória do modelo. Isso evita que a IA
> invente um código ou cobre o valor errado."

| Exigência do enunciado | Onde aparece no vídeo |
|---|---|
| Breve explicação da funcionalidade implementada | Cenas 1 e 2 |
| Execução do programa em tempo real | Cenas 3 a 6 (sem cortes durante as identificações) |
| Interação com a aplicação demonstrando suas capacidades | Cenas 4 e 5 (pergunta ao operador, item por unidade, objeto inválido) |
| Exemplo prático de uso | Cenas 3 e 6 (venda completa até o cupom) |

### Cena 3 — Caso simples: banana ou maçã (1:20 – 2:20)
*Tela: terminal + câmera. Execute `python main.py` e escolha a opção 1.*

1. Mostre o produto na área verde e aperte **ESPAÇO**.
2. Aponte o JSON da identificação: *"o modelo identificou banana prata com confiança de 0,9..."*
3. Acompanhe o ciclo ReAct, apontando as cores:
   > "Em ciano, o **pensamento** do agente. Em amarelo, a **ação**: ele busca
   > no catálogo. Em verde, a **observação**: o catálogo devolveu o código
   > 1001, vendido por quilo."
4. Quando a balança simulada pedir o peso, digite algo como **0,850**.
   > "Aqui entraria a balança real. Estou simulando o peso."
5. Mostre a linha `⌨️ [emulação de teclado → PDV] 1001 <TAB> 0,850 <ENTER>`.
   > "Essa é a sequência de teclas que o sistema enviaria ao PDV da loja, sem digitação manual."

### Cena 4 — Caso ambíguo: o agente pergunta (2:20 – 3:20)
*Opção 1 novamente, com o limão.*

> "Agora um caso difícil: limão. Existem várias variedades com preços bem
> diferentes. O taiti custa R$ 4,49 e o siciliano R$ 12,99 o quilo."

- Mostre o agente buscando no catálogo e, por estar em dúvida, chamando **perguntar_operador**.
- Escolha a opção correta.
  > "Quando não tem certeza, o agente pergunta em vez de chutar. Isso evita
  > cobrança errada, que é um dos problemas do pitch."

**Se o modelo identificar o limão com alta confiança e não perguntar**, aproveite:
> "Aqui ele teve confiança suficiente e registrou direto. Quando a imagem
> não permite distinguir, ele pergunta ao operador."
>
> Para garantir a pergunta no vídeo, você pode filmar o limão de longe ou com pouca luz.

### Cena 5 — Item por unidade e item inválido (3:20 – 4:00)
1. **Alface, abacaxi ou coco:** mostre que o agente pede a **quantidade** em vez do peso.
   > "O catálogo informa que este item é vendido por unidade, e o agente adapta a ação."
2. **Caneca ou celular:**
   > "E se não for hortifruti?" → *"Nenhum hortifruti identificado."*

*(Se o tempo apertar, mostre só um dos dois.)*

### Cena 6 — Cupom e encerramento (4:00 – 4:35)
- Opção **5**: mostre o cupom com todos os itens e o total.
  > "No fim, o cupom com todos os itens, pesos e valores, salvo em CSV."
- Encerramento:
  > "Este MVP valida o conceito do Hortifruti Vision: identificação automática
  > com IA, consulta ao catálogo da loja por RAG e decisões com o agente
  > ReAct. O próximo passo é o piloto no Sacolão ABC, com câmera e balança
  > reais e integração com o PDV. Obrigado!"

---

## Dicas

- **Fale enquanto o modelo processa** (leva de 1 a 3 s). Use esse tempo para explicar o que vai aparecer na tela.
- Se algo der errado ao vivo, **não pare**: grave de novo só aquela cena e junte as partes num editor (Shotcut, Kdenlive ou o próprio OBS).
- O vídeo não precisa ser perfeito, mas o professor precisa **ver o programa rodando em tempo real**. Evite cortes no meio de uma identificação.
- **Publicação no YouTube:** escolha a visibilidade **"Não listado"** e cole o link na entrega.

## Checklist de entrega

- [ ] .zip com os `.py`, `README.md`, `requirements.txt`, `.env.example`, `dados/` e `imagens_exemplo/` (com algumas fotos)
- [ ] `.env` com a chave de teste incluído **só** no .zip entregue (nunca no GitHub)
- [ ] Chave de teste com limite de crédito no OpenRouter
- [ ] .zip **sem** `.venv/`, `.chroma/` e `__pycache__/`
- [ ] Link do YouTube (não listado), com no máximo 5 min
- [ ] Lembrete na agenda: revogar a chave depois da nota
