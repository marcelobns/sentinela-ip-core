import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from circgen import Circ
c = Circ("regs2")
# entradas
c.pin_in("din", 60, 80, 8)
for n, y in (("we", 140), ("sel", 190), ("clk", 240), ("rst", 290)):
    c.pin_in(n, 60, y); c.w((60, y), (110, y)); c.tunnel(n, 110, y, "west")
# D = rst ? 0 : din
c.comp(2, "Multiplexer", 220, 90, width=8)          # in0 (190,80) in1 (190,100) sel (200,110)
c.w((60, 80), (190, 80))
c.const(170, 100, width=8); c.w((170, 100), (190, 100))
c.w((200, 110), (200, 130)); c.tunnel("rst", 200, 130, "north")
c.w((220, 90), (240, 90)); c.tunnel("d", 240, 90, "west", 8)

def registrador(nome, qy, en_and_inputs):
    """Register classic com Q em (400,qy): D (370,qy) en (370,qy+10) clk (380,qy+20)."""
    c.comp(4, "Register", 400, qy, appearance="classic", width=8, label=nome)
    c.tunnel("d", 350, qy, "east", 8); c.w((350, qy), (370, qy))
    c.w((380, qy + 20), (380, qy + 40)); c.tunnel("clk", 380, qy + 40, "north")
    c.w((400, qy), (460, qy)); c.pin_out(f"{nome}_out", 460, qy, 8)
    # en = rst | (we & s), com s = sel (r1) ou ~sel (r0); OR com saída em (360,qy+90)
    oy = qy + 90
    c.comp(1, "OR Gate", 360, oy, size=30)           # in (330,oy-10) (330,oy+10)
    c.w((360, oy), (360, qy + 10), (370, qy + 10))
    c.w((330, oy + 10), (320, oy + 10), (320, oy + 30)); c.tunnel("rst", 320, oy + 30, "north")
    c.comp(1, "AND Gate", 310, oy - 10, size=30)     # in (280,oy-20) (280,oy)
    c.w((310, oy - 10), (330, oy - 10))
    c.tunnel("we", 260, oy - 20, "east"); c.w((260, oy - 20), (280, oy - 20))
    en_and_inputs(oy)

def sel_negado(oy):
    c.comp(1, "NOT Gate", 260, oy, size=20)          # in (240,oy)
    c.w((260, oy), (280, oy))
    c.tunnel("sel", 220, oy, "east"); c.w((220, oy), (240, oy))
def sel_direto(oy):
    c.tunnel("sel", 230, oy, "east"); c.w((230, oy), (280, oy))

registrador("r0", 110, sel_negado)
registrador("r1", 330, sel_direto)
c.aparencia("Etapa 1 · 2 registradores", "#dbeafe")
c.write_into(sys.argv[1])
