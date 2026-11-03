# Pontos a verificar com o professor — SENTINELA

Dupla: Ezequias Carlos Ferreira da Silva e Marcelo Gomes Barbosa ·
Repositório: <https://github.com/marcelobns/sentinela-ip-core>

O roteiro ([`Lab_Logisim_SENTINELA.pdf`](Lab_Logisim_SENTINELA.pdf)) tem uma errata e alguns pontos
ambíguos. Para cada um tomamos uma decisão, implementada no circuito e coberta pelos vetores de teste
(1097 de 1097 aprovados). Os códigos (E1, D1 a D16) são os do
[Apêndice A de `02-arch.md`](02-arch.md#apêndice-a-registro-de-decisões-do-roteiro). Os itens marcados
com **[VERIFICAR]** também aparecem assim no relatório.

**Se a resposta mudar uma decisão:** a regra vive em `ref/sentinela_ref.py`. Muda-se o modelo,
regeneram-se os vetores (`python3 ref/sentinela_ref.py`) e ajusta-se o circuito até os vetores passarem.

Anote a resposta em cada item e marque a caixa quando estiver resolvido.

## Prioridade alta — afetam o resultado esperado dos testes

### 1. [ ] E1 — Valor esperado do caso 5 do fir4 [VERIFICAR]

- **O roteiro diz:** sequência `0x64, 0x64, 0xFF, 0x64` → `y_out` "≤ 0x80".
- **A conta dá:** `(16·100 + 48·255 + 48·100 + 16·100) >> 7 = 20240 >> 7 = 158 = 0x9E` (79 °C).
  O pico cai num tap de peso 48. Como os coeficientes são simétricos, a ordem da sequência não muda
  o resultado. "≤ 0x80" só sairia com o pico num tap de peso 16 (resultado `0x77`).
- **O que fizemos:** o vetor espera `0x9E`. O objetivo do caso continua atendido: `0x9E < T_VENT`, e
  o caso 10 confirma que o pico não liga a ventilação.
- **Pergunta:** o valor correto é `0x9E` (errata), ou a sequência pretendida era outra?
- **Resposta:**

### 2. [ ] D7 — Saída de ALARME quando a temperatura cai [VERIFICAR]

- **O roteiro diz:** o diagrama não mostra nenhuma saída de ALARME além de CORTE, mas o caso 4
  (`0xB8 → 0xD5 → 0xA0`) espera ALARME → VENT.
- **O que fizemos:** com `temp < T_CORTE`, ALARME volta a VENT (desce um degrau), e a amostra
  seguinte decide se volta a NORMAL. Isso segue o caso 4.
- **Pergunta:** a transição ALARME → VENT está correta, ou ALARME deveria ir direto a NORMAL quando
  `temp < T_VENT`?
- **Resposta:**

### 3. [ ] D9 — Contagem do sensor congelado [VERIFICAR]

- **O roteiro diz:** a dica fala em um contador que "incrementa se igual e reseta se diferente", com
  limiar ≥ 8. O caso 8 espera FALHA com 8 repetições e nada com 7.
- **O conflito:** 8 amostras iguais geram só 7 igualdades; contando igualdades, a FALHA sairia na 9ª
  amostra, contra o caso 8.
- **O que fizemos:** o contador conta as amostras idênticas seguidas, incluindo a atual (satura em
  15), e a FALHA sai na 8ª, como pede o caso 8.
- **Pergunta:** a interpretação pelo tamanho da sequência é a esperada?
- **Resposta:**

### 4. [ ] D8 — Uma decisão de escalada por amostra

- **O roteiro diz:** o diagrama vai de NORMAL a VENT com `temp ≥ T_VENT`, sem transição direta para
  ALARME ou CORTE.
- **O que fizemos:** a FSM sobe um degrau por amostra. De NORMAL, mesmo com `temp ≥ T_CORTE`, ela vai
  só para VENT; do primeiro valor alto até o CORTE são 3 amostras.
- **Pergunta:** está correto, ou uma temperatura muito alta deveria pular estados?
- **Resposta:**

### 5. [ ] D10 e D11 — Quando o `ack` vale

- **O roteiro diz:** "transições só são avaliadas quando amostra_ok = 1"; CORTE e FALHA saem por `ack`.
- **O que fizemos:** o `ack` só é considerado junto com `amostra_ok = 1` (D10). No `main`, um latch
  guarda o pedido de rearme até a próxima amostra, para o operador não precisar segurar o botão. Em
  FALHA, se o sensor continua falho, o `ack` é ignorado (D11).
- **Pergunta:** essas duas leituras estão corretas?
- **Resposta:**

## Prioridade média — ferramenta e forma do projeto

### 6. [ ] D16 — Versão do Logisim usada na correção [VERIFICAR]

- **O roteiro diz:** Logisim Evolution 3.8 ou superior.
- **O que fizemos:** usamos a 5.0.0. Os vetores sequenciais usam as colunas `<set>` e `<seq>` e o
  valor `<DC>`, documentados na 5.0.0. Não testamos se a 3.8 abre o `.circ` salvo pela 5.0.0 nem se
  aceita esses vetores.
- **Pergunta:** qual versão será usada na correção? Se for anterior à 5.0.0, precisamos testar nela.
- **Resposta:**

### 7. [ ] D4 — Vetor do `regs2` em arquivo próprio [VERIFICAR]

- **O roteiro diz:** gravar o caso 7 (`regs2`) em `test_alu8.txt`.
- **O que fizemos:** criamos `test_regs2.txt`, porque um Test Vector roda sobre um único circuito, e os
  pinos do `regs2` são diferentes dos da `alu8`.
- **Pergunta:** o arquivo separado é aceito?
- **Resposta:**

### 8. [ ] D15 — Subcircuito extra `sentinela_core`

- **O roteiro pede:** `alu8`, `regs2`, `fir4`, `intertravamento` e um `main` com botões e LEDs.
- **O que fizemos:** acrescentamos `sentinela_core` (`fir4` + `intertravamento`, com pinos) e o vetor
  `test_sentinela.txt`. Botões e LEDs não são controlados por Test Vector, e assim o caso 10
  (integração) fica testável automaticamente. O `main` só instancia o core e cuida da E/S.
- **Pergunta:** o subcircuito e o vetor extras são aceitos?
- **Resposta:**

### 9. [ ] D13 — Reset síncrono sem os componentes Counter e Shift Register

- **O roteiro diz:** `rst` síncrono; sugere Counter (ciclos, índice, watchdog) e Shift Register.
- **O que fizemos:** no Logisim, o *clear* desses componentes é assíncrono. Para cumprir o reset
  síncrono, usamos Registers com o reset pelo D (mux com 0) e pelo enable, mais um Adder onde haveria
  um Counter, e 4 Registers em cascata no lugar do Shift Register.
- **Pergunta:** a substituição é aceita?
- **Resposta:**

## Prioridade baixa — escopo e formato da entrega

### 10. [ ] Etapa 4 e o `sequenciador`

- **O roteiro diz:** a Etapa 4 é um "desafio opcional com bônus", e a entrega cita o `sequenciador`
  "se bônus", mas o PDF não traz a especificação da Etapa 4.
- **Pergunta:** existe um enunciado da Etapa 4? O `sequenciador` é o controle IDLE/MAC/DONE do `fir4`
  separado em subcircuito próprio, ou outra coisa?
- **Resposta:**

### 11. [ ] Bônus do controle microprogramado

- **O roteiro diz:** implementar a lógica de próximo estado hardwired e, "se tiver tempo", a versão
  em ROM como comparação, porque "isso vale na rubrica".
- **O que fizemos:** só a hardwired. O relatório dimensiona a versão em ROM (128 × 3 bits) e compara
  as duas, mas a ROM não está implementada.
- **Pergunta:** a análise sem implementação conta, ou o bônus exige a ROM funcionando?
- **Resposta:**

### 12. [ ] Etapa final — "Ponte para o PTT"

- **O roteiro diz:** "responda obrigatoriamente", mas a lista numerada só tem o item 1.
- **Pergunta:** há outras perguntas além da trilha e do subcircuito embrião?
- **Resposta:**

### 13. [ ] Formato do relatório

- **O roteiro diz:** máximo de 2 páginas, fonte 11.
- **O que fizemos:** 2 páginas A4, margens de 1,5 cm e corpo em 11 pt. A tabela de transição está em
  10 pt, e as 12 referências, em 8 pt.
- **Perguntas:** as referências contam nas 2 páginas? Tabela e referências podem ficar abaixo de 11 pt?
- **Resposta:**

### 14. [ ] Forma de entrega

- **O roteiro pede:** o `.circ`, os vetores, os prints `.png`, o relatório `.pdf` e o repositório Git
  com README.
- **Perguntas:** a entrega é só o link do repositório, ou também por outro meio (arquivo ou sistema da
  disciplina)? O PDF do relatório e os prints devem ficar no repositório? Qual é o prazo?
- **Resposta:**
