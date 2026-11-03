"""Vetor de bancada do main (modelo = pulso único + latch + SentinelaCore). Uso: vet_main.py <saida.txt>"""
import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ref"))
import sentinela_ref as R
class Main:
    def __init__(s): s.core, s.prev, s.ackp = R.SentinelaCore(), 0, 0
    def saidas(s):
        o = s.core.saidas(); return {k: o[k] for k in ("vent", "alarme", "corte", "falha_sensor", "done", "y_out", "ciclos")}
    def borda(s, x_in, btn_start, btn_ack, btn_rst):
        start, dne = int(btn_start and not s.prev), s.core.saidas()["done"]
        ack_d = int(btn_ack or (s.ackp and not dne))
        s.core.borda(x_in, start, s.ackp, btn_rst)
        s.prev, s.ackp = (0, 0) if btn_rst else (btn_start, ack_d)
v = R.Vetor("bancada do main", [("x_in", 8), ("btn_start", 1), ("btn_ack", 1), ("btn_rst", 1), ("clk", 1)],
            [("vent", 1), ("alarme", 1), ("corte", 1), ("falha_sensor", 1), ("done", 1), ("y_out", 8), ("ciclos", 8)], True)
m = Main(); v.novo_set("pulso único, escalada até CORTE e rearme pelo latch")
def ciclo(x, bs=0, ba=0, br=0, nota=""):
    e = {"x_in": x, "btn_start": bs, "btn_ack": ba, "btn_rst": br}
    R.ciclo(v, m, e, e, R.mascara_fir, nota)
ciclo(0, br=1, nota="reset")
estados = []
for amostra in range(5):                    # 0xF0 constante: N, N, VENT, ALARME, CORTE
    for _ in range(8): ciclo(0xF0, bs=1)    # botão segurado 8 ciclos -> uma única amostra
    for _ in range(3): ciclo(0xF0)
    estados.append(R.NOME_ESTADO[m.core.fsm.estado])
assert estados == ["NORMAL", "NORMAL", "VENT", "ALARME", "CORTE"], estados
ciclo(0xF0, ba=1, nota="ack por 1 ciclo, longe do done")
for _ in range(4): ciclo(0xF0)
assert m.core.fsm.estado == R.CORTE and m.ackp == 1            # latch segura o pedido
for _ in range(2): ciclo(0xF0, bs=1)
for _ in range(6): ciclo(0xF0)
assert m.core.fsm.estado == R.NORMAL and m.ackp == 0, (m.core.fsm.estado, m.ackp)
open(sys.argv[1], "w").write(v.texto()); print("bancada:", estados, "-> rearme -> NORMAL")
