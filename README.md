# SENTINELA: do circuito digital ao IP Core

Laboratório de Arquitetura e Organização de Computadores (PPGCA/UFRR). É um nó sensor de borda
que filtra a temperatura de um gerador a diesel, detecta falha do sensor e executa a sequência
de intertravamento ventilação → alarme → corte → rearme manual. O enunciado está em
[`docs/Lab_Logisim_SENTINELA.pdf`](docs/Lab_Logisim_SENTINELA.pdf).

**Ferramenta:** Logisim-evolution **5.0.0** (o roteiro pede ≥ 3.8; veja a decisão D16 em
`docs/02-arch.md`).

## Estrutura

```
sentinela.circ                  projeto Logisim: todos os subcircuitos implementados
tests/
  test_alu8.txt                 alu8: casos 1–6 do roteiro + extras (combinacional)
  test_regs2.txt                regs2: caso 7 do roteiro + extras (sequencial)
  test_fir4.txt                 fir4: casos 1–6 + pico atravessando os taps
  test_fsm.txt                  intertravamento: casos 1–9 + extras
  test_sentinela.txt            sentinela_core (fir4 + intertravamento): caso 10
ref/sentinela_ref.py            modelo de referência ciclo a ciclo; gera os vetores
scripts/rodar_testes.sh         roda todos os vetores pela linha de comando
docs/01-prd.md                  requisitos do produto (o quê e por quê)
docs/02-arch.md                 arquitetura, princípios, ADRs e registro de decisões do roteiro (como)
docs/fsm_tabela_transicao.md    tabela de transição completa da FSM (vai para o relatório)
```

## Interfaces dos subcircuitos

Os nomes dos pinos precisam ser **exatamente** estes, porque o Test Vector casa as colunas pelo
label.

| Subcircuito | Entradas | Saídas |
|---|---|---|
| `alu8` | `a[8]` `b[8]` `op[2]` | `y[8]` `zero` `carry` |
| `regs2` | `din[8]` `we` `sel` `clk` `rst` | `r0_out[8]` `r1_out[8]` |
| `fir4` | `x_in[8]` `start` `clk` `rst` | `y_out[8]` `done` `ciclos[8]` |
| `intertravamento` | `temp[8]` `amostra_ok` `ack` `clk` `rst` | `vent` `alarme` `corte` `falha_sensor` |
| `sentinela_core` | `x_in[8]` `start` `ack` `clk` `rst` | `y_out[8]` `done` `ciclos[8]` `vent` `alarme` `corte` `falha_sensor` |
| `main` | Clock, Buttons | LEDs, Hex Digit Display (integra `sentinela_core`) |

`op`: `00` ADD, `01` SUB, `10` AND, `11` SHR. O `clk` é um **pino** em todos os subcircuitos; o
Clock global fica só no `main`.

## Como rodar os vetores de teste

**No GUI:** abra `sentinela.circ`, selecione o subcircuito na árvore, use **Simulate → Test Vector…**,
carregue o `.txt` correspondente e tire o print do resultado.

**Pela linha de comando** (todos de uma vez, ou só um):

```bash
scripts/rodar_testes.sh
scripts/rodar_testes.sh fir4
```

O script usa o `.jar` do app instalado em `/Applications`. Para usar outro, defina `LOGISIM_JAR`.
O equivalente manual é:

```bash
java -jar logisim-evolution-5.0.0-all.jar --test-vector fir4 tests/test_fir4.txt sentinela.circ
```

Os logs ficam em `tests/resultados/`. Enquanto os subcircuitos estiverem vazios, todos os
vetores falham com saídas `U`. É o esperado.

### Formato dos vetores sequenciais

Cada caso é um `<set>`: o Logisim reseta o circuito no início do set, e o primeiro ciclo de cada
caso aplica `rst = 1`. Cada ciclo de relógio ocupa duas linhas:

```
clk=0  entradas novas   → saídas = estado antes da borda
clk=1  mesmas entradas  → saídas = estado depois da borda de subida
```

`<DC>` marca uma saída que não é verificada naquela linha.

## Operar o `main`

1. Abra `sentinela.circ`, com o circuito `main` selecionado, e ligue o relógio:
   **Simulate → Ticks Enabled** (ajuste a frequência em **Simulate → Tick Frequency**).
2. Clique em **rst** com o Poke Tool, mantendo-o pressionado por pelo menos um ciclo.
3. Defina a leitura do sensor no pino `x_in` (Poke Tool; por exemplo `F0` = 120 °C).
4. Clique em **start** para processar uma amostra. Segurar o botão gera uma amostra só (pulso único).
5. Os LEDs mostram ventilação, alarme, corte e falha do sensor. Os displays mostram `y_out` e
   `ciclos` em hexadecimal; `ciclos` deve ler `05`.
6. Em CORTE ou FALHA, clique em **ack**. O pedido fica guardado até a próxima amostra, e o rearme
   acontece no `done` dela.

Com `x_in = F0` e cinco cliques em start, o sistema passa por NORMAL, NORMAL, VENT, ALARME e CORTE.

## Regenerar os vetores

Os `.txt` são gerados pelo modelo de referência. Não os edite à mão.

```bash
python3 ref/sentinela_ref.py           # confere as contas do roteiro e reescreve tests/*.txt
python3 ref/sentinela_ref.py --check   # só confere
python3 ref/sentinela_ref.py --trace   # traço de referência do fir4 (y_out por amostra)
```

Se o seu fir4 tiver outra latência, mude `FIR_LATENCIA` no modelo e regenere. O script só usa a
biblioteca padrão do Python 3.10 ou mais recente.

## Entregáveis

- [x] `sentinela.circ` com `alu8`, `regs2`, `fir4`, `intertravamento`, `sentinela_core` e `main`
- [ ] aparência personalizada em cada subcircuito (entradas à esquerda, saídas à direita)
- [ ] todos os vetores passando (`scripts/rodar_testes.sh`), com prints `.png` de cada um
- [ ] print do `main` em simulação mostrando `ciclos`
- [ ] relatório `.pdf` (até 2 páginas) com a tabela de transição, as perguntas reflexivas e a ponte para o PTT
- [ ] (bônus) controle microprogramado por ROM; `sequenciador` da Etapa 4

Antes da entrega, veja os itens **[VERIFICAR]** nos bloqueios de `docs/01-prd.md`. O mais
importante é a errata do caso 5 do fir4: o valor correto é `0x9E`, não "≤ 0x80".
