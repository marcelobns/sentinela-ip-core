import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from circgen import Circ
from cells import gate2, not1, sync_reg, split2
c = Circ("intertravamento")
T_VENT, T_CORTE, T_FAIXA_MAX = 0xB4, 0xD2, 0xF0

for n, t, y, wd in (("temp", "temp", 80, 8), ("amostra_ok", "ok", 130, 1), ("ack", "ack", 180, 1),
                    ("clk", "clk", 230, 1), ("rst", "rst", 280, 1)):
    c.pin_in(n, 60, y, wd); c.w((60, y), (110, y)); c.tunnel(t, 110, y, "west", wd)

def split3(src, outs, X, Y):
    c.tunnel(src, X - 20, Y, "east", 3); c.w((X - 20, Y), (X, Y))
    c.comp(0, "Splitter", X, Y, fanout=3, incoming=3)          # b0 (X+20,Y-30) b1 (Y-20) b2 (Y-10)
    c.w((X + 20, Y - 30), (X + 60, Y - 30)); c.tunnel(outs[0], X + 60, Y - 30, "west")
    c.w((X + 20, Y - 20), (X + 40, Y - 20), (X + 40, Y + 10), (X + 60, Y + 10)); c.tunnel(outs[1], X + 60, Y + 10, "west")
    c.w((X + 20, Y - 10), (X + 30, Y - 10), (X + 30, Y + 50), (X + 60, Y + 50)); c.tunnel(outs[2], X + 60, Y + 50, "west")
def join3(ins, dst, X, Y):
    c.comp(0, "Splitter", X, Y, facing="west", fanout=3, incoming=3)
    c.tunnel(ins[0], X - 50, Y + 10, "east"); c.w((X - 50, Y + 10), (X - 20, Y + 10))
    c.tunnel(ins[1], X - 60, Y + 50, "east"); c.w((X - 60, Y + 50), (X - 40, Y + 50), (X - 40, Y + 20), (X - 20, Y + 20))
    c.tunnel(ins[2], X - 60, Y + 90, "east"); c.w((X - 60, Y + 90), (X - 30, Y + 90), (X - 30, Y + 30), (X - 20, Y + 30))
    c.w((X, Y), (X + 20, Y)); c.tunnel(dst, X + 20, Y, "west", 3)
def comparador(X, Y, saida, porta, b_const=None, b_tunnel=None):
    """Comparator unsigned temp x B; porta: 'gt' (Y-10), 'eq' (Y), 'lt' (Y+10)."""
    c.comp(3, "Comparator", X, Y, width=8, mode="unsigned")
    c.tunnel("temp", X - 60, Y - 10, "east", 8); c.w((X - 60, Y - 10), (X - 40, Y - 10))
    if b_const is not None:
        c.const(X - 50, Y + 10, width=8, value=hex(b_const)); c.w((X - 50, Y + 10), (X - 40, Y + 10))
    else:
        c.tunnel(b_tunnel, X - 110, Y + 10, "east", 8); c.w((X - 110, Y + 10), (X - 40, Y + 10))
    dy = {"gt": -10, "eq": 0, "lt": 10}[porta]
    c.w((X, Y + dy), (X + 20, Y + dy)); c.tunnel(saida, X + 20, Y + dy, "west")

# --- condições sobre temp (coluna X=300)
comparador(360, 360, "lt_v", "lt", b_const=T_VENT)         # ge_v = ¬(temp < T_VENT)
comparador(360, 440, "lt_c", "lt", b_const=T_CORTE)        # ge_c = ¬(temp < T_CORTE)
comparador(360, 520, "faixa", "gt", b_const=T_FAIXA_MAX)   # temp > T_FAIXA_MAX
comparador(360, 600, "igual", "eq", b_tunnel="anterior")   # temp == amostra anterior

# --- detector de congelamento: run_prox = igual ? min(run+1, 15) : 1 ; congelado = run_prox >= 8
c.comp(3, "Adder", 360, 720, width=4)                      # a (320,710) b (320,730) cin (340,700) out (360,720) cout (340,740)
c.tunnel("run", 300, 710, "east", 4); c.w((300, 710), (320, 710))
c.const(310, 730, width=4, value="0x1"); c.w((310, 730), (320, 730))
c.const(340, 680, facing="south"); c.w((340, 680), (340, 700))
c.w((360, 720), (380, 720)); c.tunnel("run_inc", 380, 720, "west", 4)
c.w((340, 740), (340, 760)); c.tunnel("run_max", 340, 760, "north")
c.tunnel("run_inc", 300, 840, "east", 4); c.w((300, 840), (330, 840))
c.comp(2, "Multiplexer", 360, 850, width=4)                # in0 (330,840) in1 (330,860) sel (340,870): satura em 15
c.tunnel("run", 200, 860, "east", 4); c.w((200, 860), (330, 860))
c.w((340, 870), (340, 890)); c.tunnel("run_max", 340, 890, "north")
c.w((360, 850), (380, 850)); c.tunnel("run_sat", 380, 850, "west", 4)
c.comp(2, "Multiplexer", 360, 990, width=4)                # in0 = 1 (amostra diferente), in1 = run_sat (igual)
c.const(320, 980, width=4, value="0x1"); c.w((320, 980), (330, 980))
c.tunnel("run_sat", 250, 1000, "east", 4); c.w((250, 1000), (330, 1000))
c.w((340, 1010), (340, 1030)); c.tunnel("igual", 340, 1030, "north")
c.w((360, 990), (380, 990)); c.tunnel("run_prox", 380, 990, "west", 4)
split2(c, "run_prox", "run_lo", "congelado", 340, 1120, 4, 3, 1)

