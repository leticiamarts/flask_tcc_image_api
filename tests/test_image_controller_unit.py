import io
import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
from api.controllers.image_controller import image_bp

@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(image_bp)
    return app

@pytest.fixture
def client(app):
    return app.test_client()


def test_processar_no_image(client):
    response = client.post('/processar')
    assert response.status_code == 400
    assert "Nenhuma imagem enviada" in response.data.decode()


def test_processar_empty_file(client):
    data = {
        'image': (io.BytesIO(b''), '')
    }
    response = client.post('/processar', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert "Arquivo de imagem vazio" in response.data.decode()


@patch('api.controllers.image_controller.read_image_from_bytes', return_value=None)
def test_processar_invalid_image(mock_read_image, client):
    data = {
        'image': (io.BytesIO(b'test'), 'test.jpg')
    }
    response = client.post('/processar?operacao=rotacionar', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert "Erro: Imagem inválida ou não pôde ser lida." in response.data.decode()


@patch('api.controllers.image_controller.read_image_from_bytes')
@patch('api.controllers.image_controller.process_image')
@patch('api.controllers.image_controller.image_to_bytes')
def test_processar_success(mock_image_to_bytes, mock_process_image, mock_read_image, client):
    fake_image = b'fake_image_data'
    mock_read_image.return_value = 'fake_image_obj'
    mock_process_image.return_value = 'processed_image_obj'
    mock_image_to_bytes.return_value = io.BytesIO(b'jpg_binary_data')

    data = {
        'image': (io.BytesIO(b'test'), 'test.jpg')
    }

    response = client.post('/processar?operacao=brilho', data=data, content_type='multipart/form-data')

    mock_read_image.assert_called_once()
    mock_process_image.assert_called_once_with('fake_image_obj', 'brilho', {'operacao': 'brilho'})
    mock_image_to_bytes.assert_called_once_with('processed_image_obj')

    assert response.status_code == 200
    assert response.data.decode() == 'jpg_binary_data'
    assert response.headers['Content-Type'] == 'image/jpeg'


@patch('api.controllers.image_controller.read_image_from_bytes', return_value='fake_image_obj')
@patch('api.controllers.image_controller.process_image', return_value=None)
def test_processar_process_returns_none(mock_process_image, mock_read_image, client):
    data = {
        'image': (io.BytesIO(b'test'), 'test.jpg')
    }
    response = client.post('/processar?operacao=contraste', data=data, content_type='multipart/form-data')
    assert response.status_code == 500
    assert "Erro: O processamento retornou imagem vazia ou inválida." in response.data.decode()


@patch('api.controllers.image_controller.read_image_from_bytes', return_value='fake_image_obj')
@patch('api.controllers.image_controller.process_image', side_effect=Exception("Erro inesperado"))
def test_processar_process_raises_exception(mock_process_image, mock_read_image, client):
    data = {
        'image': (io.BytesIO(b'test'), 'test.jpg')
    }
    response = client.post('/processar?operacao=rotacionar', data=data, content_type='multipart/form-data')
    assert response.status_code == 500
    assert "Erro ao processar imagem: Erro inesperado" in response.data.decode()