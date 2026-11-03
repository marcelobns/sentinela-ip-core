"""Lint de layout para circuitos Logisim: uso  python3 lint.py <dump.txt>"""
import sys
def parse(path):
    circs, cur = {}, None
    for line in open(path):
        t = line.split()
        if not t: continue
        if t[0] == "CIRCUIT": cur = circs.setdefault(t[1], {"comps": [], "wires": []})
        elif t[0] == "COMP": cur["comps"].append({"name": t[1], "b": tuple(map(int, t[2:6])), "loc": (int(t[6]), int(t[7])), "label": t[8], "ends": []})
        elif t[0] == "END": cur["comps"][-1]["ends"].append((int(t[1]), int(t[2])))
        elif t[0] == "WIRE": cur["wires"].append(tuple(map(int, t[1:5])))
    return circs
def on_seg(p, w, strict=True):
    x, y = p; x1, y1, x2, y2 = w
    if x1 == x2 == x and min(y1, y2) <= y <= max(y1, y2): inside = True
    elif y1 == y2 == y and min(x1, x2) <= x <= max(x1, x2): inside = True
    else: return False
    return not (strict and p in ((x1, y1), (x2, y2)))
def seg_hits_rect(w, r, pad=1):
    x1, y1, x2, y2 = w; rx, ry, rw, rh = r
    ax0, ax1, ay0, ay1 = rx + pad, rx + rw - pad, ry + pad, ry + rh - pad
    sx0, sx1, sy0, sy1 = min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)
    return sx0 <= ax1 and sx1 >= ax0 and sy0 <= ay1 and sy1 >= ay0
def rects_overlap(a, b, pad=1):
    return a[0] + pad < b[0] + b[2] and b[0] + pad < a[0] + a[2] and a[1] + pad < b[1] + b[3] and b[1] + pad < a[1] + a[3]
def lint(name, c):
    errs = []
    ports = [(e, comp) for comp in c["comps"] for e in comp["ends"]]
    wend = [p for w in c["wires"] for p in ((w[0], w[1]), (w[2], w[3]))]
    for w in c["wires"]:
        for p, comp in ports:
            if on_seg(p, w): errs.append(f"porta de {comp['name']}({comp['label']}) em {p} no meio do fio {w}")
        for p in wend:
            if on_seg(p, w): errs.append(f"ponta de fio {p} no meio do fio {w} (junção em T)")
        for comp in c["comps"]:
            x1, y1, x2, y2 = w
            for (ex, ey) in comp["ends"]:          # fio ligado a uma porta: ignora 10 px junto à porta (ex.: seleção do mux na borda inclinada)
                if (x1, y1) == (ex, ey): x1 += (10 if x2 > x1 else -10 if x2 < x1 else 0); y1 += (10 if y2 > y1 else -10 if y2 < y1 else 0)
                if (x2, y2) == (ex, ey): x2 += (10 if x1 > x2 else -10 if x1 < x2 else 0); y2 += (10 if y1 > y2 else -10 if y1 < y2 else 0)
            if seg_hits_rect((x1, y1, x2, y2), comp["b"]): errs.append(f"fio {w} atravessa {comp['name']}({comp['label']}) {comp['b']}")
    cs = c["comps"]
    for i in range(len(cs)):
        for j in range(i + 1, len(cs)):
            if rects_overlap(cs[i]["b"], cs[j]["b"]):
                errs.append(f"{cs[i]['name']}({cs[i]['label']}) sobrepõe {cs[j]['name']}({cs[j]['label']})")
    # pontas soltas: ponta de fio que não toca porta nem outro fio
    pts = [p for p, _ in ports]
    for p in wend:
        if p not in pts and wend.count(p) < 2 and not any(on_seg(p, w) for w in c["wires"]):
            errs.append(f"ponta de fio solta em {p}")
    for e in sorted(set(errs)): print(f"  [{name}] {e}")
    return len(set(errs))
circs = parse(sys.argv[1]); assert circs and all(v["comps"] for v in circs.values()), "dump vazio"
n = sum(lint(k, v) for k, v in circs.items())
print(f"lint: {n} problema(s)")
sys.exit(1 if n else 0)
