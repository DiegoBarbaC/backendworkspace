from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from model import mongo
from flask_bcrypt import Bcrypt
from datetime import timedelta
from flask_mail import Message
import random
import string
from bson import ObjectId


auth_bp = Blueprint("auth", __name__,)
bcrypt=Bcrypt()

def generate_random_password(length=7):
    # Caracteres para la contraseña
    characters = string.ascii_letters + string.digits 
    # Generar contraseña aleatoria
    password = ''.join(random.choice(characters) for i in range(length))
    return password

@auth_bp.route("/login", methods=["POST"])
def login():
    data= request.get_json()
    email=data.get('email')
    password = data.get('password')

    user = mongo.db.usuarios.find_one({"email":email})
    

    if user and bcrypt.check_password_hash(user['password'], password):
        # Crear access token con duración más corta (15 minutos)
        access_expires = timedelta(minutes=15)
        # Crear refresh token con duración más larga (7 días)
        refresh_expires = timedelta(days=7)
        
        additional_claims = {
            "admin": user.get("admin", False),
            "editar": user.get("editar", False), 
        }
        
        # Generar access token
        access_token = create_access_token(
            identity=str(user["_id"]), 
            expires_delta=access_expires, 
            additional_claims=additional_claims
        )
        
        # Generar refresh token
        refresh_token = create_refresh_token(
            identity=str(user["_id"]),
            expires_delta=refresh_expires
        )
        
        return jsonify(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=str(user["_id"]),
            admin=user.get("admin", False),
            editar=user.get("editar", False)
        ), 200
    else:
        return jsonify({"msg":"Credenciales incorrectas"}), 401

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """
    Endpoint para refrescar el access token usando el refresh token
    """
    # Obtener la identidad del usuario desde el refresh token
    current_user_id = get_jwt_identity()
    
    # Buscar el usuario en la base de datos para obtener sus claims
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user_id)})
    
    if not user:
        return jsonify({"msg": "Usuario no encontrado"}), 404
    
    # Crear un nuevo access token
    additional_claims = {
        "admin": user.get("admin", False),
        "editar": user.get("editar", False), 
    }
    
    access_token = create_access_token(
        identity=current_user_id,
        expires_delta=timedelta(minutes=15),
        additional_claims=additional_claims
    )
    
    return jsonify(access_token=access_token), 200

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Endpoint para cerrar sesión (invalidar tokens)
    """
    # En una implementación completa, aquí se añadiría el token a una lista negra
    # Por ahora, solo devolvemos un mensaje de éxito
    return jsonify({"msg": "Sesión cerrada exitosamente"}), 200


@auth_bp.route('/register', methods=['POST'])
@jwt_required()
def register():
    from app import mail  
    
    data = request.get_json()

    email = data.get('email')
    editar = data.get('editar', False)
    admin = data.get('admin', False)

    if not email:
        return jsonify({'message': 'Se requiere email para crear el usuario'}), 400

    if mongo.db.usuarios.find_one({'email': email}):
        return jsonify({'message': 'Este email ya tiene una cuenta creada, debe iniciar sesión'}), 400

    password = generate_random_password()
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

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
        try:
            msg = Message(
                'Bienvenido al Workspace CAA - Tus credenciales de acceso',
                recipients=[email]
            )
            msg.html = f"""
            <h2>Bienvenido al Workspace CAA</h2>
            <p>Tu cuenta ha sido creada exitosamente. Aquí están tus credenciales de acceso:</p>
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Contraseña:</strong> {password}</p>
            <p>Por favor, cambia tu contraseña después de iniciar sesión por primera vez.</p>
            <p>¡Gracias por unirte a nosotros!</p>
            """
            mail.send(msg)
            return jsonify({"msg": "Usuario Creado Correctamente y correo enviado"}), 201
        except Exception as e:
            mongo.db.usuarios.delete_one({"_id": result.inserted_id})
            return jsonify({"msg": f"Error al enviar el correo: {str(e)}"}), 500
    else:
        return jsonify({"msg": "Hubo un error, no se pudieron guardar los datos"}), 400
