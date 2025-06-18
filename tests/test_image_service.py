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
    # A imagem deve manter as mesmas dimensões
    assert rotated.shape == sample_image.shape
    # Não deve ser identica à original (a menos que imagem for simétrica)
    assert not np.array_equal(rotated, sample_image)


def test_scale_image(sample_image):
    scaled = image_service.scale_image(sample_image, 0.5, 0.5)
    # Dimensões esperadas
    assert scaled.shape[0] == sample_image.shape[0] // 2
    assert scaled.shape[1] == sample_image.shape[1] // 2


def test_adjust_brightness_contrast(sample_image):
    bright = image_service.adjust_brightness_contrast(sample_image, brightness=50)
    # Deve ser diferente da imagem original
    assert not np.array_equal(bright, sample_image)

    # Contraste
    contrast = image_service.adjust_brightness_contrast(sample_image, contrast=50)
    assert not np.array_equal(contrast, sample_image)


def test_add_noise(sample_image):
    noisy = image_service.add_noise(sample_image, mean=0, var=100)
    # A imagem com ruído deve ser diferente
    assert noisy.shape == sample_image.shape
    assert noisy.dtype == np.uint8
    assert not np.array_equal(noisy, sample_image)


def test_crop_image(sample_image):
    cropped = image_service.crop_image(sample_image, 10, 10, 20, 20)
    assert cropped.shape == (20, 20, 3)
    # Como a imagem é preta, o conteúdo será zero
    assert np.all(cropped == 0)


# Testando process_image

@patch('api.services.image_service.request')
def test_process_image_rotate(mock_request, sample_image):
    mock_request.args.get.side_effect = lambda k, default=None: 90 if k == 'angle' else default
    out = image_service.process_image(sample_image, 'rotacionar', mock_request.args)
    assert out.shape == sample_image.shape
    assert not np.array_equal(out, sample_image)


# PODE SUBSTITUI O TESTE ACIMA POR se achar mais apropriado:
#@patch('api.services.image_service.rotate_image')
#@patch('api.services.image_service.request')
#def test_process_image_rotate(mock_request, mock_rotate, sample_image):
#    mock_request.args.get.return_value = 90
#    mock_rotate.return_value = sample_image

#    result = image_service.process_image(sample_image, 'rotacionar', mock_request.args)
#    mock_rotate.assert_called_once_with(sample_image, 90)
#    assert np.array_equal(result, sample_image)
    


@patch('api.services.image_service.request')
def test_process_image_brightness(mock_request, sample_image):
    mock_request.args.get.side_effect = lambda k, default=None: 50 if k == 'brightness' else default
    out = image_service.process_image(sample_image, 'brilho', mock_request.args)
    assert out.shape == sample_image.shape
    assert not np.array_equal(out, sample_image)

# PODE SUBSTITUI O TESTE ACIMA POR se achar mais apropriado:
#@patch('api.services.image_service.adjust_brightness_contrast')
#@patch('api.services.image_service.request')
#def test_process_image_brightness(mock_request, mock_adjust, sample_image):
#    mock_request.args.get.return_value = 30
#    mock_adjust.return_value = sample_image

#    result = image_service.process_image(sample_image, 'brilho', mock_request.args)
#    mock_adjust.assert_called_once_with(sample_image, brightness=30, contrast=0)
#    assert np.array_equal(result, sample_image)


@patch('api.services.image_service.request')
def test_process_image_contrast(mock_request, sample_image):
    mock_request.args.get.side_effect = lambda k, default=None: 50 if k == 'contrast' else default
    out = image_service.process_image(sample_image, 'contraste', mock_request.args)
    assert out.shape == sample_image.shape
    assert not np.array_equal(out, sample_image)


# PODE SUBSTITUI O TESTE ACIMA POR se achar mais apropriado:
#@patch('api.services.image_service.adjust_brightness_contrast')
#@patch('api.services.image_service.request')
#def test_process_image_contrast(mock_request, mock_adjust, sample_image):
#    mock_request.args.get.return_value = 50
#    mock_adjust.return_value = sample_image

#    result = image_service.process_image(sample_image, 'contraste', mock_request.args)
#    mock_adjust.assert_called_once_with(sample_image, brightness=0, contrast=50)
#    assert np.array_equal(result, sample_image)


@patch('api.services.image_service.request')
def test_process_image_noise(mock_request, sample_image):
    mock_request.args.get.side_effect = lambda k, default=None: 625 if k == 'var' else default
    out = image_service.process_image(sample_image, 'ruido', mock_request.args)
    assert out.shape == sample_image.shape
    assert not np.array_equal(out, sample_image)


# PODE SUBSTITUI O TESTE ACIMA POR se achar mais apropriado:
#@patch('api.services.image_service.add_noise')
#@patch('api.services.image_service.request')
#def test_process_image_noise(mock_request, mock_noise, sample_image):
#    mock_request.args.get.return_value = 625
#    mock_noise.return_value = sample_image

#    result = image_service.process_image(sample_image, 'ruido', mock_request.args)
#    mock_noise.assert_called_once_with(sample_image, mean=0, var=625)
#    assert np.array_equal(result, sample_image)


@patch('api.services.image_service.request')
def test_process_image_crop(mock_request, sample_image):
    # x=10, y=10, w=20, h=20
    mock_request.args.get.side_effect = lambda k, default=None: {'x':10, 'y':10, 'w':20, 'h':20}.get(k, default)
    out = image_service.process_image(sample_image, 'recorte', mock_request.args)
    assert out.shape == (20, 20, 3)


# PODE SUBSTITUI O TESTE ACIMA POR se achar mais apropriado:
#@patch('api.services.image_service.crop_image')
#@patch('api.services.image_service.request')
#def test_process_image_crop(mock_request, mock_crop, sample_image):
#    mock_request.args.get.side_effect = lambda k, default=None: {
#        'x': 10, 'y': 10, 'w': 20, 'h': 20
#    }.get(k, default)
#    mock_crop.return_value = sample_image

#    result = image_service.process_image(sample_image, 'recorte', mock_request.args)
#    mock_crop.assert_called_once_with(sample_image, 10, 10, 20, 20)
#    assert np.array_equal(result, sample_image)


def test_process_image_invalid_operation(sample_image):
    with pytest.raises(ValueError, match="Operação inválida"):
        image_service.process_image(sample_image, 'operacao_invalida', {})

