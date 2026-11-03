#!/usr/bin/env bash
# Regera todos os subcircuitos de sentinela.circ a partir dos scripts build_*.py e roda o lint.
# Cada script substitui só o bloco <circuit> do seu subcircuito e preserva a aparência
# personalizada (<appear>), se houver.
#
# Uso:  tools/regenerar.sh [projeto.circ]     (padrão: sentinela.circ)
set -euo pipefail
cd "$(dirname "$0")/.."

CIRC="${1:-sentinela.circ}"
for b in regs2 alu8 fir4 fsm core main; do
  python3 -I "tools/build_$b.py" "$CIRC"
done
tools/lint.sh "$CIRC"
