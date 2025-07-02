import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from models import db
import logging
from logging.handlers import RotatingFileHandler

def create_app():
    app = Flask(__name__)

    CORS(app, origins=["http://example.com", "http://example.org"],
         methods=["GET", "POST", "PUT", "DELETE"],
         allow_headers=["Content-Type", "Authorization"],
         supports_credentials=True)

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_TOKEN_LOCATION'] = ['cookies']
    app.config['JWT_COOKIE_CSRF_PROTECT'] = True
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600
    app.config['JWT_SECRET_KEY'] = os.urandom(24).hex()
    app.config['SECRET_KEY'] = os.urandom(24).hex()

    db.init_app(app)
    jwt = JWTManager(app)

    logging.basicConfig(level=logging.DEBUG, filename='app.log', filemode='w',
                        format='%(asctime)s - %(levelname)s - %(message)s')
    handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)

    from routes import configure_routes
    configure_routes(app)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
