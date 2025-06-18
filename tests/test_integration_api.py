# tests/test_integration_api.py

import io
import pytest
from PIL import Image
from api.app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def generate_image_bytes():
    image = Image.new("RGB", (100, 100), color="red")
    byte_io = io.BytesIO()
    image.save(byte_io, format='JPEG')
    byte_io.seek(0)
    return byte_io


def test_process_image_endpoint(client):
    image_data = generate_image_bytes()
    data = {
        "image": (image_data, "test.jpg")
    }

    response = client.post("/processar?operacao=rotacionar&angle=90", content_type='multipart/form-data', data=data)

    assert response.status_code == 200
    assert response.content_type in ["image/jpeg", "image/png"]
    assert response.data != b""
