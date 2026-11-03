#!/usr/bin/env bash
# Roda os Test Vectors de todos os subcircuitos pela linha de comando do Logisim.
#
# Uso:  scripts/rodar_testes.sh            # todos
#       scripts/rodar_testes.sh fir4       # só um subcircuito
#
# Variáveis: LOGISIM_JAR (caminho do .jar), CIRC (padrão: sentinela.circ)
#
# Atenção: o Logisim-evolution 5.0.0 sai com código 0 mesmo com falhas,
# então este script lê a linha "Passed: X, Failed: Y" para decidir.
set -uo pipefail

cd "$(dirname "$0")/.."

JAR="${LOGISIM_JAR:-/Applications/Logisim-evolution.app/Contents/app/logisim-evolution-5.0.0-all.jar}"
CIRC="${CIRC:-sentinela.circ}"
LOGS="tests/resultados"

# subcircuito:arquivo
PARES=(
  "alu8:test_alu8.txt"
  "regs2:test_regs2.txt"
  "fir4:test_fir4.txt"
  "intertravamento:test_fsm.txt"
  "sentinela_core:test_sentinela.txt"
)

[[ -f "$JAR" ]]  || { echo "Logisim não encontrado em $JAR (defina LOGISIM_JAR)"; exit 2; }
[[ -f "$CIRC" ]] || { echo "Projeto $CIRC não encontrado"; exit 2; }
command -v java >/dev/null || { echo "java não está no PATH"; exit 2; }
mkdir -p "$LOGS"

falhou=0
printf "%-18s %-22s %s\n" "subcircuito" "vetor" "resultado"
for par in "${PARES[@]}"; do
  circ="${par%%:*}"; vetor="${par#*:}"
  [[ $# -gt 0 && "$circ" != "$1" ]] && continue
  log="$LOGS/${circ}.log"
  java -jar "$JAR" --test-vector "$circ" "tests/$vetor" "$CIRC" >"$log" 2>&1
  resumo="$(grep -Eo 'Passed: ?[0-9]+, ?Failed: ?[0-9]+' "$log" | tail -1)"
  if [[ -z "$resumo" ]]; then
    printf "%-18s %-22s %s\n" "$circ" "$vetor" "ERRO (veja $log)"
    falhou=1
  else
    nfalhas="$(sed -E 's/.*Failed: ?([0-9]+).*/\1/' <<<"$resumo")"
    marca="OK"; [[ "$nfalhas" != "0" ]] && { marca="FALHOU"; falhou=1; }
    printf "%-18s %-22s %s  [%s]\n" "$circ" "$vetor" "$resumo" "$marca"
  fi
done
echo "Logs detalhados em $LOGS/"
exit $falhou
