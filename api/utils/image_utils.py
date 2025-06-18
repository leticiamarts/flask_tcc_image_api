import numpy as np
import cv2
import io

def read_image_from_bytes(file_bytes):
    nparr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

def image_to_bytes(image):
    is_success, buffer = cv2.imencode(".jpg", image)
    if not is_success:
        raise ValueError("Falha ao codificar imagem.")
    return io.BytesIO(buffer)
