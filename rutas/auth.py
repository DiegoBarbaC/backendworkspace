from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required
from model import mongo
from flask_bcrypt import Bcrypt
from datetime import timedelta


auth_bp = Blueprint("auth", __name__,)
bcrypt=Bcrypt()

@auth_bp.route("/login", methods=["POST"])
def login():
    data= request.get_json()
    email=data.get('email')
    password = data.get('password')
    print(password)

    user = mongo.db.usuarios.find_one({"email":email})
    print(user['password'])

    if user and bcrypt.check_password_hash(user['password'], password):
        expires = timedelta(days=1)
        additional_claims = {
        "admin": user.get("admin", False),
        "editar": user.get("editar", False)   
    }
        access_token = create_access_token(identity=str(user["_id"]), expires_delta=expires, additional_claims=additional_claims)
        
        return jsonify(access_token=access_token),200
    else:
        return jsonify({"msg":"Credenciales incorrectas"}), 401

#Ruta para registrar un nuevo usuario, se requiere jwt para crear un nuevo usuario
@auth_bp.route('/register', methods=['POST'])
@jwt_required()
def register():
    data = request.get_json()

    # Verificar que el correo y la contraseña están presentes en la solicitud
    email = data.get('email')
    password = data.get('password')
    editar=data.get('editar', False)
    admin=data.get('admin', False)

    if not email or not password:
        return jsonify({'message': 'Se requiere email y contraseña para crear el usuario'}), 400

    # Verificar si el correo ya está registrado
    if mongo.db.usuarios.find_one({'email': email}):
        return jsonify({'message': 'Este email ya tiene una cuenta creada, debe iniciar sesión'}), 400

    # Crear hash de la contraseña
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    # Obtener todas las secciones globales existentes para asignarlas al nuevo usuario
    secciones_globales = list(mongo.db.secciones_globales.find())
    secciones_usuario = [
        {"seccion_id": seccion['_id'], "orden": idx}
        for idx, seccion in enumerate(secciones_globales)
    ]

    result = mongo.db.usuarios.insert_one({
        "email": email,
        "password": hashed_password,
        "admin": admin,
        "editar": editar,
        "secciones": secciones_usuario
    })
    
    if result.acknowledged:
        return jsonify({"msg": "Usuario Creado Correctamente"}), 201
    else:
        return jsonify({"msg": "Hubo un error, no se pudieron guardar los datos"}), 400
        
