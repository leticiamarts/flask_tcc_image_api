#!/bin/bash
set -e

CLUSTER_NAME="local-cluster"

echo "[INFO] Criando cluster local com k3d..."
k3d cluster create $CLUSTER_NAME --servers 1 --agents 1 -p "8000:80@loadbalancer" -p "8501:8501@loadbalancer"

echo "[INFO] Aguardando o cluster iniciar..."
sleep 10

echo "[INFO] Aplicando deployments e services..."
kubectl apply -f ./k8s/

echo "[INFO] Instalando ingress-nginx..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.0/deploy/static/provider/k3d/deploy.yaml
