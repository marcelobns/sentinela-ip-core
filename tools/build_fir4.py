import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from circgen import Circ, geometria
from cells import gate2, not1, sync_reg, split2, join2, soma_const, alu_add
c = Circ("fir4")
g_alu = geometria(sys.argv[1], "alu8")
# --- entradas
for n, y, wd in (("x_in", 80, 8), ("start", 130, 1), ("clk", 180, 1), ("rst", 230, 1)):
    c.pin_in(n, 60, y, wd); c.w((60, y), (110, y)); c.tunnel(n, 110, y, "west", wd)

# --- controle (coluna X=300): estado s = {s1,s0}: IDLE=00, MAC=01, DONE=10
X, Y = 300, 340
portas = [
    ("NOT", "s0", None, "n0"), ("NOT", "s1", None, "n1"),
    ("AND", "n1", "n0", "idle"), ("AND", "n1", "s0", "mac"), ("AND", "s1", "n0", "dne"),
    ("AND", "i0", "i1", "last"), ("NOT", "last", None, "nlast"),
    ("AND", "idle", "start", "go"),                       # aceita uma nova amostra
    ("AND", "mac", "nlast", "t1"), ("OR", "go", "t1", "ns0"), ("AND", "mac", "last", "ns1"),
    ("OR", "rst", "go", "rgo"),                           # zera acc/índice; habilita o shift
    ("OR", "rgo", "mac", "en_acc"),                       # acc, índice e ciclos avançam
    ("OR", "rst", "ns1", "en_y"),                         # y_out captura no último tap
]
for k, (kind, a, b, out) in enumerate(portas):
    (not1(c, a, out, X, Y + 60 * k) if kind == "NOT" else gate2(c, kind, a, b, out, X, Y + 60 * k))

# --- divisões de barramentos e incrementos (coluna X=700)
split2(c, "s", "s0", "s1", 720, 380, 2, 1, 1)
split2(c, "i", "i0", "i1", 720, 500, 2, 1, 1)
join2(c, "ns0", "ns1", "ns", 760, 600, 2, 1, 1)
soma_const(c, "i", "i_next", 760, 740, 2)
# ciclos: na borda do start vale 1; a cada MAC, +1
c.tunnel("ciclos", 690, 850, "east", 8); c.w((690, 850), (710, 850))
c.comp(2, "Multiplexer", 740, 860, width=8)                # in0 (710,850) in1 (710,870) sel (720,880)
c.const(700, 870, width=8); c.w((700, 870), (710, 870))
c.w((720, 880), (720, 900)); c.tunnel("go", 720, 900, "north")
c.w((740, 860), (760, 860)); c.tunnel("cyc_base", 760, 860, "west", 8)
soma_const(c, "cyc_base", "cyc_next", 760, 1000, 8)

# --- registradores (coluna X=1000), todos com reset síncrono
regs = [
    ("x_in", "x0", 8, "rgo", "rst"), ("x0", "x1", 8, "rgo", "rst"),
    ("x1", "x2", 8, "rgo", "rst"), ("x2", "x3", 8, "rgo", "rst"),
    ("soma", "acc", 16, "en_acc", "rgo"), ("i_next", "i", 2, "en_acc", "rgo"),
    ("y_n", "y", 8, "en_y", "rst"), ("cyc_next", "ciclos", 8, "en_acc", "rst"),
    ("ns", "s", 2, None, "rst"),
]
for k, (d, q, wd, en, clr) in enumerate(regs):
    sync_reg(c, d, q, 1000, 100 + 130 * k, width=wd, en=en, clr=clr)

# --- caminho de dados (coluna X=1500)
# x[i] por mux 4:1 (entradas em (1460, 80..110))
c.comp(2, "Multiplexer", 1500, 100, width=8, select=2)
lanes = [1440, 1430, 1420, 1450]
for k, (rot, ty) in enumerate((("x0", 30), ("x1", 60), ("x2", 140), ("x3", 170))):
    c.tunnel(rot, 1380, ty, "east", 8); c.w((1380, ty), (lanes[k], ty), (lanes[k], 80 + 10 * k), (1460, 80 + 10 * k))
c.w((1480, 120), (1480, 140)); c.tunnel("i", 1480, 140, "north", 2)
c.w((1500, 100), (1520, 100)); c.tunnel("x_sel", 1520, 100, "west", 8)
# coeficientes h0..h3 em ROM 4 x 8 (16, 48, 48, 16)
c.comp(4, "ROM", 1420, 220, addrWidth=2, dataWidth=8, appearance="classic",
       contents="addr/data: 2 8\n10 30 30 10\n")       # A (1420,230) D (1660,280)
c.tunnel("i", 1400, 230, "east", 2); c.w((1400, 230), (1420, 230))
c.w((1660, 280), (1680, 280)); c.tunnel("h", 1680, 280, "west", 8)
# produto 16 bits = x_sel * h
c.comp(3, "Multiplier", 1560, 480, width=8)           # a (1520,470) b (1520,490) cin (1540,460) lo (1560,480) hi (1540,500)
c.tunnel("x_sel", 1500, 470, "east", 8); c.w((1500, 470), (1520, 470))
c.tunnel("h", 1450, 490, "east", 8); c.w((1450, 490), (1520, 490))
c.const(1540, 430, width=8, facing="south"); c.w((1540, 430), (1540, 460))
c.w((1560, 480), (1580, 480)); c.tunnel("p_lo", 1580, 480, "west", 8)
c.w((1540, 500), (1540, 520)); c.tunnel("p_hi", 1540, 520, "north", 8)
# soma = acc + produto com 3 alu8 (ADR-006): lo, h1 = alto, hi = h1 + carry de lo
split2(c, "acc", "acc_lo", "acc_hi", 1440, 620, 16, 8, 8)
alu_add(c, g_alu, "acc_lo", "p_lo", "s_lo", 1530, 760, carry="c_lo")
alu_add(c, g_alu, "acc_hi", "p_hi", "s_h1", 1530, 900)
c.tunnel("c_lo", 1440, 1020, "east"); c.w((1440, 1020), (1480, 1020))
c.comp(0, "Bit Extender", 1520, 1020, in_width=1, out_width=8, type="zero")   # in (1480,1020)
c.w((1520, 1020), (1540, 1020)); c.tunnel("c_lo8", 1540, 1020, "west", 8)
alu_add(c, g_alu, "s_h1", "c_lo8", "s_hi", 1530, 1140)
join2(c, "s_lo", "s_hi", "soma", 1520, 1260, 16, 8, 8)
# y_n = soma[14:7]
bits = {f"bit{k}": (0 if k < 7 else 1 if k < 15 else 2) for k in range(16)}
c.tunnel("soma", 1440, 1420, "east", 16); c.w((1440, 1420), (1460, 1420))
c.comp(0, "Splitter", 1460, 1420, fanout=3, incoming=16, **bits)   # [6:0] (1480,1390) [14:7] (1480,1400) [15] (1480,1410)
c.w((1480, 1400), (1500, 1400)); c.tunnel("y_n", 1500, 1400, "west", 8)

# --- saídas
for n, y, wd in (("y_out", 80, 8), ("done", 130, 1), ("ciclos", 180, 1 * 8)):
    src = {"y_out": "y", "done": "dne", "ciclos": "ciclos"}[n]
    c.tunnel(src, 1800, y, "east", wd); c.w((1800, y), (1840, y)); c.pin_out(n, 1840, y, wd)
c.aparencia("Etapa 2 · FIR 4 taps", "#dcfce7")
c.write_into(sys.argv[1])
