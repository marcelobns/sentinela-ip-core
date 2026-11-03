"""Células reutilizáveis (layout fixo, conexões só por tunnels)."""
def gate2(c, kind, a, b, out, X, Y):
    """Porta de 2 entradas com saída em (X+150,Y)."""
    c.comp(1, f"{kind} Gate", X + 150, Y, size=30)
    c.tunnel(a, X + 100, Y - 10, "east"); c.w((X + 100, Y - 10), (X + 120, Y - 10))
    xb = min(X + 20, X + 100 - (8 * len(a) + 9) - 10) // 10 * 10   # afasta conforme o rótulo de a
    c.tunnel(b, xb, Y + 10, "east"); c.w((xb, Y + 10), (X + 120, Y + 10))
    c.w((X + 150, Y), (X + 170, Y)); c.tunnel(out, X + 170, Y, "west")
def not1(c, a, out, X, Y):
    c.comp(1, "NOT Gate", X + 150, Y, size=20)
    c.tunnel(a, X + 100, Y, "east"); c.w((X + 100, Y), (X + 130, Y))
    c.w((X + 150, Y), (X + 170, Y)); c.tunnel(out, X + 170, Y, "west")
def sync_reg(c, d, q, X, Y, width=8, en=None, clr="rst", label=None):
    """Registrador com reset síncrono: D = clr ? 0 : d; grava quando en (ou sempre, se en=None)."""
    c.tunnel(d, X + 80, Y - 10, "east", width); c.w((X + 80, Y - 10), (X + 110, Y - 10))
    c.comp(2, "Multiplexer", X + 140, Y, width=width)
    c.const(X + 100, Y + 10, width=width); c.w((X + 100, Y + 10), (X + 110, Y + 10))
    c.w((X + 120, Y + 20), (X + 120, Y + 40)); c.tunnel(clr, X + 120, Y + 40, "north")
    c.w((X + 140, Y), (X + 170, Y))
    c.comp(4, "Register", X + 200, Y, appearance="classic", width=width, label=label or f"reg_{q}")
    if en:
        c.w((X + 170, Y + 10), (X + 150, Y + 10), (X + 150, Y + 70)); c.tunnel(en, X + 150, Y + 70, "north")
    c.w((X + 180, Y + 20), (X + 180, Y + 40)); c.tunnel("clk", X + 180, Y + 40, "north")
    c.w((X + 200, Y), (X + 220, Y)); c.tunnel(q, X + 220, Y, "west", width)
def split2(c, src, lo, hi, X, Y, width, lo_w, hi_w):
    """Separa src em (lo, hi). Splitter em (X,Y)."""
    bits = {f"bit{k}": (0 if k < lo_w else 1) for k in range(width)}
    c.tunnel(src, X - 20, Y, "east", width); c.w((X - 20, Y), (X, Y))
    c.comp(0, "Splitter", X, Y, fanout=2, incoming=width, **bits)
    c.w((X + 20, Y - 20), (X + 40, Y - 20)); c.tunnel(lo, X + 40, Y - 20, "west", lo_w)
    c.w((X + 20, Y - 10), (X + 30, Y - 10), (X + 30, Y + 20), (X + 40, Y + 20)); c.tunnel(hi, X + 40, Y + 20, "west", hi_w)
def join2(c, lo, hi, dst, X, Y, width, lo_w, hi_w):
    """Junta (lo, hi) em dst. Splitter voltado para oeste com a saída em (X,Y)."""
    bits = {f"bit{k}": (0 if k < lo_w else 1) for k in range(width)}
    c.comp(0, "Splitter", X, Y, facing="west", fanout=2, incoming=width, **bits)
    c.tunnel(lo, X - 40, Y + 10, "east", lo_w); c.w((X - 40, Y + 10), (X - 20, Y + 10))
    c.tunnel(hi, X - 60, Y + 50, "east", hi_w); c.w((X - 60, Y + 50), (X - 30, Y + 50), (X - 30, Y + 20), (X - 20, Y + 20))
    c.w((X, Y), (X + 20, Y)); c.tunnel(dst, X + 20, Y, "west", width)
def soma_const(c, a, out, X, Y, width, k=1):
    """out = a + k (Adder com saída em (X,Y), carry-in = 0)."""
    c.comp(3, "Adder", X, Y, width=width)
    c.tunnel(a, X - 60, Y - 10, "east", width); c.w((X - 60, Y - 10), (X - 40, Y - 10))
    c.const(X - 50, Y + 10, width=width, value=hex(k)); c.w((X - 50, Y + 10), (X - 40, Y + 10))
    c.const(X - 20, Y - 30, facing="south"); c.w((X - 20, Y - 30), (X - 20, Y - 20))
    c.w((X, Y), (X + 20, Y)); c.tunnel(out, X + 20, Y, "west", width)
