import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from circgen import Circ
c = Circ("alu8")
for n, y, wd in (("a", 80, 8), ("b", 130, 8), ("op", 180, 2)):
    c.pin_in(n, 60, y, wd); c.w((60, y), (110, y)); c.tunnel(n, 110, y, "west", wd)

def entradas_ab(xin, y):
    """Alimenta duas entradas em (xin,y-10)=a e (xin,y+10)=b com tunnels escalonados."""
    c.tunnel("a", xin - 20, y - 10, "east", 8); c.w((xin - 20, y - 10), (xin, y - 10))
    c.tunnel("b", xin - 70, y + 10, "east", 8); c.w((xin - 70, y + 10), (xin, y + 10))

# ADD e SUB (Adder/Subtractor: a (-40,-10) b (-40,+10) cin (-20,-20) cout (-20,+20))
for nome, comp, y in (("add", "Adder", 100), ("sub", "Subtractor", 220)):
    c.comp(3, comp, 300, y, width=8)
    entradas_ab(260, y)
    c.const(280, y - 30, facing="south"); c.w((280, y - 30), (280, y - 20))   # cin/bin = 0
    c.w((280, y + 20), (280, y + 40)); c.tunnel(f"c_{nome}", 280, y + 40, "north")
    c.w((300, y), (320, y)); c.tunnel(f"s_{nome}", 320, y, "west", 8)
# AND
c.comp(1, "AND Gate", 300, 330, width=8, size=30)     # in (270,320) (270,340)
entradas_ab(270, 330)
c.w((300, 330), (320, 330)); c.tunnel("s_and", 320, 330, "west", 8)
# SHR por fiação: separa a[0] e a[7:1]; recombina com bit 7 = 0
bits = {f"bit{i}": (0 if i == 0 else 1) for i in range(8)}
c.comp(0, "Splitter", 260, 420, fanout=2, incoming=8, **bits)   # a (260,420) a0 (280,400) a[7:1] (280,410)
c.tunnel("a", 240, 420, "east", 8); c.w((240, 420), (260, 420))
c.w((280, 400), (300, 400)); c.tunnel("a0", 300, 400, "west")
bits = {f"bit{i}": (1 if i == 7 else 0) for i in range(8)}
c.comp(0, "Splitter", 360, 440, facing="west", fanout=2, incoming=8, **bits)  # y (360,440) [6:0] (340,450) [7] (340,460)
c.w((280, 410), (290, 410), (290, 450), (340, 450))
c.const(320, 460); c.w((320, 460), (340, 460))
c.w((360, 440), (380, 440)); c.tunnel("s_shr", 380, 440, "west", 8)

def mux4(y0, mx, fontes, width):
    """Mux 4:1 com saída em (mx,y0+20); entradas em (mx-40, y0..y0+30). fontes: lista (tipo, rotulo, ty)."""
    c.comp(2, "Multiplexer", mx, y0 + 20, width=width, select=2)
    lanes = [mx - 60, mx - 70, mx - 80, mx - 50]
    for k, (tipo, rot, ty) in enumerate(fontes):
        yk = y0 + 10 * k
        if tipo == "const":
            c.const(mx - 60, yk, width=width); c.w((mx - 60, yk), (mx - 40, yk))
        else:
            c.tunnel(rot, mx - 120, ty, "east", width)
            c.w((mx - 120, ty), (lanes[k], ty), (lanes[k], yk), (mx - 40, yk))
    c.w((mx - 20, y0 + 40), (mx - 20, y0 + 60)); c.tunnel("op", mx - 20, y0 + 60, "north", 2)

# y = mux(op): 00 ADD, 01 SUB, 10 AND, 11 SHR
mux4(220, 560, [("t", "s_add", 160), ("t", "s_sub", 200), ("t", "s_and", 290), ("t", "s_shr", 330)], 8)
c.w((560, 240), (590, 240), (620, 240)); c.pin_out("y", 620, 240, 8)
# zero = (y == 0)
c.comp(3, "Comparator", 680, 340, width=8, mode="unsigned")   # A (640,330) B (640,350) eq (680,340)
c.w((590, 240), (590, 330), (640, 330))
c.const(620, 350, width=8); c.w((620, 350), (640, 350))
c.w((680, 340), (720, 340)); c.pin_out("zero", 720, 340)
# carry = mux(op): c_add, c_sub (empréstimo), 0, a[0]
mux4(430, 560, [("t", "c_add", 380), ("t", "c_sub", 410), ("const", None, None), ("t", "a0", 500)], 1)
c.w((560, 450), (620, 450)); c.pin_out("carry", 620, 450)
c.aparencia("Etapa 1 · ULA de 8 bits", "#dbeafe")
c.write_into(sys.argv[1])
