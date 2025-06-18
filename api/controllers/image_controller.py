from flask import Blueprint, request, send_file
from api.services.image_service import process_image
from api.utils.image_utils import read_image_from_bytes, image_to_bytes

image_bp = Blueprint('image', __name__)

@image_bp.route('/processar', methods=['POST'])
def processar():
    operacao = request.args.get('operacao', default='rotacionar')
    if 'image' not in request.files:
        return "Nenhuma imagem enviada", 400
    
    file = request.files['image']
    if file.filename == '':
        return "Arquivo de imagem vazio.", 400
    
    img = read_image_from_bytes(file.read())
    if img is None:
        return "Erro: Imagem inválida ou não pôde ser lida.", 400

    try:
        params = request.args.to_dict()
        img = process_image(img, operacao, params)
        if img is None:
            return "Erro: O processamento retornou imagem vazia ou inválida.", 500
    except Exception as e:
        return f"Erro ao processar imagem: {str(e)}", 500

    return send_file(
        image_to_bytes(img),
        mimetype='image/jpeg',
        as_attachment=False
    )