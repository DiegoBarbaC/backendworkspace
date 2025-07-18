from flask import Flask, request, jsonify, Blueprint
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



app = Flask(__name__)
app.config.from_object(config)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
CORS(app)
mail = Mail(app)


from rutas.auth import auth_bp
from rutas.usuario import usuario_bp
from rutas.secciones import secciones_bp
from rutas.eventos import eventos_bp
from rutas.notas import notas_bp

# Crear un blueprint principal para /api
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Registrar los blueprints en el blueprint principal
api_bp.register_blueprint(auth_bp)
api_bp.register_blueprint(usuario_bp)
api_bp.register_blueprint(secciones_bp)
api_bp.register_blueprint(eventos_bp)
api_bp.register_blueprint(notas_bp)

# Registrar el blueprint principal en la app
app.register_blueprint(api_bp)

#Inicializamos el acceso a MongoDB
init_db(app)
fs = gridfs.GridFS(mongo.db)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
    
