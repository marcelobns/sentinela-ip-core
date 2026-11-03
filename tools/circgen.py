"""Gerador de blocos <circuit> para Logisim-evolution 5.0.0 (coordenadas medidas pela API)."""
import re

ROTULO = re.compile(r"[A-Za-z][A-Za-z0-9_]*")   # o 5.0.0 renomeia rótulos fora disso (acento, espaço) ao abrir
from collections import namedtuple

PASSO = 20                      # distância entre portas na aparência personalizada
X0, Y0, CAB = 50, 50, 32        # canto da caixa e altura do cabeçalho (coordenadas da aparência)
Y1 = Y0 + CAB + 18              # linha da primeira porta; a âncora fica na primeira entrada

class Circ:
    def __init__(self, name, dx=60, dy=0):
        self.name, self.comps, self.wires = name, [], []
        self.dx, self.dy = dx, dy        # deslocamento global (mantém os pinos de 8 bits dentro da tela)
        self.pins, self.appear = [], None
    def comp(self, lib, name, x, y, **attrs):
        assert "label" not in attrs or ROTULO.fullmatch(str(attrs["label"])), f"rótulo inválido: {attrs['label']!r}"
        a = "".join(f'\n      <a name="{k}">{v}</a>' if k == "contents" else f'\n      <a name="{k}" val="{v}"/>'
                    for k, v in attrs.items())
        x, y = x + self.dx, y + self.dy
        lib_attr = "" if lib is None else f'lib="{lib}" '      # lib=None: subcircuito do próprio projeto
        self.comps.append(f'    <comp {lib_attr}loc="({x},{y})" name="{name}">{a}\n    </comp>')
    def w(self, *pts):
        """Fio poligonal: w((x1,y1),(x2,y2),...) — cada trecho é horizontal ou vertical."""
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            assert x1 == x2 or y1 == y2, (x1, y1, x2, y2)
            x1, x2, y1, y2 = x1 + self.dx, x2 + self.dx, y1 + self.dy, y2 + self.dy
            self.wires.append(f'    <wire from="({x1},{y1})" to="({x2},{y2})"/>')
    def pin_in(self, label, x, y, width=1):
        self.comp(0, "Pin", x, y, appearance="classic", label=label, width=width)
        self.pins.append(("in", label, x + self.dx, y + self.dy, width))
    def pin_out(self, label, x, y, width=1):
        self.comp(0, "Pin", x, y, appearance="classic", facing="west", output="true",
                  label=label, labelloc="east", width=width)
        self.pins.append(("out", label, x + self.dx, y + self.dy, width))
    def tunnel(self, label, x, y, facing, width=1):
        """facing=east: corpo à esquerda do ponto; west: à direita; north: abaixo; south: acima."""
        self.comp(0, "Tunnel", x, y, facing=facing, label=label, width=width)
    def const(self, x, y, width=1, value="0x0", facing="east"):
        self.comp(0, "Constant", x, y, facing=facing, width=width, value=value)
    def aparencia(self, subtitulo, cor):
        """Aparência personalizada: entradas à esquerda e saídas à direita, na ordem em que os pinos
        foram criados, uma a cada PASSO px. A âncora é a primeira entrada."""
        ins = [p for p in self.pins if p[0] == "in"]
        outs = [p for p in self.pins if p[0] == "out"]
        rot = lambda p: p[1] if p[4] == 1 else f"{p[1]}[{p[4] - 1}:0]"
        n = max(len(ins), len(outs))
        linhas = [(rot(ins[k]) if k < len(ins) else "", rot(outs[k]) if k < len(outs) else "") for k in range(n)]
        W = max([6 * (len(a) + len(b)) + 36 for a, b in linhas] + [8 * len(self.name) + 24, 6 * len(subtitulo) + 20, 80])
        W = -(-W // 10) * 10                         # múltiplo de 10: as saídas caem na grade
        H = CAB + 18 + PASSO * (n - 1) + 20
        cx = X0 + W // 2
        txt = lambda x, y, s, tam, ancora, peso="plain": (
            f'      <text dominant-baseline="central" font-family="SansSerif" font-size="{tam}" font-style="plain" '
            f'font-weight="{peso}" text-anchor="{ancora}" x="{x}" y="{y}">{s}</text>')
        # Sem <line>: no 5.0.0, Line.paint estoura NullPointerException ao desenhar a instância
        # (CircuitAppearance.paintSubcircuit passa gesture = null) e o canvas fica em branco.
        # A borda do retângulo do cabeçalho faz o papel da linha separadora.
        e = [f'      <rect fill="#ffffff" height="{H}" stroke="#ffffff" stroke-width="1" width="{W}" x="{X0}" y="{Y0}"/>',
             f'      <rect fill="{cor}" height="{CAB}" stroke="#000000" stroke-width="1" width="{W}" x="{X0}" y="{Y0}"/>',
             f'      <rect fill="none" height="{H}" stroke="#000000" stroke-width="2" width="{W}" x="{X0}" y="{Y0}"/>',
             txt(cx, Y0 + 11, self.name, 12, "middle", "bold"),
             txt(cx, Y0 + 24, subtitulo, 9, "middle")]
        for k, p in enumerate(ins):
            y = Y1 + PASSO * k
            if p[1] == "clk":                        # triângulo de relógio
                e.append(f'      <polyline fill="none" points="{X0},{y - 5} {X0 + 7},{y} {X0},{y + 5}" '
                         f'stroke="#000000" stroke-width="1"/>')
            e.append(txt(X0 + (10 if p[1] == "clk" else 6), y, rot(p), 10, "start"))
        for k, p in enumerate(outs):
            e.append(txt(X0 + W - 6, Y1 + PASSO * k, rot(p), 10, "end"))
        for k, p in enumerate(ins):
            e.append(f'      <circ-port dir="in" pin="{p[2]},{p[3]}" x="{X0}" y="{Y1 + PASSO * k}"/>')
        for k, p in enumerate(outs):
            e.append(f'      <circ-port dir="out" pin="{p[2]},{p[3]}" x="{X0 + W}" y="{Y1 + PASSO * k}"/>')
        e.append(f'      <circ-anchor facing="east" x="{X0}" y="{Y1}"/>')
        self.appear = "\n    <appear>\n" + "\n".join(e) + "\n    </appear>"
    def block(self):
        return f'  <circuit name="{self.name}">\n' + "\n".join(self.comps + self.wires) + "\n  </circuit>"
    def write_into(self, path):
        s = open(path).read()
        def repl(m):   # usa a aparência gerada; sem ela, preserva a que já existir (<appear>)
            ap = re.search(r"\n\s*<appear>.*?</appear>", m.group(0), re.S)
            ap = self.appear or (ap.group(0) if ap else "")
            return self.block().replace("\n  </circuit>", ap + "\n  </circuit>")
        s2, n = re.subn(rf'  <circuit name="{self.name}">.*?</circuit>', repl, s, flags=re.S)
        assert n == 1, f"circuito {self.name} não encontrado"
        open(path, "w").write(s2)
        print(f"{self.name}: {len(self.comps)} componentes, {len(self.wires)} fios")

Porta = namedtuple("Porta", "rotulo dx dy")
Geometria = namedtuple("Geometria", "entradas saidas")
def geometria(path, nome):
    """Portas de uma instância de `nome`, relativas à âncora, lidas da aparência gravada em `path`.
    Quem instancia um subcircuito usa isto em vez de coordenadas fixas."""
    bloco = re.search(rf'  <circuit name="{nome}">.*?</circuit>', open(path).read(), re.S).group(0)
    ap = re.search(r"<appear>.*?</appear>", bloco, re.S)
    assert ap, f"{nome} sem aparência personalizada: gere {nome} antes de quem o instancia"
    pinos = {loc: lab for loc, lab in re.findall(
        r'<comp lib="0" loc="\((\d+,\d+)\)" name="Pin">.*?<a name="label" val="([^"]*)"/>', bloco, re.S)}
    ax, ay = map(int, re.search(r'<circ-anchor[^>]*x="(\d+)" y="(\d+)"', ap.group(0)).groups())
    portas = {"in": [], "out": []}
    for d, pin, x, y in re.findall(r'<circ-port dir="(\w+)" pin="(\d+,\d+)" x="(\d+)" y="(\d+)"/>', ap.group(0)):
        portas[d].append(Porta(pinos[pin], int(x) - ax, int(y) - ay))
    return Geometria(*(sorted(portas[d], key=lambda p: p.dy) for d in ("in", "out")))
