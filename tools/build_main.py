"""main: E/S + pulso único no start + latch de rearme. Uso: build_main.py <circ> [--bancada]"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from circgen import Circ, geometria
from cells import gate2, not1, sync_reg, split2, instancia
bancada = "--bancada" in sys.argv
c = Circ("main")
# --- entradas
if bancada:
    c.pin_in("clk", 100, 100)
else:
    c.comp(0, "Clock", 100, 100, label="clk")
c.w((100, 100), (130, 100)); c.tunnel("clk", 130, 100, "west")
for nome, tun, y in (("btn_start", "btn_start", 170), ("btn_ack", "btn_ack", 240), ("btn_rst", "rst", 310)):
    if bancada:
        c.pin_in(nome, 100, y)
    else:
        c.comp(5, "Button", 100, y, label=nome.replace("btn_", ""))
    c.w((100, y), (130, y)); c.tunnel(tun, 130, y, "west")
c.pin_in("x_in", 100, 380, 8); c.w((100, 380), (130, 380)); c.tunnel("x_in", 130, 380, "west", 8)

# --- pulso único: start = botão ∧ ¬(botão no ciclo anterior)
sync_reg(c, "btn_start", "prev", 250, 500, width=1)
not1(c, "prev", "nprev", 250, 640)
gate2(c, "AND", "btn_start", "nprev", "start", 250, 700)
# --- latch de rearme (ADR-009): ack_pendente <- botão ∨ (ack_pendente ∧ ¬done)
not1(c, "dne", "ndne", 250, 760)
gate2(c, "AND", "ackp", "ndne", "hold", 250, 820)
gate2(c, "OR", "btn_ack", "hold", "ack_d", 250, 880)
sync_reg(c, "ack_d", "ackp", 250, 980, width=1)

# --- núcleo
instancia(c, geometria(sys.argv[1], "sentinela_core"), "sentinela_core", 670, 300,
          [("x_in", "x_in", 8), ("start", "start", 1), ("ack", "ackp", 1), ("clk", "clk", 1), ("rst", "rst", 1)],
          [("y_out", "y", 8), ("done", "dne", 1), ("ciclos", "cic", 8), ("vent", "vent_o", 1),
           ("alarme", "alarme_o", 1), ("corte", "corte_o", 1), ("falha_sensor", "falha_o", 1)])

# --- LEDs
leds = (("vent_o", "ventilacao", "#00b000"), ("alarme_o", "alarme", "#ff0000"), ("corte_o", "corte", "#ff8000"),
        ("falha_o", "falha_sensor", "#ffcc00"), ("dne", "done", "#0080ff"))
for k, (src, rot, cor) in enumerate(leds):
    y = 120 + 50 * k
    c.tunnel(src, 1110, y, "east"); c.w((1110, y), (1140, y))
    c.comp(5, "LED", 1140, y, color=cor, label=("led_" + rot) if bancada else rot, labelloc="east")
# --- displays hexadecimais: y_out e ciclos
for base, src, X in (("y", "y", 1100), ("c", "cic", 1300)):
    c.comp(8, "Text", X + 25, 400, text="y_out" if base == "y" else "ciclos")
    for dx, nib in ((0, "hi"), (50, "lo")):
        c.comp(5, "Hex Digit Display", X + dx, 500)
        c.w((X + dx, 500), (X + dx, 520)); c.tunnel(f"{base}_{nib}", X + dx, 520, "north", 4)
    split2(c, src, f"{base}_lo", f"{base}_hi", X + 20, 640, 8, 4, 4)
# --- bancada: expõe as saídas para Test Vector
if bancada:
    for k, (n, src, wd) in enumerate((("vent", "vent_o", 1), ("alarme", "alarme_o", 1), ("corte", "corte_o", 1),
                                       ("falha_sensor", "falha_o", 1), ("done", "dne", 1), ("y_out", "y", 8), ("ciclos", "cic", 8))):
        y = 800 + 50 * k
        c.tunnel(src, 1500, y, "east", wd); c.w((1500, y), (1540, y)); c.pin_out(n, 1540, y, wd)
c.write_into(sys.argv[1])
