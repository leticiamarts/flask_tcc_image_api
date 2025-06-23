#!/bin/bash
set -e

apt-get update -y
apt-get install -y docker.io docker-compose git curl

systemctl enable docker
systemctl start docker

curl -sfL https://get.k3s.io | sh -


git clone https://github.com/leticiamarts/flask_tcc_image_api.git /home/ubuntu/app


until k3s kubectl get node &>/dev/null; do
  echo "Aguardando K3s iniciar..."
  sleep 5
done

#if [ -f /home/ubuntu/app/k8s/deployment.yaml ]; then
#  /usr/local/bin/kubectl apply -f /home/ubuntu/app/k8s/
#fi
# troquei o de cima pelo comando abaixo

k3s kubectl apply -f /home/ubuntu/app/k8s/

#cd /home/ubuntu/app

#docker-compose up -d
