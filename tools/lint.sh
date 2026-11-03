#!/usr/bin/env bash
# Verifica o layout dos circuitos: componentes sobrepostos, fios atravessando componentes,
# junções em T acidentais e pontas de fio soltas.
#
# Uso:  tools/lint.sh [projeto.circ]       (padrão: sentinela.circ)
set -euo pipefail
cd "$(dirname "$0")/.."

JAR="${LOGISIM_JAR:-/Applications/Logisim-evolution.app/Contents/app/logisim-evolution-5.0.0-all.jar}"
CIRC="${1:-sentinela.circ}"
[[ -f "$JAR" ]] || { echo "Logisim não encontrado em $JAR (defina LOGISIM_JAR)"; exit 2; }

dump="$(mktemp)"; trap 'rm -f "$dump"' EXIT
java -cp "$JAR" tools/Dump.java "$CIRC" main alu8 regs2 fir4 intertravamento sentinela_core >"$dump"
python3 -I tools/lint.py "$dump"
