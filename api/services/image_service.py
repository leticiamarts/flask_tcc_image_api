import cv2
import numpy as np
from flask import request
from api.utils.image_utils import image_to_bytes

def rotate_image(image, angle):
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h))
    return rotated

def scale_image(image, scale_x, scale_y):
    scaled = cv2.resize(image, None, fx=scale_x, fy=scale_y, interpolation=cv2.INTER_LINEAR)
    return scaled

def adjust_brightness_contrast(image, brightness=0, contrast=0):
    beta = brightness
    alpha = 1 + contrast / 100.0
    adjusted = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
    return adjusted

def add_noise(image, mean=0, var=10):
    sigma = var ** 0.5
    gauss = np.random.normal(mean, sigma, image.shape).astype('float32')
    noisy = cv2.add(image.astype('float32'), gauss)
    noisy = np.clip(noisy, 0, 255).astype('uint8')
    return noisy

def crop_image(image, x, y, w, h):
    cropped = image[y:y+h, x:x+w]
    return cropped

def process_image(img, operacao, params):
    if operacao == 'rotacionar':
            angle = int(params.get('angle', 0))
            img = rotate_image(img, angle)

    elif operacao == 'brilho':
        brightness = int(params.get('brightness', 0))
        img = adjust_brightness_contrast(img, brightness=brightness)

    elif operacao == 'contraste':
        contrast = int(params.get('contrast', 0))
        img = adjust_brightness_contrast(img, contrast=contrast)

    elif operacao == 'ruido':
        var = int(params.get('var', 0))
        img = add_noise(img, mean=0, var=var)

    elif operacao == 'recorte':
        x = int(params.get('x', 0))
        y = int(params.get('y', 0))
        w = int(params.get('w', 0))
        h = int(params.get('h', 0))
        img = crop_image(img, x, y, w, h)

    else:
        raise ValueError("Operação inválida")

    print("[debug]")
    return img