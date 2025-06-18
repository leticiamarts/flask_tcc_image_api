import requests

def montar_url(base_url: str, operacao: str, params: dict) -> str:
    query = "&".join([f"{key}={int(val)}" for key, val in params.items()])
    return f"{base_url}?operacao={operacao}" + (f"&{query}" if query else "")

def enviar_imagem(url: str, imagem) -> requests.Response:
    files = {"image": imagem}
    return requests.post(url, files=files)
