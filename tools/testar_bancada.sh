#!/usr/bin/env bash
# Testa o `main` numa cópia de bancada: o Test Vector não aciona Clock nem Buttons, então a
# cópia troca esses componentes por pinos (o resto do circuito é idêntico) e roda o vetor
# gerado por tools/vet_main.py. O sentinela.circ do repositório não é alterado.
#
# Uso:  tools/testar_bancada.sh
set -euo pipefail
cd "$(dirname "$0")/.."

JAR="${LOGISIM_JAR:-/Applications/Logisim-evolution.app/Contents/app/logisim-evolution-5.0.0-all.jar}"
[[ -f "$JAR" ]] || { echo "Logisim não encontrado em $JAR (defina LOGISIM_JAR)"; exit 2; }

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
cp sentinela.circ "$tmp/bancada.circ"
python3 -I tools/build_main.py "$tmp/bancada.circ" --bancada >/dev/null
python3 -I tools/vet_main.py "$tmp/test_main_bancada.txt"
java -jar "$JAR" --test-vector main "$tmp/test_main_bancada.txt" "$tmp/bancada.circ" >"$tmp/log" 2>&1 || true
resumo="$(grep -Eo 'Passed: ?[0-9]+, ?Failed: ?[0-9]+' "$tmp/log" | tail -1)"
[[ -n "$resumo" ]] || { cat "$tmp/log"; echo "ERRO ao rodar o vetor de bancada"; exit 1; }
echo "main (bancada): $resumo"
[[ "$resumo" =~ Failed:\ ?0$ ]]
