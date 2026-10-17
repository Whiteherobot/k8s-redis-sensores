#!/usr/bin/env bash
# Construye las imágenes, las carga en el clúster local (kind o minikube),
# crea el Secret con una clave aleatoria y aplica los manifiestos.
set -euo pipefail
cd "$(dirname "$0")/.."
NS=logistica-system

docker build -q -t logistica/sensor:1.0 apps/sensor >/dev/null
docker build -q -t logistica/panel:1.0 apps/panel >/dev/null

contexto=$(kubectl config current-context)
case "$contexto" in
  kind-*) for i in sensor panel; do kind load docker-image "logistica/$i:1.0" --name "${contexto#kind-}" >/dev/null; done ;;
  minikube) for i in sensor panel; do minikube image load "logistica/$i:1.0"; done ;;
  *) echo "Contexto $contexto: las imágenes logistica/* tienen que estar en un registro accesible" ;;
esac

kubectl apply -f k8s/00-namespace.yaml >/dev/null
# La clave se genera una sola vez; si el Secret ya existe se conserva.
if ! kubectl -n "$NS" get secret redis-credentials >/dev/null 2>&1; then
  kubectl -n "$NS" create secret generic redis-credentials \
    --from-literal=redis-password="$(head -c 24 /dev/urandom | base64 | tr -d '/+=')" >/dev/null
fi
kubectl apply -f k8s/ >/dev/null
for d in redis sensor panel; do
  kubectl -n "$NS" rollout status "deployment/$d" --timeout=180s >/dev/null
done
kubectl -n "$NS" get pods
echo "Panel: http://<IP del nodo>:30081 (con kind y scripts/kind.yaml: http://localhost:30081)"
