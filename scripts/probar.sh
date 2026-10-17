#!/usr/bin/env bash
# Verifica el sistema desplegado: llegan lecturas de los 3 sensores, el panel
# las muestra, y al borrar el pod de Redis los datos siguen ahí y los sensores
# vuelven a escribir solos.
# "cond && ok ... || falla ..." es seguro aquí: ok solo imprime.
# shellcheck disable=SC2015
set -euo pipefail
NS=logistica-system
URL=${URL_PANEL:-http://localhost:30081}
ok() { printf 'ok   %s\n' "$*"; }
falla() { printf 'MAL  %s\n' "$*"; exit 1; }
redis_cli() {
  kubectl -n "$NS" exec deploy/redis -- sh -c "redis-cli --no-auth-warning -a \"\$REDIS_PASSWORD\" $*"
}

sleep 8
sensores=$(redis_cli HLEN sensor:latest)
[ "$sensores" -eq 3 ] && ok "3 sensores publicando" || falla "hay $sensores sensores"
antes=$(redis_cli LLEN sensor:data)
[ "$antes" -gt 3 ] && ok "$antes lecturas guardadas" || falla "casi no hay lecturas ($antes)"

panel=$(curl -sf "$URL/api/lecturas")
[ "$(echo "$panel" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["sensores"]))')" -eq 3 ] \
  && ok "el panel muestra los 3 sensores" || falla "el panel no muestra los sensores"
curl -sf "$URL/" | grep -q "Monitoreo de sensores" && ok "la página del panel responde" || falla "la página no responde"

# Sin la clave, Redis no deja leer.
kubectl -n "$NS" exec deploy/redis -- redis-cli LLEN sensor:data 2>&1 | grep -q NOAUTH \
  && ok "Redis rechaza a quien no tiene la clave" || falla "Redis responde sin clave"

ultima=$(redis_cli LINDEX sensor:data -1)
kubectl -n "$NS" delete pod -l app=redis --wait=true >/dev/null
kubectl -n "$NS" rollout status deployment/redis --timeout=180s >/dev/null
for _ in $(seq 30); do redis_cli PING 2>/dev/null | grep -q PONG && break; sleep 1; done
despues=$(redis_cli LLEN sensor:data)
[ "$despues" -ge "$antes" ] && ok "tras borrar el pod de Redis siguen $despues lecturas (antes $antes)" || falla "se perdieron datos: $antes -> $despues"
[ "$(redis_cli LINDEX sensor:data -1)" = "$ultima" ] && ok "la lectura más vieja sigue igual" || falla "cambió el historial"

sleep 12
nuevas=$(redis_cli LLEN sensor:data)
[ "$nuevas" -gt "$despues" ] && ok "los sensores volvieron a escribir solos ($despues -> $nuevas)" || falla "los sensores no se reconectaron"
reinicios=$(kubectl -n "$NS" get pods -l app=sensor -o jsonpath='{range .items[*]}{.status.containerStatuses[0].restartCount}{"\n"}{end}' | awk '{s += $1} END {print s + 0}')
[ "$reinicios" -eq 0 ] && ok "sin reinicios de los sensores (reintentan en vez de caerse)" || falla "los sensores se reiniciaron $reinicios veces"
