#!/usr/bin/env python3
"""Modelo de referência (golden model) do SENTINELA e gerador dos Test Vectors.

Uso:
    python3 ref/sentinela_ref.py            # confere o roteiro e regenera tests/*.txt
    python3 ref/sentinela_ref.py --check    # só confere, não escreve arquivos
    python3 ref/sentinela_ref.py --trace    # imprime o traço de referência do fir4

O modelo é ciclo-a-ciclo e segue as decisões do Apêndice A de docs/02-arch.md (E1, D1-D16).
Se o seu hardware tiver outra latência no fir4, ajuste FIR_LATENCIA e regenere.

Convenção dos vetores (sequenciais): clk é um *pino de entrada* do subcircuito.
Cada ciclo de relógio vira duas linhas:
    linha A: clk=0, entradas novas  -> saídas = estado atual (antes da borda)
    linha B: clk=1, mesmas entradas -> saídas = estado após a borda de subida
Cada caso é um <set> próprio (o Logisim reseta o circuito no início do set) e
começa com um ciclo de rst=1, testando também o reset síncrono.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"

DC = "<DC>"

# ---------------------------------------------------------------- parâmetros
H = (16, 48, 48, 16)          # coeficientes Q1.7 (h0..h3), soma = 128
FIR_LATENCIA = 5              # bordas entre a borda do start e done=1 (= ciclos)

T_VENT = 0xB4                 # 90,0 °C
T_CORTE = 0xD2                # 105,0 °C
T_FAIXA_MAX = 0xF0            # 120,0 °C
N_CONGELADO = 8               # amostras idênticas seguidas -> sensor congelado
RUN_MAX = 15                  # contador de 4 bits, saturante

assert sum(H) == 128, "ganho unitário em Q1.7 exige soma 128"


def hx(v: int) -> str:
    return f"0x{v:02X}"


def celsius(v: int) -> str:
    return f"{v / 2:.1f} °C"


# ===================================================================== alu8
ADD, SUB, AND, SHR = 0, 1, 2, 3
OP_NOME = {ADD: "ADD", SUB: "SUB", AND: "AND", SHR: "SHR"}


def alu8(a: int, b: int, op: int) -> tuple[int, int, int]:
    """Retorna (y, zero, carry). carry da SUB = empréstimo (1 se a < b)."""
    if op == ADD:
        s = a + b
        y, c = s & 0xFF, s >> 8
    elif op == SUB:
        y, c = (a - b) & 0xFF, int(a < b)
    elif op == AND:
        y, c = a & b, 0                      # referência: carry=0 (vetor usa <DC>)
    elif op == SHR:
        y, c = a >> 1, a & 1
    else:
        raise ValueError(op)
    return y, int(y == 0), c


# Casos obrigatórios do roteiro: (a, b, op, y, zero, carry|None)
ALU8_ROTEIRO = [
    (0x0F, 0x01, ADD, 0x10, 0, 0),
    (0xFF, 0x01, ADD, 0x00, 1, 1),
    (0x10, 0x10, SUB, 0x00, 1, 0),
    (0x05, 0x0A, SUB, 0xFB, 0, 1),
    (0xF0, 0x3C, AND, 0x30, 0, None),        # "—" no roteiro
    (0x81, 0x00, SHR, 0x40, 0, 1),           # b "—" no roteiro -> 0x00
]

ALU8_EXTRAS = [
    (0x80, 0x80, ADD, "estouro exato: 0x100 -> zero e carry"),
    (0x7F, 0x01, ADD, "sem carry, bit 7 liga"),
    (0x00, 0x00, ADD, "zero sem carry"),
    (0x00, 0x01, SUB, "empréstimo: 0x00 - 0x01 = 0xFF"),
    (0xFF, 0x00, SUB, "sem empréstimo"),
    (0xAA, 0x55, AND, "AND resultando zero"),
    (0x01, 0x00, SHR, "SHR descarta o único bit: zero=1, carry=1"),
    (0xFE, 0x00, SHR, "SHR carry=0"),
    (0x81, 0xFF, SHR, "SHR ignora b"),
]


# ===================================================================== regs2
@dataclass
class Regs2:
    r0: int = 0
    r1: int = 0

    def saidas(self) -> dict:
        return {"r0_out": self.r0, "r1_out": self.r1}

    def borda(self, din: int, we: int, sel: int, rst: int) -> None:
        if rst:
            self.r0 = self.r1 = 0
        elif we:
            if sel:
                self.r1 = din
            else:
                self.r0 = din


# ====================================================================== fir4
def fir4_y(x: list[int]) -> int:
    """x[0] = x[n] (mais nova) ... x[3] = x[n-3]."""
    acc = sum(h * xi for h, xi in zip(H, x))
    assert acc <= 0xFFFF
    return acc >> 7


@dataclass
class Fir4:
    """Modelo de temporização: IDLE -> MAC (LATENCIA-1 bordas) -> DONE (1 ciclo).

    Borda E0 (IDLE & start): desloca x_in, zera acc/índice, ciclos <- 1.
    Bordas E1..E(L-1):       MAC; ciclos += 1; na última, y_out <- acc >> 7.
    Ciclo DONE:              done = 1 (y_out e ciclos já válidos).
    Borda seguinte:          volta a IDLE; y_out e ciclos ficam congelados.
    """
    x: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
    k: int = 0              # 0 = IDLE; 1..L = bordas desde o start
    y: int = 0
    ciclos: int = 0

    def saidas(self) -> dict:
        return {"y_out": self.y, "done": int(self.k == FIR_LATENCIA), "ciclos": self.ciclos}

    def borda(self, x_in: int, start: int, rst: int) -> None:
        if rst:
            self.__init__()
            return
        if self.k == 0:
            if start:
                self.x = [x_in] + self.x[:3]
                self.k, self.ciclos = 1, 1
        elif self.k < FIR_LATENCIA:
            self.k += 1
            self.ciclos += 1
            if self.k == FIR_LATENCIA:
                self.y = fir4_y(self.x)
        else:                               # DONE -> IDLE
            self.k = 0


# Casos do roteiro: (amostras, mais antiga primeiro) -> y esperado na última
FIR4_ROTEIRO = [
    ([0x00, 0x00, 0x00, 0x00], 0x00, "reset do acumulador"),
    ([0x80, 0x80, 0x80, 0x80], 0x80, "ganho unitário em regime"),
    ([0xFF, 0xFF, 0xFF, 0xFF], 0xFF, "ausência de overflow no pior caso"),
    ([0x00, 0x00, 0x00, 0xFF], 0x1F, "resposta ao impulso (tap h0)"),
    ([0x64, 0x64, 0xFF, 0x64], None, "rejeição de pico de 1 amostra"),
]

FIR4_PICO_STREAM = [0x64] * 4 + [0xFF] + [0x64] * 4


# ======================================================== intertravamento
NORMAL, VENT, ALARME, CORTE, FALHA = 0b000, 0b001, 0b010, 0b011, 0b100
NOME_ESTADO = {NORMAL: "NORMAL", VENT: "VENT", ALARME: "ALARME", CORTE: "CORTE", FALHA: "FALHA"}
SAIDAS_MOORE = {          # vent alarme corte falha_sensor
    NORMAL: (0, 0, 0, 0),
    VENT:   (1, 0, 0, 0),
    ALARME: (1, 1, 0, 0),
    CORTE:  (1, 1, 1, 0),
    FALHA:  (1, 1, 1, 1),
}
SAIDAS_INVALIDO = (1, 1, 1, 1)   # 101, 110, 111: saídas seguras


def proximo_estado(estado: int, temp: int, ack: int, sensor_falho: int) -> int:
    """Lógica de próximo estado, avaliada só quando amostra_ok = 1."""
    if estado not in NOME_ESTADO:
        return FALHA
    if sensor_falho:
        return FALHA                         # prioridade máxima
    ge_v, ge_c = temp >= T_VENT, temp >= T_CORTE
    if estado == NORMAL:
        return VENT if ge_v else NORMAL
    if estado == VENT:
        return ALARME if ge_c else (VENT if ge_v else NORMAL)
    if estado == ALARME:
        return CORTE if ge_c else VENT
    # CORTE e FALHA só saem por ack
    return NORMAL if ack else estado


@dataclass
class Intertravamento:
    estado: int = NORMAL
    anterior: int = 0       # temp da amostra anterior
    run: int = 0            # nº de amostras idênticas seguidas (inclui a última)

    def saidas(self) -> dict:
        v, a, c, f = SAIDAS_MOORE.get(self.estado, SAIDAS_INVALIDO)
        return {"vent": v, "alarme": a, "corte": c, "falha_sensor": f}

    def sensor_falho(self, temp: int) -> tuple[int, int]:
        run_prox = min(self.run + 1, RUN_MAX) if temp == self.anterior else 1
        falho = int(temp > T_FAIXA_MAX or run_prox >= N_CONGELADO)
        return falho, run_prox

    def borda(self, temp: int, amostra_ok: int, ack: int, rst: int) -> None:
        if rst:
            self.__init__()
            return
        if self.estado not in NOME_ESTADO:
            self.estado = FALHA
            return
        if not amostra_ok:
            return
        falho, run_prox = self.sensor_falho(temp)
        self.estado = proximo_estado(self.estado, temp, ack, falho)
        self.anterior, self.run = temp, run_prox


# ============================================================ sentinela_core
@dataclass
class SentinelaCore:
    fir: Fir4 = field(default_factory=Fir4)
    fsm: Intertravamento = field(default_factory=Intertravamento)

    def saidas(self) -> dict:
        return {**self.fir.saidas(), **self.fsm.saidas()}

    def borda(self, x_in: int, start: int, ack: int, rst: int) -> None:
        f = self.fir.saidas()                # valores antes da borda
        self.fsm.borda(f["y_out"], f["done"], ack, rst)
        self.fir.borda(x_in, start, rst)


# ============================================================ escrita .txt
class Vetor:
    def __init__(self, titulo: str, entradas: list[tuple[str, int]], saidas: list[tuple[str, int]],
                 sequencial: bool):
        self.titulo = titulo
        self.entradas, self.saidas = entradas, saidas
        self.sequencial = sequencial
        self.cols = [(n, w) for n, w in entradas + saidas]
        if sequencial:
            self.cols += [("<set>", 0), ("<seq>", 0)]
        self.linhas: list[list[str] | str] = []
        self.set_id = 0
        self.seq = 0

    @staticmethod
    def fmt(v, w: int) -> str:
        if isinstance(v, str):
            return v
        if w <= 1:
            return str(v)
        if w == 8:
            return hx(v)
        return format(v, f"0{w}b")       # binário com exatamente w dígitos

    def comentario(self, texto: str) -> None:
        self.linhas.append(f"# {texto}")

    def novo_set(self, texto: str) -> None:
        self.set_id += 1
        self.seq = 0
        self.linhas.append("")
        self.comentario(f"--- set {self.set_id}: {texto}")

    def linha(self, valores: dict, nota: str = "") -> None:
        cel = [self.fmt(valores[n], w) for n, w in self.entradas + self.saidas]
        if self.sequencial:
            self.seq += 1
            cel += [str(self.set_id), str(self.seq)]
        self.linhas.append(cel if not nota else cel + [f"# {nota}"])

    def texto(self) -> str:
        cab = [f"{n}[{w}]" if w > 1 else n for n, w in self.cols]
        dados = [l for l in self.linhas if isinstance(l, list)]
        larg = [max([len(cab[i])] + [len(l[i]) for l in dados]) for i in range(len(cab))]
        out = [f"# {self.titulo}", "# Gerado por ref/sentinela_ref.py — não edite à mão; regenere.", ""]
        out.append("  ".join(c.ljust(larg[i]) for i, c in enumerate(cab)).rstrip())
        for l in self.linhas:
            if isinstance(l, str):
                out.append(l)
            else:
                partes = [c.ljust(larg[i]) for i, c in enumerate(l[:len(cab)])]
                out.append(("  ".join(partes) + ("  " + l[len(cab)] if len(l) > len(cab) else "")).rstrip())
        return "\n".join(out) + "\n"


def ciclo(vet: Vetor, modelo, entradas: dict, borda_args: dict, mascara=None, nota: str = "") -> None:
    """Emite as duas linhas (clk=0 / clk=1) de um ciclo de relógio."""
    for clk in (0, 1):
        if clk == 1:
            modelo.borda(**borda_args)
        s = modelo.saidas()
        if mascara:
            s = mascara(s)
        vet.linha({**entradas, "clk": clk, **s}, nota if clk == 1 else "")


# --------------------------------------------------------------- geradores
def gerar_alu8() -> Vetor:
    v = Vetor("test_alu8.txt — circuito alu8 (combinacional)",
              [("a", 8), ("b", 8), ("op", 2)], [("y", 8), ("zero", 1), ("carry", 1)], False)
    v.comentario("op: 00=ADD 01=SUB 10=AND 11=SHR | carry da SUB = empréstimo (1 se a < b)")
    v.comentario("Casos obrigatórios do roteiro (1-6)")
    for i, (a, b, op, y_esp, z_esp, c_esp) in enumerate(ALU8_ROTEIRO, 1):
        y, z, c = alu8(a, b, op)
        assert (y, z) == (y_esp, z_esp) and (c_esp is None or c == c_esp), f"alu8 caso {i}"
        v.linha({"a": a, "b": b, "op": op, "y": y, "zero": z, "carry": DC if c_esp is None else c},
                f"caso {i}: {OP_NOME[op]}")
    v.comentario("Casos extras (não exigidos)")
    for a, b, op, nota in ALU8_EXTRAS:
        y, z, c = alu8(a, b, op)
        v.linha({"a": a, "b": b, "op": op, "y": y, "zero": z, "carry": DC if op == AND else c},
                f"extra: {OP_NOME[op]} — {nota}")
    return v


def gerar_regs2() -> Vetor:
    v = Vetor("test_regs2.txt — circuito regs2 (sequencial; caso 7 do roteiro)",
              [("din", 8), ("we", 1), ("sel", 1), ("clk", 1), ("rst", 1)],
              [("r0_out", 8), ("r1_out", 8)], True)
    v.comentario("sel=0 escreve r0, sel=1 escreve r1; escrita na borda de subida se we=1; rst síncrono")
    m = Regs2()

    def c(din, we, sel, rst, nota=""):
        ciclo(v, m, {"din": din, "we": we, "sel": sel, "rst": rst},
              {"din": din, "we": we, "sel": sel, "rst": rst}, nota=nota)

    v.novo_set("caso 7: escreve 0xAA em r1 (we=1), tenta 0x55 com we=0 -> r1 permanece 0xAA")
    c(0x00, 0, 0, 1, "reset síncrono")
    c(0xAA, 1, 1, 0, "r1 <- 0xAA")
    c(0x55, 0, 1, 0, "we=0: r1 permanece 0xAA")
    c(0x55, 0, 0, 0, "we=0: r0 permanece 0x00")
    assert m.r1 == 0xAA and m.r0 == 0x00
    m = Regs2()             # o Logisim reseta o circuito a cada novo <set>
    v.novo_set("extra: sel escolhe o registrador; rst tem prioridade sobre we")
    c(0x00, 0, 0, 1, "reset síncrono")
    c(0x55, 1, 0, 0, "r0 <- 0x55")
    c(0xAA, 1, 1, 0, "r1 <- 0xAA, r0 intacto")
    c(0x3C, 0, 0, 0, "we=0: nada muda")
    c(0xFF, 1, 0, 1, "rst=1 e we=1: rst vence; na linha clk=0 ainda 0x55/0xAA (síncrono)")
    return v


def mascara_fir(s: dict, sempre_ciclos=False) -> dict:
    if s["done"]:
        return s
    return {**s, "y_out": DC, "ciclos": s["ciclos"] if sempre_ciclos else DC}


def amostra_fir(v: Vetor, m: Fir4, x: int, mascara, idle_extra: int = 0, extra: dict | None = None) -> int:
    """start por 1 ciclo, espera até done cair; retorna y_out lido com done=1."""
    lido = None
    nota = f"start, x_in={hx(x)}"
    ent = {"x_in": x, "rst": 0, **(extra or {})}
    ciclo(v, m, {**ent, "start": 1}, {"x_in": x, "start": 1, "rst": 0}, mascara, nota)
    while True:
        antes = m.saidas()["done"]
        ciclo(v, m, {**ent, "start": 0}, {"x_in": x, "start": 0, "rst": 0}, mascara)
        if m.saidas()["done"]:
            lido = m.y
            v.linhas[-1].append(f"# done=1 -> y_out={hx(m.y)} ({celsius(m.y)}), ciclos={m.ciclos}")
        if antes and not m.saidas()["done"]:
            break
    for _ in range(idle_extra):
        ciclo(v, m, {**ent, "start": 0}, {"x_in": x, "start": 0, "rst": 0}, mascara, "ocioso")
    assert lido is not None
    return lido


def gerar_fir4() -> Vetor:
    v = Vetor(f"test_fir4.txt — circuito fir4 (sequencial), h={{{', '.join(map(str, H))}}}, "
              f"latência={FIR_LATENCIA}",
              [("x_in", 8), ("start", 1), ("clk", 1), ("rst", 1)],
              [("y_out", 8), ("done", 1), ("ciclos", 8)], True)
    v.comentario("done é verificado em todas as linhas; y_out e ciclos só enquanto done=1")
    v.comentario("x_in fica estável durante toda a amostra; start dura 1 ciclo")
    for i, (seq, esperado, oque) in enumerate(FIR4_ROTEIRO, 1):
        m = Fir4()
        y_final = fir4_y(list(reversed(seq)))
        if esperado is not None:
            assert y_final == esperado, f"fir4 caso {i}: {hx(y_final)} != {hx(esperado)}"
        v.novo_set(f"caso {i}: {', '.join(map(hx, seq))} -> {hx(y_final)} ({oque})")
        ciclo(v, m, {"x_in": 0, "start": 0, "rst": 1}, {"x_in": 0, "start": 0, "rst": 1},
              mascara_fir, "reset síncrono")
        for x in seq:
            y = amostra_fir(v, m, x, mascara_fir)
        assert y == y_final
    # caso 6: instrumentação
    m = Fir4()
    v.novo_set(f"caso 6: ciclos = {FIR_LATENCIA}, done dura exatamente 1 ciclo, ciclos congela depois")
    ciclo(v, m, {"x_in": 0, "start": 0, "rst": 1}, {"x_in": 0, "start": 0, "rst": 1},
          lambda s: mascara_fir(s, True), "reset síncrono")
    amostra_fir(v, m, 0x50, lambda s: mascara_fir(s, True), idle_extra=3)
    assert m.ciclos == FIR_LATENCIA
    # extra: pico atravessando todos os taps
    m = Fir4()
    v.novo_set("extra: pico 0xFF isolado atravessando os 4 taps (base 0x64)")
    ciclo(v, m, {"x_in": 0, "start": 0, "rst": 1}, {"x_in": 0, "start": 0, "rst": 1},
          mascara_fir, "reset síncrono")
    for x in FIR4_PICO_STREAM:
        amostra_fir(v, m, x, mascara_fir)
    return v


def gerar_fsm() -> Vetor:
    v = Vetor("test_fsm.txt — circuito intertravamento (sequencial, Moore)",
              [("temp", 8), ("amostra_ok", 1), ("ack", 1), ("clk", 1), ("rst", 1)],
              [("vent", 1), ("alarme", 1), ("corte", 1), ("falha_sensor", 1)], True)
    v.comentario(f"T_VENT={hx(T_VENT)} T_CORTE={hx(T_CORTE)} T_FAIXA_MAX={hx(T_FAIXA_MAX)} "
                 f"N_CONGELADO={N_CONGELADO}")
    v.comentario("Cada amostra = 1 ciclo com amostra_ok=1 seguido de 1 ciclo com amostra_ok=0 "
                 "(mesmo temp): nada pode mudar sem amostra_ok")
    v.comentario("Saídas (vent alarme corte falha): NORMAL 0000, VENT 1000, ALARME 1100, "
                 "CORTE 1110, FALHA 1111")

    def novo(texto):
        v.novo_set(texto)
        m = Intertravamento()
        ciclo(v, m, {"temp": 0, "amostra_ok": 0, "ack": 0, "rst": 1},
              {"temp": 0, "amostra_ok": 0, "ack": 0, "rst": 1}, nota="reset síncrono")
        return m

    def amostra(m, temp, ack=0, gap=True):
        ent = {"temp": temp, "ack": ack, "rst": 0}
        ciclo(v, m, {**ent, "amostra_ok": 1}, {**ent, "amostra_ok": 1})
        v.linhas[-1].append(f"# temp={hx(temp)}{' ack=1' if ack else ''} -> {NOME_ESTADO[m.estado]}")
        if gap:
            ciclo(v, m, {**ent, "amostra_ok": 0, "ack": 0}, {**ent, "amostra_ok": 0, "ack": 0})
        return m.estado

    def caso(texto, temps, esperado, prefixo=(), acks=None):
        m = novo(texto)
        for t in prefixo:
            amostra(m, t)
        obtidos = [amostra(m, t, (acks or {}).get(j, 0)) for j, t in enumerate(temps)]
        assert obtidos == esperado, f"{texto}: {[NOME_ESTADO[e] for e in obtidos]}"

    N, V, A, C, F = NORMAL, VENT, ALARME, CORTE, FALHA
    caso("caso 1: 0x60, 0x70, 0x80 -> permanece NORMAL", [0x60, 0x70, 0x80], [N, N, N])
    caso("caso 2: 0x60 -> 0xB8 -> 0xA0 = NORMAL -> VENT -> NORMAL", [0x60, 0xB8, 0xA0], [N, V, N])
    caso("caso 3: 0xB8 -> 0xD5 -> 0xD5 = VENT -> ALARME -> CORTE", [0xB8, 0xD5, 0xD5], [V, A, C])
    caso("caso 4: 0xB8 -> 0xD5 -> 0xA0 = VENT -> ALARME -> VENT", [0xB8, 0xD5, 0xA0], [V, A, V])
    caso("caso 5: em CORTE, temp cai para 0x40 sem ack -> permanece CORTE",
         [0x40, 0x41, 0x40], [C, C, C], prefixo=[0xB8, 0xD5, 0xD5])
    caso("caso 6: em CORTE, ack=1 -> NORMAL", [0x40, 0x41], [C, N],
         prefixo=[0xB8, 0xD5, 0xD5], acks={1: 1})
    caso("caso 7a: temp=0xF5 em NORMAL -> FALHA", [0xF5], [F])
    caso("caso 7b: temp=0xF5 em VENT -> FALHA", [0xF5], [F], prefixo=[0xB8])
    caso("caso 7c: temp=0xF5 em ALARME -> FALHA", [0xF5], [F], prefixo=[0xB8, 0xD5])
    caso("caso 7d: temp=0xF5 em CORTE -> FALHA", [0xF5], [F], prefixo=[0xB8, 0xD5, 0xD5])
    caso("caso 7e: em FALHA, ack com sensor ainda falho -> fica; ack com sensor bom -> NORMAL",
         [0xF5, 0xF6, 0x60], [F, F, N], acks={1: 1, 2: 1})
    caso("caso 8a: 0x90 repetido 8 vezes -> FALHA na 8ª amostra", [0x90] * 8, [N] * 7 + [F])
    caso("caso 8b: 0x90 repetido 7 vezes e depois 0x91 -> não falha", [0x90] * 7 + [0x91], [N] * 8)
    caso("caso 9: em VENT, 0xF5 (> T_FAIXA_MAX e >= T_CORTE) -> FALHA, não ALARME",
         [0xF5], [F], prefixo=[0xB8])
    caso("extra: de NORMAL direto para 0xD5 -> só VENT (sobe um degrau por amostra)",
         [0xD5, 0xD5, 0xD5], [V, A, C])
    caso("extra: em ALARME com temp entre T_VENT e T_CORTE (0xC0) -> VENT", [0xC0], [V],
         prefixo=[0xB8, 0xD5])
    caso("extra: congelado em 0x00 desde o reset também conta 8", [0x00] * 8, [N] * 7 + [F])
    caso("extra: sensor congelado por 20 amostras com ack insistente -> FALHA não some (contador satura)",
         [0x90] * 20, [N] * 7 + [F] * 13, acks={j: 1 for j in range(8, 20)})
    caso("extra: limiares exatos 0xB4 (VENT), 0xD2 (ALARME), 0xF0 não é falha",
         [0xB3, 0xB4, 0xD1, 0xD2, 0xF0], [N, V, V, A, C])

    # extra: amostra_ok gating explícito e reset síncrono a partir de CORTE
    m = novo("extra: temp=0xF5 com amostra_ok=0 por 3 ciclos não muda nada; com amostra_ok=1 -> FALHA")
    for _ in range(3):
        ciclo(v, m, {"temp": 0xF5, "amostra_ok": 0, "ack": 0, "rst": 0},
              {"temp": 0xF5, "amostra_ok": 0, "ack": 0, "rst": 0}, nota="sem amostra_ok")
    assert amostra(m, 0xF5) == F
    m = novo("extra: rst síncrono em CORTE volta a NORMAL")
    for t in (0xB8, 0xD5, 0xD5):
        amostra(m, t)
    ciclo(v, m, {"temp": 0xD5, "amostra_ok": 0, "ack": 0, "rst": 1},
          {"temp": 0xD5, "amostra_ok": 0, "ack": 0, "rst": 1}, nota="rst -> NORMAL")
    assert m.estado == NORMAL
    return v


def gerar_sentinela() -> Vetor:
    v = Vetor("test_sentinela.txt — circuito sentinela_core (fir4 + intertravamento; caso 10)",
              [("x_in", 8), ("start", 1), ("ack", 1), ("clk", 1), ("rst", 1)],
              [("y_out", 8), ("done", 1), ("ciclos", 8),
               ("vent", 1), ("alarme", 1), ("corte", 1), ("falha_sensor", 1)], True)
    v.comentario("fir4.y_out -> intertravamento.temp; fir4.done -> intertravamento.amostra_ok")
    v.comentario("Saídas do intertravamento verificadas em todas as linhas")

    def rodar(texto, seq, esperado_max_estado):
        v.novo_set(texto)
        m = SentinelaCore()
        ciclo(v, m, {"x_in": 0, "start": 0, "ack": 0, "rst": 1},
              {"x_in": 0, "start": 0, "ack": 0, "rst": 1}, mascara_fir, "reset síncrono")
        ys = [amostra_fir(v, _Adapt(m), x, mascara_fir, extra={"ack": 0}) for x in seq]
        assert m.fsm.estado == esperado_max_estado and max(ys) < T_VENT, texto
        return ys

    ys = rodar("caso 10: 0x64, 0x64, 0xFF, 0x64 -> pico isolado não dispara VENT",
               [0x64, 0x64, 0xFF, 0x64], NORMAL)
    assert ys[-1] == 0x9E
    rodar("extra: pico 0xFF atravessando os 4 taps (base 0x64) -> nunca sai de NORMAL",
          FIR4_PICO_STREAM, NORMAL)

    # A FSM precisa decidir no done do filtro (não no start): este caso escala e rearma,
    # então qualquer atraso de uma amostra na decisão muda as saídas.
    v.novo_set("extra: aquecimento sustentado 0xF0 -> NORMAL, NORMAL, VENT, ALARME, CORTE; ack -> NORMAL -> VENT")
    m = SentinelaCore()
    ciclo(v, m, {"x_in": 0, "start": 0, "ack": 0, "rst": 1},
          {"x_in": 0, "start": 0, "ack": 0, "rst": 1}, mascara_fir, "reset síncrono")
    estados = []
    for ack in (0, 0, 0, 0, 0, 1, 0):
        amostra_fir(v, _Adapt2(m, ack), 0xF0, mascara_fir, extra={"ack": ack})
        estados.append(m.fsm.estado)
    assert estados == [NORMAL, NORMAL, VENT, ALARME, CORTE, NORMAL, VENT], [NOME_ESTADO[e] for e in estados]
    return v


class _Adapt2(object):
    """Como _Adapt, mas com ack fixo durante a amostra."""

    def __init__(self, core: "SentinelaCore", ack: int):
        self.core, self.ack = core, ack

    def saidas(self):
        return self.core.saidas()

    @property
    def y(self):
        return self.core.fir.y

    @property
    def ciclos(self):
        return self.core.fir.ciclos

    def borda(self, x_in, start, rst):
        self.core.borda(x_in, start, self.ack, rst)


class _Adapt:
    """Permite reusar amostra_fir() com o núcleo integrado (ack=0)."""

    def __init__(self, core: SentinelaCore):
        self.core = core

    def saidas(self):
        return self.core.saidas()

    @property
    def y(self):
        return self.core.fir.y

    @property
    def ciclos(self):
        return self.core.fir.ciclos

    def borda(self, x_in, start, rst):
        self.core.borda(x_in, start, 0, rst)


# ------------------------------------------------------------------ main
def traco_fir4():
    print("Traço de referência fir4 (y_out após cada amostra):")
    for seq, _, oque in FIR4_ROTEIRO + [(FIR4_PICO_STREAM, None, "pico atravessando taps")]:
        x = [0, 0, 0, 0]
        ys = []
        for s in seq:
            x = [s] + x[:3]
            ys.append(fir4_y(x))
        print(f"  {oque:38s} entrada {' '.join(map(hx, seq))}")
        print(f"  {'':38s} y_out   {' '.join(map(hx, ys))}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="só confere, não escreve")
    ap.add_argument("--trace", action="store_true", help="imprime o traço do fir4")
    args = ap.parse_args()

    geradores = {
        "test_alu8.txt": gerar_alu8,
        "test_regs2.txt": gerar_regs2,
        "test_fir4.txt": gerar_fir4,
        "test_fsm.txt": gerar_fsm,
        "test_sentinela.txt": gerar_sentinela,
    }
    textos = {nome: g().texto() for nome, g in geradores.items()}

    caso5 = fir4_y([0x64, 0xFF, 0x64, 0x64])
    print(f"OK: todos os casos do roteiro conferem com o modelo.")
    print(f"    fir4 caso 5 = {hx(caso5)} ({celsius(caso5)}) — o roteiro diz '<= 0x80' (errata)")
    if args.trace:
        traco_fir4()
    if args.check:
        return 0
    TESTS.mkdir(exist_ok=True)
    for nome, txt in textos.items():
        (TESTS / nome).write_text(txt, encoding="utf-8")
        n = sum(1 for l in txt.splitlines() if l and not l.startswith("#")) - 1
        print(f"    escrito tests/{nome} ({n} vetores)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
