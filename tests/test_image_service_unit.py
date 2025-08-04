import pytest
import numpy as np
import cv2
from unittest.mock import patch, MagicMock
from api.services import image_service

@pytest.fixture
def sample_image():
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    for i in range(100):
        img[:, i, 0] = i * 255 // 99
        img[:, i, 2] = 255 - img[:, i, 0] 
    return img


def test_rotate_image(sample_image):
    rotated = image_service.rotate_image(sample_image, 90)
    assert rotated.shape == sample_image.shape
    # Não deve ser identica à original (a menos que imagem for simétrica)
    assert not np.array_equal(rotated, sample_image)


def test_scale_image(sample_image):
    scaled = image_service.scale_image(sample_image, 0.5, 0.5)
    assert scaled.shape[0] == sample_image.shape[0] // 2
    assert scaled.shape[1] == sample_image.shape[1] // 2


def test_adjust_brightness_contrast(sample_image):
    bright = image_service.adjust_brightness_contrast(sample_image, brightness=50)
    assert not np.array_equal(bright, sample_image)

    contrast = image_service.adjust_brightness_contrast(sample_image, contrast=50)
    assert not np.array_equal(contrast, sample_image)


def test_add_noise(sample_image):
    noisy = image_service.add_noise(sample_image, mean=0, var=100)
    assert noisy.shape == sample_image.shape
    assert noisy.dtype == np.uint8
    assert not np.array_equal(noisy, sample_image)


def test_crop_image(sample_image):
    cropped = image_service.crop_image(sample_image, 10, 10, 20, 20)
    assert cropped.shape == (20, 20, 3)


def test_process_image_rotate(sample_image):
    params = {'angle': 90}
    out = image_service.process_image(sample_image, 'rotacionar', params)
    assert out.shape == sample_image.shape
    assert not np.array_equal(out, sample_image)
    

def test_process_image_brightness(sample_image):
    params = {'brightness': 50}
    out = image_service.process_image(sample_image, 'brilho', params)
    assert out.shape == sample_image.shape
    assert not np.array_equal(out, sample_image)


def test_process_image_contrast(sample_image):
    params = {'contrast': 50}
    out = image_service.process_image(sample_image, 'contraste', params)
    assert out.shape == sample_image.shape
    assert not np.array_equal(out, sample_image)


def test_process_image_noise(sample_image):
    params = {'mean': 0, 'var': 625}
    out = image_service.process_image(sample_image, 'ruido', params)
    assert out.shape == sample_image.shape
    assert not np.array_equal(out, sample_image)


def test_process_image_crop(sample_image):
    params = {'x': 10, 'y': 10, 'w': 20, 'h': 20}
    out = image_service.process_image(sample_image, 'recorte', params)
    assert out.shape == (20, 20, 3)


def test_process_image_invalid_operation(sample_image):
    with pytest.raises(ValueError, match="Operação inválida"):
        image_service.process_image(sample_image, 'operacao_invalida', {})
