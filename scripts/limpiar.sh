#!/usr/bin/env bash
# Borra el namespace con todo (incluido el volumen de Redis).
set -euo pipefail
kubectl delete namespace logistica-system --wait=true
