$ErrorActionPreference = "Stop"

$CLUSTER_NAME = "local-cluster"

Write-Host "[INFO] Verificando pré-requisitos..."

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "[ERROR] Docker não está instalado. Por favor, instale e reinicie o script."
    exit 1
}

if (-not (Get-Command k3d -ErrorAction SilentlyContinue)) {
    Write-Host "[INFO] Instalando k3d..."
    Invoke-WebRequest -Uri "https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh" -OutFile "install_k3d.sh"
    wsl bash install_k3d.sh
}

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "[INFO] Instalando kubectl..."
    $kubectlUrl = "https://dl.k8s.io/release/$(Invoke-RestMethod https://dl.k8s.io/release/stable.txt)/bin/windows/amd64/kubectl.exe"
    Invoke-WebRequest -Uri $kubectlUrl -OutFile "kubectl.exe"
    Move-Item .\kubectl.exe "C:\Program Files\kubectl.exe" -Force
    $env:Path += ";C:\Program Files\"
}

if (-not (Get-Command ngrok -ErrorAction SilentlyContinue)) {
    Write-Error "[INFO] ngrok não encontrado. Instale manualmente de https://ngrok.com/download ou adicione ao PATH."
    exit 1
}

Write-Host "[INFO] Criando cluster local com k3d..."
try {
    k3d cluster create $CLUSTER_NAME --servers 1 --agents 1 `
        -p "8000:80@loadbalancer" -p "8501:8501@loadbalancer" `
        --k3s-arg "--disable=traefik@server:*"
} catch {
    Write-Host "[INFO] Cluster já existe ou erro ao criar. Tentando reutilizar cluster existente..."
}

Start-Sleep -Seconds 10

Write-Host "[INFO] Rotulando nodes para ingress-nginx..."
kubectl label node "k3d-$CLUSTER_NAME-server-0" ingress-ready=true -o json | Out-Null
kubectl label node "k3d-$CLUSTER_NAME-agent-0" ingress-ready=true -o json | Out-Null

Write-Host "[INFO] Instalando ingress-nginx..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.12.3/deploy/static/provider/kind/deploy.yaml

Write-Host "[INFO] Aguardando o Ingress NGINX ficar pronto..."
kubectl wait --namespace ingress-nginx `
  --for=condition=Ready pod `
  --selector=app.kubernetes.io/component=controller `
  --timeout=90s

Write-Host "[INFO] Aplicando seus arquivos do Kubernetes..."
kubectl apply -f ./k8s/

Write-Host "[INFO] Expondo sua aplicação na internet com ngrok..."
ngrok http 8000
