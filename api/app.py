from flask import Flask
from controllers.image_controller import image_bp

def create_app():
    app = Flask(__name__)
    app.register_blueprint(image_bp)
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
