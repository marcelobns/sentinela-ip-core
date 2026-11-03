# Documento de Requisitos do Produto — SENTINELA

## Contexto

O SENTINELA é um nó sensor de borda que protege um gerador a diesel contra superaquecimento.
O gerador alimenta o laboratório de uma escola numa comunidade ribeirinha e não tem supervisão
permanente. O SENTINELA lê a temperatura do bloco do motor uma vez por amostra, filtra o ruído
elétrico, detecta quando o próprio sensor está com defeito e executa uma sequência de
intertravamento segura: ventilação, depois alarme, depois corte do gerador, e então exige rearme
manual. Ele também mede quantos ciclos de relógio gasta por amostra. O produto é construído como
um conjunto de blocos reutilizáveis, na disciplina de um IP Core, e é entregue como projeto de
laboratório em Logisim Evolution.

O SENTINELA **não** é um equipamento certificado de segurança. Ele também não faz a aquisição
analógica do sensor, não se comunica em rede e não controla a parte de potência do gerador. Ele
apenas decide e sinaliza: ventilação, alarme, corte e falha do sensor.

Fonte primária: [`Lab_Logisim_SENTINELA.pdf`](Lab_Logisim_SENTINELA.pdf). A errata e as
interpretações do roteiro, citadas aqui como E1 e D1 a D16, estão registradas no
[Apêndice A do documento de arquitetura](02-arch.md#apêndice-a-registro-de-decisões-do-roteiro).

## Personas

| Persona                              | Necessidade principal                                                                         | Interfaces                                                      |
| ------------------------------------ | --------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| Operador local (escola)              | Saber se o gerador está em risco e rearmá-lo com segurança depois de um corte                 | LEDs (ventilação, alarme, corte, falha do sensor), botão de rearme |
| Equipe de manutenção                 | Distinguir superaquecimento real de sensor defeituoso; ajustar limiares e filtro              | Saídas de estado, constantes de limiar, conteúdo da ROM de coeficientes |
| Projetista (aluno)                   | Construir, verificar e documentar cada bloco isoladamente e integrado                         | `sentinela.circ`, vetores de teste, modelo de referência        |
| Avaliador (professor)                | Conferir rapidamente se cada bloco cumpre a especificação                                     | Prints dos Test Vectors, relatório, repositório Git             |
| Integrador de trilha PTT             | Reaproveitar a ALU, o MAC/FIR ou a FSM como embrião de outro produto (PTT2, PTT5, PTT7)       | Subcircuitos com interface fixa e documentada                   |

## Problema

O gerador já queimou duas vezes por superaquecimento. Numa delas, o sensor estava com um fio solto
e a leitura "congelou" num valor normal, então nada disparou. Um termostato simples com um único
limiar não resolve: ele reage ao ruído elétrico do próprio gerador (alarmes falsos e corte
desnecessário de energia da escola) e confia cegamente no sensor (nenhuma proteção quando a leitura
congela ou sai de faixa). Também não existe hoje uma medida do custo de tempo do circuito por
amostra, então ninguém sabe se a solução cabe num orçamento de tempo real.

## Objetivos

### Metas

- Impedir que o gerador opere em superaquecimento sustentado sem que ninguém seja avisado ou sem
  que ele seja desligado.
- Não reagir a picos isolados de ruído: um pico de uma amostra não pode acionar a ventilação.
- Tratar a falha do sensor como condição insegura, detectável e sinalizada separadamente.
- Exigir decisão humana para religar o gerador depois de um corte ou de uma falha.
- Tornar o desempenho mensurável, em ciclos de relógio por amostra.
- Entregar cada bloco como componente reutilizável, verificado isoladamente, com interface estável.

### Não-metas

- Controlar a temperatura de forma contínua, por exemplo com um PID ou ventilação proporcional.
  O controle é por limiares e estados.
- Fazer telemetria, registro histórico ou acesso remoto.
- Fazer diagnóstico de outras falhas do gerador (combustível, óleo, tensão de saída).
- Religar automaticamente depois de um corte.
- Otimizar área, potência ou frequência máxima. Esses números são discutidos no relatório, mas não
  são requisitos.

## Escopo

### Estado atual

| Capacidade                                  | Status  | Observações                                                       |
| ------------------------------------------- | ------- | ----------------------------------------------------------------- |
| Especificação e resolução de ambiguidades   | ✅ 100% | Apêndice A de `02-arch.md`, `fsm_tabela_transicao.md`             |
| Modelo de referência ciclo a ciclo          | ✅ 100% | `ref/sentinela_ref.py`; confere todas as contas do roteiro        |
| Vetores de teste                            | ✅ 100% | 1097 vetores em 5 arquivos, todos aceitos pelo Logisim 5.0.0     |
| Execução automatizada dos testes            | ✅ 100% | `scripts/rodar_testes.sh`                                         |
| Interface dos subcircuitos (pinos)          | ✅ 100% | Aparência personalizada gerada pelos scripts de `tools/`          |
| `regs2` (Etapa 1)                           | ✅ 100% | 18/18 vetores; reset síncrono validado                            |
| `alu8` (Etapa 1)                            | ✅ 100% | 15/15 vetores; SHR por fiação, carry da SUB = empréstimo          |
| `fir4` com contador de ciclos (Etapa 2)     | ✅ 100% | 380/380 vetores; latência 5; soma de 16 bits com 3 × alu8         |
| `intertravamento` (Etapa 3)                 | ✅ 100% | 438/438 vetores; versão hardwired (portas lógicas)                |
| `sentinela_core` e `main` (integração)      | ✅ 100% | core 246/246 vetores; `main` validado numa bancada com pinos      |
| Controle microprogramado (ROM)              | 🔴 0%   | Opcional; vale na rubrica                                         |
| `sequenciador` (Etapa 4, bônus)             | 🔴 0%   | Sem especificação no roteiro                                      |
| Relatório (2 páginas)                       | 🔴 0%   | Tabela de transição pronta; faltam as respostas reflexivas        |

### Bloqueios para a entrega

| Bloqueio                                                                                      | Severidade | Área            |
| --------------------------------------------------------------------------------------------- | ---------- | --------------- |
| Prints e relatório ainda não feitos                                                           | Alta       | Entregáveis     |
| Errata do caso 5 do fir4 (0x9E e não "≤ 0x80") ainda não confirmada com o professor (E1)      | Alta       | Especificação   |
| Transição ALARME → VENT ausente do diagrama, mas exigida pelo caso 4 (D7)                     | Alta       | Especificação   |
| Contagem do sensor congelado diverge entre a dica e o caso 8 (D9)                             | Alta       | Especificação   |
| Vetores sequenciais exigem recursos documentados na 5.0.0; o roteiro pede ≥ 3.8 (D16)         | Média      | Ferramenta      |
| Teste do `regs2` em arquivo separado, diferente do que o roteiro pede (D4)                    | Baixa      | Entregáveis     |
| Etapa 4 e Etapa final possivelmente incompletas no roteiro                                    | Baixa      | Especificação   |

## Regras de negócio

### Representação dos dados

- Uma amostra de temperatura é um inteiro sem sinal de 8 bits; o valor `v` corresponde a
  `v × 0,5 °C`, de 0,0 °C (0x00) a 127,5 °C (0xFF).
- Os coeficientes do filtro estão em Q1.7: o valor 128 representa 1,0.
- Há um único relógio global. O reset é síncrono, ativo em nível alto, e não altera nenhum estado
  antes da borda de subida.

### Aritmética (alu8)

- A operação é selecionada por 2 bits: `00` soma, `01` subtração, `10` AND, `11` deslocamento
  lógico de 1 bit à direita.
- `zero = 1` se e somente se o resultado é 0x00, em todas as operações.
- Na soma, `carry = 1` quando o resultado verdadeiro passa de 0xFF.
- Na subtração, `carry = 1` quando houve empréstimo, ou seja, quando `a < b` (D1).
- No deslocamento, `carry` recebe o bit descartado, e a entrada `b` é ignorada (D2).
- Na AND, `carry` não é especificado; o valor recomendado é 0 (D2).

### Registradores (regs2)

- Uma escrita só acontece na borda de subida com `we = 1`; `sel = 0` escreve r0 e `sel = 1`
  escreve r1 (D4).
- Com `we = 0`, os dois registradores mantêm o valor indefinidamente.
- O reset tem prioridade sobre a escrita.

### Filtragem (fir4)

- A saída é `y[n] = (h0·x[n] + h1·x[n−1] + h2·x[n−2] + h3·x[n−3]) >> 7`.
- Os coeficientes somam exatamente 128 (ganho unitário). O padrão é {16, 48, 48, 16}.
- Os coeficientes são parametrizáveis: trocá-los não exige mudar a lógica do bloco, só o conteúdo
  armazenado.
- Uma entrada constante `c` produz, em regime, a saída `c`, inclusive com `c = 0xFF` (sem estouro,
  D6).
- Cada pulso de `start` processa exatamente uma amostra nova. Com o processador ocupado, `start` é
  ignorado.
- `done` fica em 1 durante exatamente um ciclo por amostra, e `y_out` já é válido nesse ciclo (D5).
- `ciclos` informa a latência entre o `start` e o `done`. Ele fica congelado depois do `done` até o
  próximo `start`. Na implementação de referência, vale 5; outro valor é aceito desde que
  justificado.

### Intertravamento

- Limiares padrão, configuráveis sem alterar a lógica: T_VENT = 0xB4 (90 °C), T_CORTE = 0xD2
  (105 °C), T_FAIXA_MAX = 0xF0 (120 °C), N_CONGELADO = 8 amostras.
- O bloco toma exatamente uma decisão por amostra válida (`amostra_ok = 1`). Sem amostra válida,
  nenhuma saída muda, mesmo que `temp` ou `ack` mudem (D10).
- O sensor é considerado falho quando `temp > T_FAIXA_MAX` ou quando a mesma leitura exata se repete
  em N_CONGELADO amostras seguidas. A falha sai na N-ésima amostra igual, não na seguinte (D9).
- Leitura repetida é contada só em amostras válidas, nunca em ciclos de relógio (D9).
- A falha do sensor tem prioridade sobre qualquer outra transição, inclusive sobre o rearme (D11).
- A escalada sobe no máximo um degrau por amostra: NORMAL → VENT → ALARME → CORTE (D8).
- VENT é ativada com `temp ≥ T_VENT` e desativada com `temp < T_VENT`.
- ALARME é ativado a partir de VENT com `temp ≥ T_CORTE`. O CORTE exige uma segunda amostra
  seguida com `temp ≥ T_CORTE`. Se a temperatura cair abaixo de T_CORTE, o estado volta a VENT (D7).
- CORTE e FALHA só são deixados por rearme manual (`ack`). Eles nunca voltam sozinhos a NORMAL,
  mesmo que a temperatura caia.
- Saídas por estado (ventilação, alarme, corte, falha do sensor): NORMAL 0000, VENT 1000,
  ALARME 1100, CORTE 1110, FALHA 1111. Em FALHA, o gerador é desligado.
- Qualquer código de estado não utilizado leva a FALHA na borda seguinte e apresenta as saídas de
  FALHA enquanto durar (D12).

### Verificação

- Todo bloco tem um arquivo de vetores de teste próprio, gerado a partir do modelo de referência.
  Os vetores não são editados à mão.
- Os vetores conferem todos os casos obrigatórios do roteiro, além de casos extras identificados
  como tais.

## Casos de uso

### UC-001 — Filtrar uma nova leitura do sensor

**Ator:** fonte de amostras (sensor + aquisição)

**Pré-condições:** o filtro está ocioso.

**Fluxo:**

1. A fonte apresenta a nova leitura e pulsa `start`.
2. O filtro incorpora a leitura ao histórico das 4 últimas amostras.
3. O filtro calcula a média ponderada e sinaliza `done` por um ciclo, com o resultado disponível.

**Critérios de aceitação:**

- Com o histórico 0x80 ×4, a saída é 0x80; com 0xFF ×4, é 0xFF; com 0x00, 0x00, 0x00, 0xFF, é 0x1F.
- Com 0x64, 0x64, 0xFF, 0x64, a saída é 0x9E, abaixo de T_VENT (E1).
- `done` dura exatamente um ciclo, e `ciclos` lê o valor de latência declarado (5 na referência).

---

### UC-002 — Acionar a ventilação em aquecimento moderado

**Ator:** SENTINELA (automático)

**Pré-condições:** estado NORMAL, sensor saudável.

**Fluxo:**

1. Chega uma amostra filtrada com `temp ≥ T_VENT`.
2. O SENTINELA liga a ventilação.
3. Quando uma amostra posterior fica abaixo de T_VENT, a ventilação é desligada.

**Critérios de aceitação:**

- A sequência 0x60 → 0xB8 → 0xA0 produz NORMAL → VENT → NORMAL.
- A sequência 0x60, 0x70, 0x80 mantém NORMAL com todas as saídas em 0.
- 0xB3 não liga a ventilação; 0xB4 liga.

---

### UC-003 — Escalar até o corte em superaquecimento sustentado

**Ator:** SENTINELA (automático)

**Pré-condições:** estado VENT.

**Fluxo:**

1. Chega uma amostra com `temp ≥ T_CORTE`: o alarme soa (ALARME).
2. Chega uma segunda amostra seguida com `temp ≥ T_CORTE`: o gerador é cortado (CORTE).

**Critérios de aceitação:**

- 0xB8 → 0xD5 → 0xD5 produz VENT → ALARME → CORTE, com corte = 1.
- 0xB8 → 0xD5 → 0xA0 produz VENT → ALARME → VENT; uma única amostra alta não corta.
- A partir de NORMAL, 0xD5 três vezes seguidas produz VENT → ALARME → CORTE (um degrau por amostra).

---

### UC-004 — Rearmar o gerador depois de um corte

**Ator:** operador local

**Pré-condições:** estado CORTE ou FALHA.

**Fluxo:**

1. O operador verifica o gerador e pressiona o botão de rearme.
2. Na próxima amostra válida, se o sensor estiver saudável, o SENTINELA volta a NORMAL.

**Critérios de aceitação:**

- Em CORTE, uma queda de temperatura para 0x40 sem rearme mantém CORTE.
- Em CORTE, o rearme junto com uma amostra válida leva a NORMAL.
- Em FALHA, um rearme com o sensor ainda falho (por exemplo, 0xF6) mantém FALHA.
- O rearme sem amostra válida não muda o estado.

---

### UC-005 — Detectar leitura fisicamente implausível

**Ator:** SENTINELA (automático)

**Pré-condições:** qualquer estado válido.

**Fluxo:**

1. Chega uma amostra com `temp > T_FAIXA_MAX`.
2. O SENTINELA vai para FALHA na mesma decisão: acende o LED de falha do sensor e corta o gerador.

**Critérios de aceitação:**

- 0xF5 leva a FALHA a partir de NORMAL, VENT, ALARME e CORTE.
- Em VENT, 0xF5 leva a FALHA e não a ALARME (prioridade).
- 0xF0 exato não é considerado falha.

---

### UC-006 — Detectar sensor congelado

**Ator:** SENTINELA (automático)

**Pré-condições:** qualquer estado válido.

**Fluxo:**

1. O SENTINELA recebe leituras idênticas em amostras válidas consecutivas.
2. Na N_CONGELADO-ésima leitura idêntica, ele vai para FALHA.

**Critérios de aceitação:**

- 0x90 oito vezes seguidas leva a FALHA na 8ª amostra.
- 0x90 sete vezes seguida de 0x91 não leva a FALHA.
- 0x00 oito vezes desde o reset também leva a FALHA na 8ª amostra.
- Ciclos de relógio sem amostra válida entre as leituras não contam como repetição.

---

### UC-007 — Rejeitar um pico isolado de ruído

**Ator:** SENTINELA (automático)

**Pré-condições:** sistema integrado (filtro ligado ao intertravamento), estado NORMAL.

**Fluxo:**

1. A fonte entrega uma leitura bruta de 0xFF (127,5 °C) cercada de leituras normais (0x64).
2. O filtro atenua o pico.
3. O intertravamento permanece em NORMAL.

**Critérios de aceitação:**

- Com 0x64, 0x64, 0xFF, 0x64 na entrada bruta, a ventilação não é ligada.
- Com o pico atravessando os 4 taps (0x64 ×4, 0xFF, 0x64 ×4), a maior saída filtrada é 0x9E e o
  estado nunca sai de NORMAL.

---

### UC-008 — Verificar um bloco isoladamente

**Ator:** projetista ou avaliador

**Pré-condições:** o bloco está implementado com a interface documentada.

**Fluxo:**

1. O ator roda os vetores de teste do bloco, no GUI ou pela linha de comando.
2. A ferramenta informa quantos vetores passaram e quais falharam, sinal a sinal.

**Critérios de aceitação:**

- Cada bloco (alu8, regs2, fir4, intertravamento, sentinela_core) tem o seu arquivo de vetores.
- O script de testes informa falha quando qualquer vetor falha, mesmo que a ferramenta retorne
  sucesso (D16).
- Mudar a latência do filtro e regenerar os vetores não exige editar arquivos de teste à mão.

---

### UC-009 — Trocar o filtro sem redesenhar o bloco

**Ator:** equipe de manutenção

**Fluxo:**

1. A equipe escolhe novos coeficientes com soma 128.
2. A equipe substitui o conteúdo armazenado dos coeficientes.

**Critérios de aceitação:**

- Nenhuma ligação ou porta lógica do filtro muda.
- Com coeficientes de soma 128, uma entrada constante continua produzindo a mesma saída em regime.

## Riscos e mitigações

Os riscos de projeto abaixo são também os pontos que o relatório deve discutir.

| Risco                                                                                       | Impacto | Mitigação                                                                            |
| ------------------------------------------------------------------------------------------- | ------- | ------------------------------------------------------------------------------------ |
| Falso "sensor congelado": a filtragem torna leituras estáveis e saudáveis idênticas (0x64 constante por 8 amostras, com o filtro cheio, leva a FALHA) | Alto    | Detectar o congelamento no sinal bruto, onde o ruído prova que o sensor está vivo |
| Fio solto lendo 0x00 não é detectado (não há limite inferior de faixa)                      | Alto    | Propor um limite T_FAIXA_MIN no relatório                                            |
| Rearme com o motor ainda quente volta a escalar logo em seguida                             | Médio   | Propor aceitar o rearme só com `temp < T_VENT`                                       |
| Ventilação liga e desliga a cada amostra perto de T_VENT                                    | Médio   | Propor histerese (dois limiares)                                                     |
| FALHA corta o gerador e deixa a escola sem energia por defeito do sensor                    | Médio   | Discutir um modo degradado (ventilação + alarme, corte após um tempo limite)         |
| Botão de rearme não coincide com uma amostra válida                                         | Baixo   | Registrador de "rearme pendente" no circuito de topo (D10)                           |
| Interpretação divergente da do professor nos pontos ambíguos (E1, D4, D7, D9)               | Alto    | Confirmar antes da entrega; o modelo regenera os vetores se a decisão mudar          |
| Professor usa uma versão do Logisim sem suporte aos vetores sequenciais                     | Médio   | Confirmar a versão; README declara a 5.0.0                                           |
| Orçamento de tempo real impossível de avaliar (sem clock nem período de amostragem)         | Baixo   | Assumir e declarar valores no relatório                                              |

## Roadmap

### Estado atual (novembro de 2026)

A especificação está fechada, com errata e decisões documentadas. Há um modelo de referência
executável e 1097 vetores de teste. Todos os subcircuitos (`alu8`, `regs2`, `fir4`,
`intertravamento`, `sentinela_core` e `main`) estão implementados, e os cinco testáveis por vetores
passam em todos eles. O `main` foi validado numa bancada equivalente, com pinos no lugar dos botões e
do relógio. Os subcircuitos têm aparência personalizada. Faltam os prints e o relatório.

### Curto prazo (até a entrega)

- Confirmar com o professor os itens [VERIFICAR] (E1, D4, D7, D9, D16, Etapa 4).
- ~~Implementar `regs2` e `alu8`~~ (feito).
- ~~Implementar `fir4` com o contador de ciclos~~ (feito).
- ~~Implementar o `intertravamento` (hardwired) e o `sentinela_core`~~ (feito).
- ~~Montar o `main` com relógio, botões, LEDs e exibição de `ciclos`~~ (feito).
- ~~Personalizar a aparência dos subcircuitos~~ (feito).
- Gerar os prints e escrever o relatório.

### Médio prazo (bônus)

- Implementar a lógica de próximo estado em ROM (controle microprogramado) e comparar com a hardwired.
- Implementar a Etapa 4 (`sequenciador`), quando houver especificação.

### Longo prazo

- Reaproveitar o bloco escolhido como embrião da trilha PTT: MAC/FIR para PTT2/PTT3, a FSM para
  PTT5/PTT7.

## Critérios de sucesso

### Qualitativos

- Um avaliador abre o projeto, roda um comando e vê todos os blocos aprovados.
- Cada bloco pode ser testado e reaproveitado sem conhecer os outros.
- Um pico isolado de ruído nunca liga a ventilação, e superaquecimento sustentado sempre corta o
  gerador.
- Um sensor com defeito é sinalizado de forma distinta de um superaquecimento real.
- Todas as decisões tomadas sobre pontos ambíguos do roteiro estão escritas e justificadas.

### Quantitativos

| Critério                                                             | Meta                      |
| -------------------------------------------------------------------- | ------------------------- |
| Vetores de teste aprovados                                           | 1097 de 1097 (100%)       |
| Latência do filtro por amostra (`ciclos`)                            | 5 (ou outro, justificado) |
| Duração de `done` por amostra                                        | exatamente 1 ciclo        |
| Maior saída filtrada com pico isolado de 0xFF sobre base 0x64        | 0x9E (< T_VENT = 0xB4)    |
| Amostras desde a primeira leitura alta até o corte (a partir de NORMAL) | 3                      |
| Amostras idênticas até a detecção de congelamento                    | exatamente 8              |
| Transições de saída de CORTE ou FALHA sem rearme                      | 0                         |
| Relatório                                                            | ≤ 2 páginas, fonte 11     |

## Fora de escopo

- Aquisição analógica do sensor, conversor A/D e calibração do sensor.
- Acionamento de potência: relés, contatores e a eletrônica do gerador.
- Comunicação em rede, telemetria, registro histórico ou alerta remoto (SMS, rádio).
- Religamento automático do gerador.
- Certificação de segurança funcional (por exemplo, IEC 61508) ou garantia de operação em campo.
- Síntese para FPGA ou ASIC e medidas reais de área, potência e frequência.
- Ajuste automático de limiares ou coeficientes em operação.
- Monitoramento de grandezas além da temperatura do bloco do motor.