def alu_add(c, g, a, b, y, X, Y, carry=None):
    """Instância de alu8 em modo ADD (op = 00) com a âncora (porta a) em (X,Y); g = geometria("alu8")."""
    p = {q.rotulo: q for q in g.entradas + g.saidas}
    assert p["a"].dx == p["b"].dx == p["op"].dx == 0 and p["a"].dy == 0, "alu8: entradas fora da coluna da âncora"
    yb, yop, xo = Y + p["b"].dy, Y + p["op"].dy, X + p["y"].dx
    c.comp(None, "alu8", X, Y)
    c.tunnel(a, X - 80, Y - 30, "east", 8); c.w((X - 80, Y - 30), (X - 20, Y - 30), (X - 20, Y), (X, Y))
    c.tunnel(b, X - 80, yop + 40, "east", 8); c.w((X - 80, yop + 40), (X - 40, yop + 40), (X - 40, yb), (X, yb))
    c.const(X - 20, yop + 30, width=2, facing="north"); c.w((X - 20, yop + 30), (X - 20, yop), (X, yop))
    c.w((xo, Y + p["y"].dy), (xo + 20, Y + p["y"].dy)); c.tunnel(y, xo + 20, Y + p["y"].dy, "west", 8)
    if carry:
        yc = Y + p["carry"].dy
        c.w((xo, yc), (xo + 20, yc), (xo + 20, yc + 30)); c.tunnel(carry, xo + 20, yc + 30, "north")

def fanin(c, px, py0, fontes, tx=None, passo=10):
    """Liga tunnels a portas de entrada empilhadas em (px, py0 + passo·k), com trilhos sem cruzamento.
    fontes: lista de (rótulo, largura); metade de cima sobe, metade de baixo desce."""
    n = len(fontes); m = (n + 1) // 2
    tx = tx if tx is not None else px - 30 - 10 * n - 60
    for k, (rot, wd) in enumerate(fontes):
        yk = py0 + passo * k
        if k < m:
            lane, ty = px - 20 - 10 * k, py0 - 40 * (m - k)
        else:
            j = n - 1 - k
            lane, ty = px - 20 - 10 * (m + j), py0 + passo * (n - 1) + 40 * (k - m + 1)
        c.tunnel(rot, tx, ty, "east", wd)
        c.w((tx, ty), (lane, ty), (lane, yk), (px, yk))
def fanout(c, qx, qy0, destinos, tx=None, passo=10):
    """Espelho de fanin para portas de saída empilhadas em (qx, qy0 + passo·k)."""
    n = len(destinos); m = (n + 1) // 2
    tx = tx if tx is not None else qx + 30 + 10 * n + 20
    for k, (rot, wd) in enumerate(destinos):
        yk = qy0 + passo * k
        if k < m:
            lane, ty = qx + 20 + 10 * k, qy0 - 40 * (m - k)
        else:
            j = n - 1 - k
            lane, ty = qx + 20 + 10 * (m + j), qy0 + passo * (n - 1) + 40 * (k - m + 1)
        c.w((qx, yk), (lane, yk), (lane, ty), (tx, ty))
        c.tunnel(rot, tx, ty, "west", wd)
def instancia(c, g, nome, X, Y, entradas, saidas):
    """Subcircuito `nome` com a âncora em (X,Y), ligado por tunnels.
    entradas/saidas: (rótulo do pino, tunnel, largura), na ordem das portas de cima para baixo."""
    for portas, lig in ((g.entradas, entradas), (g.saidas, saidas)):
        assert [p.rotulo for p in portas] == [r for r, _, _ in lig], (nome, portas, lig)
        dys = [p.dy for p in portas]
        assert len({p.dx for p in portas}) == 1 and all(b - a == dys[1] - dys[0] for a, b in zip(dys, dys[1:])), \
            f"{nome}: portas fora de uma coluna regular"
    passo = lambda ps: ps[1].dy - ps[0].dy if len(ps) > 1 else 10
    c.comp(None, nome, X, Y)
    pi, po = g.entradas, g.saidas
    fanin(c, X + pi[0].dx, Y + pi[0].dy, [(t, w) for _, t, w in entradas], passo=passo(pi))
    fanout(c, X + po[0].dx, Y + po[0].dy, [(t, w) for _, t, w in saidas], passo=passo(po))