# --- portas (colunas X=600 e X=1000)
portas = [
    ("NOT", "lt_v", None, "ge_v"), ("NOT", "lt_c", None, "ge_c"),
    ("OR", "faixa", "congelado", "sf"), ("NOT", "sf", None, "nsf"), ("NOT", "ack", None, "nack"),
    ("NOT", "s0", None, "n0"), ("NOT", "s1", None, "n1"), ("NOT", "s2", None, "n2"),
    ("AND", "n2", "n1", "t_n"), ("AND", "t_n", "n0", "is_n"), ("AND", "t_n", "s0", "is_v"),
    ("AND", "n2", "s1", "t_a"), ("AND", "t_a", "n0", "is_a"), ("AND", "t_a", "s0", "is_c"),
    ("AND", "n1", "n0", "t_f"), ("AND", "s2", "t_f", "is_f"),
    ("OR", "s1", "s0", "o10"), ("AND", "s2", "o10", "inval"),
    # nxt2 = sf | (FALHA & ¬ack)
    ("AND", "is_f", "nack", "f_hold"), ("OR", "sf", "f_hold", "nxt2"),
    # nxt1 = ¬sf & (((VENT|ALARME) & ge_c) | (CORTE & ¬ack))
    ("AND", "is_c", "nack", "c_hold"), ("OR", "is_v", "is_a", "va"), ("AND", "va", "ge_c", "va_c"),
    ("OR", "va_c", "c_hold", "x1"), ("AND", "nsf", "x1", "nxt1"),
    # nxt0 = ¬sf & ((NORMAL & ge_v) | (VENT & ge_v & ¬ge_c) | ALARME | (CORTE & ¬ack))
    ("AND", "is_n", "ge_v", "a1"), ("AND", "ge_v", "lt_c", "vgc"), ("AND", "is_v", "vgc", "a2"),
    ("OR", "a1", "a2", "o1"), ("OR", "o1", "is_a", "o2"), ("OR", "o2", "c_hold", "o3"), ("AND", "nsf", "o3", "nxt0"),
    # habilitações: estado só avança com amostra válida (ou reset, ou estado inválido)
    ("OR", "rst", "ok", "en_amostra"), ("OR", "en_amostra", "inval", "en_s"),
    # saídas Moore
    ("NOT", "is_n", None, "vent_o"), ("OR", "is_n", "is_v", "nv"), ("NOT", "nv", None, "alarme_o"),
    ("OR", "nv", "is_a", "nva"), ("NOT", "nva", None, "corte_o"),
]
for k, (kind, a, b, out) in enumerate(portas):
    X, Y = (600, 340 + 60 * k) if k < 20 else (1000, 340 + 60 * (k - 20))
    (not1(c, a, out, X, Y) if kind == "NOT" else gate2(c, kind, a, b, out, X, Y))

# --- estado (coluna X=1400): D = rst ? 000 : (inválido ? 100 : nxt)
split3("s", ("s0", "s1", "s2"), 1440, 140)
join3(("nxt0", "nxt1", "nxt2"), "nxt", 1480, 260)
c.tunnel("nxt", 1430, 410, "east", 3); c.w((1430, 410), (1450, 410))
c.comp(2, "Multiplexer", 1480, 420, width=3)               # in0 (1450,410) in1 (1450,430) sel (1460,440)
c.const(1440, 430, width=3, value="0x4"); c.w((1440, 430), (1450, 430))
c.w((1460, 440), (1460, 460)); c.tunnel("inval", 1460, 460, "north")
c.w((1480, 420), (1500, 420)); c.tunnel("s_d", 1500, 420, "west", 3)
sync_reg(c, "s_d", "s", 1400, 600, width=3, en="en_s")
sync_reg(c, "temp", "anterior", 1400, 760, width=8, en="en_amostra")
sync_reg(c, "run_prox", "run", 1400, 920, width=4, en="en_amostra")

# --- saídas
for n, src, y in (("vent", "vent_o", 80), ("alarme", "alarme_o", 130), ("corte", "corte_o", 180), ("falha_sensor", "s2", 230)):
    c.tunnel(src, 1800, y, "east"); c.w((1800, y), (1840, y)); c.pin_out(n, 1840, y)
c.aparencia("Etapa 3 · FSM Moore", "#fee2e2")
c.write_into(sys.argv[1])
