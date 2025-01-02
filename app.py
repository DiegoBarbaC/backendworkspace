from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from model import mongo, init_db
from config import config
from bson.json_util import ObjectId
from flask_bcrypt import Bcrypt
from flask_jwt_extended import get_jwt_identity
from bson import ObjectId, Binary
from datetime import timedelta
from bson.json_util import dumps
from flask_cors import CORS
from flask_mail import Mail
import gridfs
import base64

from rutas.auth import auth_bp
from rutas.usuario import usuario_bp
from rutas.secciones import secciones_bp
from rutas.eventos import eventos_bp

app = Flask(__name__)
app.config.from_object(config)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
CORS(app)
mail = Mail(app)

app.register_blueprint(auth_bp)
app.register_blueprint(usuario_bp)
app.register_blueprint(secciones_bp)
app.register_blueprint(eventos_bp)

#Inicializamos el acceso a MongoDB
init_db(app)
fs = gridfs.GridFS(mongo.db)


if __name__ == '__main__':
    app.run(debug=True)
