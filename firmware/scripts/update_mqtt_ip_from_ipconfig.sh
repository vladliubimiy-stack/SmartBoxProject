#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ADAPTER_NAME="${ADAPTER_NAME:-Ethernet 2}"
CONFIG_FILE="${CONFIG_FILE:-${REPO_ROOT}/include/config.h}"
EXAMPLE_FILE="${EXAMPLE_FILE:-${REPO_ROOT}/include/config_example.h}"

if ! command -v ipconfig >/dev/null 2>&1; then
  echo "Ошибка: команда ipconfig не найдена. Запускай скрипт в Windows (PowerShell/CMD/Git Bash)." >&2
  exit 1
fi

MQTT_IP="$(LC_ALL=C ipconfig | LC_ALL=C awk -v adapter="${ADAPTER_NAME}" '
  BEGIN { in_target = 0 }
  { line = $0; sub(/\r$/, "", line) }

  (!in_target) && index(line, adapter) > 0 && line ~ /:[[:space:]]*$/ { in_target = 1; next }
  in_target && index(line, adapter) == 0 && line ~ /^[[:space:]]*[^[:space:]].*:[[:space:]]*$/ { in_target = 0 }

  in_target {
    if (match(line, /([0-9]{1,3}\.){3}[0-9]{1,3}/)) {
      print substr(line, RSTART, RLENGTH); exit
    }
  }
')"

if [[ -z "${MQTT_IP}" ]]; then
  echo "Ошибка: не удалось найти IPv4 у адаптера '${ADAPTER_NAME}'. Проверь имя адаптера в ipconfig." >&2
  exit 1
fi

if [[ ! -f "${CONFIG_FILE}" ]]; then
  if [[ -f "${EXAMPLE_FILE}" ]]; then
    cp "${EXAMPLE_FILE}" "${CONFIG_FILE}"
  else
    echo "Ошибка: не найден ${CONFIG_FILE} и ${EXAMPLE_FILE}." >&2
    exit 1
  fi
fi

TMP_FILE="$(mktemp)"
awk -v ip="${MQTT_IP}" '
  BEGIN { updated = 0 }
  {
    line = $0
    sub(/\r$/, "", line)
    if (line ~ /^[[:space:]]*#define[[:space:]]+MQTT_HOST[[:space:]]+/) {
      print "#define MQTT_HOST \"" ip "\""; updated = 1
    } else {
      print line
    }
  }
  END {
    if (!updated) {
      print ""
      print "// Автоматически обновляется scripts/update_mqtt_ip_from_ipconfig.sh"
      print "#define MQTT_HOST \"" ip "\""
    }
  }
' "${CONFIG_FILE}" > "${TMP_FILE}"
mv "${TMP_FILE}" "${CONFIG_FILE}"

echo "MQTT_HOST обновлён: ${MQTT_IP} (${CONFIG_FILE})"
