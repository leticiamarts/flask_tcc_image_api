#!/bin/bash
set -e

CLUSTER_NAME="local-cluster"

echo "[INFO] Verificando pré-requisitos..."

if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker não está instalado. Por favor, instale e reinicie o script."
    exit 1
fi

if ! command -v k3d &> /dev/null; then
    echo "[INFO] Instalando k3d..."
    curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash
fi

if ! command -v kubectl &> /dev/null; then
    echo "[INFO] Instalando kubectl..."
    curl -LO "https://dl.k8s.io/release/$(curl -sL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    chmod +x kubectl
    sudo mv kubectl /usr/local/bin/
fi

if ! command -v ngrok &> /dev/null; then
    echo "[INFO] ngrok não encontrado. Instale manualmente de https://ngrok.com/download ou adicione ao PATH."
    exit 1
fi

echo "[INFO] Criando cluster local com k3d..."
k3d cluster create $CLUSTER_NAME --servers 1 --agents 1 \
    -p "8000:80@loadbalancer" -p "8501:8501@loadbalancer" \
    --k3s-arg "--disable=traefik@server:*" || {
    echo "[INFO] Cluster já existe ou erro ao criar. Tentando reutilizar cluster existente..."
}

echo "[INFO] Aguardando o cluster iniciar..."
sleep 10

echo "[INFO] Rotulando nodes para ingress-nginx..."
kubectl label node k3d-$CLUSTER_NAME-server-0 ingress-ready=true || true
kubectl label node k3d-$CLUSTER_NAME-agent-0 ingress-ready=true || true

echo "[INFO] Instalando ingress-nginx..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.12.3/deploy/static/provider/kind/deploy.yaml

echo "[INFO] Aguardando o Ingress NGINX ficar pronto..."
kubectl wait --namespace ingress-nginx \
  --for=condition=Ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s

echo "[INFO] Aplicando seus arquivos do Kubernetes..."
kubectl apply -f k8s/flask-deployment.yaml
kubectl apply -f k8s/flask-service.yaml
kubectl apply -f k8s/streamlit-deployment.yaml
kubectl apply -f k8s/streamlit-service.yaml
kubectl apply -f k8s/ingress.yaml

echo "[INFO] Cluster e Kubernetes aplicados com sucesso!"
