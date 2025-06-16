from flask import Flask, request, jsonify, send_file
import cv2
import numpy as np
import io

app = Flask(__name__)

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
    # brightness: -100 to 100
    # contrast: -100 to 100
    beta = brightness
    alpha = 1 + contrast / 100.0
    adjusted = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
    return adjusted

def add_noise(image, mean=0, var=10):
    # Gaussian noise
    sigma = var ** 0.5
    gauss = np.random.normal(mean, sigma, image.shape).astype('float32')
    noisy = cv2.add(image.astype('float32'), gauss)
    noisy = np.clip(noisy, 0, 255).astype('uint8')
    return noisy

def crop_image(image, x, y, w, h):
    cropped = image[y:y+h, x:x+w]
    return cropped


def read_image_from_bytes(file_bytes):
    nparr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

def image_to_bytes(image):
    is_success, buffer = cv2.imencode(".jpg", image)
    if not is_success:
        raise ValueError("Falha ao codificar imagem.")
    return io.BytesIO(buffer)


@app.route('/processar', methods=['POST'])
def processar():
    operacao = request.args.get('operacao', default='rotacionar')
    if 'image' not in request.files:
        return "Nenhuma imagem enviada", 400

    file = request.files['image']
    img = read_image_from_bytes(file.read())

    try:
        if operacao == 'rotacionar':
            angle = int(request.args.get('angle', 90))
            img = rotate_image(img, angle)

        elif operacao == 'brilho':
            brightness = int(request.args.get('brightness', 30))
            img = adjust_brightness_contrast(img, brightness=brightness, contrast=0)

        elif operacao == 'contraste':
            contrast = int(request.args.get('contrast', 50))
            img = adjust_brightness_contrast(img, brightness=0, contrast=contrast)

        elif operacao == 'ruido':
            var = int(request.args.get('var', 625))  # 25² = 625
            img = add_noise(img, mean=0, var=var)

        elif operacao == 'recorte':
            x = int(request.args.get('x', img.shape[1] // 4))
            y = int(request.args.get('y', img.shape[0] // 4))
            w = int(request.args.get('w', img.shape[1] // 2))
            h = int(request.args.get('h', img.shape[0] // 2))
            img = crop_image(img, x, y, w, h)

        else:
            return "Operação inválida", 400
    except Exception as e:
        return f"Erro ao processar imagem: {str(e)}", 500

    return send_file(
        image_to_bytes(img),
        mimetype='image/jpeg',
        as_attachment=False
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


