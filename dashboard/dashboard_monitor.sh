#!/bin/bash
set -e

echo "[INFO] Instalando Kubernetes Dashboard..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml

echo "[INFO] Aguardando namespace 'kubernetes-dashboard' ficar disponível..."
kubectl wait --namespace kubernetes-dashboard \
  --for=condition=Ready pod \
  --selector=k8s-app=kubernetes-dashboard \
  --timeout=90s

echo "[INFO] Aplicando o usuário admin do dashboard..."
kubectl apply -f dashboard/dashboard-admin-user.yaml

echo "[INFO] Iniciando proxy local para acesso ao dashboard..."
nohup kubectl proxy > /dev/null 2>&1 &

DASHBOARD_URL="http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/"
echo "[✅] Dashboard disponível em:"
echo "$DASHBOARD_URL"
echo
echo "[🔐] Token de acesso:"
kubectl -n kubernetes-dashboard create token admin-user
