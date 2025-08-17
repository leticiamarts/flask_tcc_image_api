#!/bin/bash
set -euo pipefail

echo "[INFO] Instalando Kubernetes Dashboard (v2.7.0)..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml

echo "[INFO] Aguardando pods do namespace 'kubernetes-dashboard'..."
kubectl wait --namespace kubernetes-dashboard \
  --for=condition=Ready pod \
  --selector=k8s-app=kubernetes-dashboard \
  --timeout=120s

echo "[INFO] Aplicando ServiceAccount + ClusterRoleBinding do admin..."
kubectl apply -f dashboard/dashboard-admin-user.yaml

# Inicia proxy se não houver um rodando
if ! pgrep -f "kubectl proxy" >/dev/null 2>&1; then
  echo "[INFO] Iniciando kubectl proxy em background..."
  nohup kubectl proxy > /dev/null 2>&1 &
  sleep 1
fi

DASHBOARD_URL="http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/"
echo "[✅] Dashboard disponível em:"
echo "$DASHBOARD_URL"
echo
echo "[🔐] Token (válido por tempo limitado):"
kubectl -n kubernetes-dashboard create token admin-user || true

cat << 'TIP'

[ D I C A ]
- Se quiser abrir o dashboard, acesse a URL acima e use o token impresso.
- Para iniciar o monitor de métricas em paralelo ao seu teste:
  
  # (requer Python e 'pip install kubernetes')
  python dashboard/dashboard_monitor.py \
    --namespace default \
    --deployment-name flask-api \
    --label-selector app=flask-api \
    --interval 1.0 \
    --duration 180 \
    --scenario sem_hpa \
    --out results/monitor_sem_hpa.ndjson

- Em outra janela, rode o seu run_experiments.py normalmente.
TIP
