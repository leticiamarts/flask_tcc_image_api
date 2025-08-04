import pytest
from unittest.mock import patch, MagicMock
from frontend.utils import montar_url, enviar_imagem


def test_montar_url_sem_parametros():
    base = "http://url:port/processar"
    operacao = "rotacionar"
    url = montar_url(base, operacao, {})
    assert url == "http://url:port/processar?operacao=rotacionar"


def test_montar_url_com_parametros():
    base = "http://url:port/processar"
    operacao = "brilho"
    params = {"brightness": 30, "extra": 5}
    url = montar_url(base, operacao, params)

    assert "operacao=brilho" in url
    assert "brightness=30" in url
    assert "extra=5" in url
    assert url.startswith("http://url:port/processar?")


@patch("frontend.utils.requests.post")
def test_enviar_imagem_sucesso(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"imagem"
    mock_post.return_value = mock_response

    url = "http://url:port/processar?operacao=brilho"
    imagem = MagicMock()
    response = enviar_imagem(url, imagem)

    mock_post.assert_called_once()
    assert response.status_code == 200
    assert response.content == b"imagem"


@patch("frontend.utils.requests.post")
def test_enviar_imagem_falha(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Erro interno"
    mock_post.return_value = mock_response

    url = "http://url:port/processar?operacao=brilho"
    imagem = MagicMock()
    response = enviar_imagem(url, imagem)

    assert response.status_code == 500
    assert "Erro" in response.text