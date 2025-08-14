# API de Processamento de Imagem




### Run experiments:
#### Selenium on-prem no-autoscaling
```bash
python run_experiments.py --env onprem --autoscaling false --load_type selenium --url https_url--image img_complete_url --n 100 --sleep 0.1
```

#### Requests on-prem no-autoscaling
```bash
python run_experiments.py --env onprem --autoscaling false --load_type requests --url https_url --total 500 --concurrency 20
```