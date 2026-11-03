import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from circgen import Circ, geometria
from cells import instancia
c = Circ("sentinela_core")
for n, y, wd in (("x_in", 80, 8), ("start", 130, 1), ("ack", 180, 1), ("clk", 230, 1), ("rst", 280, 1)):
    c.pin_in(n, 60, y, wd); c.w((60, y), (110, y)); c.tunnel(n, 110, y, "west", wd)
# portas lidas da aparência gravada no arquivo (build_fir4 e build_fsm rodam antes)
instancia(c, geometria(sys.argv[1], "fir4"), "fir4", 470, 460,
          [("x_in", "x_in", 8), ("start", "start", 1), ("clk", "clk", 1), ("rst", "rst", 1)],
          [("y_out", "y", 8), ("done", "dne", 1), ("ciclos", "cic", 8)])
# intertravamento: temp = y_out do fir4, amostra_ok = done do fir4
instancia(c, geometria(sys.argv[1], "intertravamento"), "intertravamento", 470, 820,
          [("temp", "y", 8), ("amostra_ok", "dne", 1), ("ack", "ack", 1), ("clk", "clk", 1), ("rst", "rst", 1)],
          [("vent", "vent_o", 1), ("alarme", "alarme_o", 1), ("corte", "corte_o", 1), ("falha_sensor", "falha_o", 1)])
for k, (n, src, wd) in enumerate((("y_out", "y", 8), ("done", "dne", 1), ("ciclos", "cic", 8), ("vent", "vent_o", 1),
                                   ("alarme", "alarme_o", 1), ("corte", "corte_o", 1), ("falha_sensor", "falha_o", 1))):
    y = 80 + 50 * k
    c.tunnel(src, 900, y, "east", wd); c.w((900, y), (940, y)); c.pin_out(n, 940, y, wd)
c.aparencia("fir4 + intertravamento", "#ede9fe")
c.write_into(sys.argv[1])
