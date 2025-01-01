from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required
from model import mongo
from flask_bcrypt import Bcrypt
from datetime import timedelta
from flask_mail import Mail, Message
import random
import string


auth_bp = Blueprint("auth", __name__,)
bcrypt=Bcrypt()

def generate_random_password(length=12):
    # Caracteres para la contraseña
    characters = string.ascii_letters + string.digits + string.punctuation
    # Generar contraseña aleatoria
    password = ''.join(random.choice(characters) for i in range(length))
    return password

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
    from app import mail  # Importamos mail aquí para evitar importación circular
    
    data = request.get_json()

    # Verificar que el correo está presente en la solicitud
    email = data.get('email')
    editar = data.get('editar', False)
    admin = data.get('admin', False)

    if not email:
        return jsonify({'message': 'Se requiere email para crear el usuario'}), 400

    # Verificar si el correo ya está registrado
    if mongo.db.usuarios.find_one({'email': email}):
        return jsonify({'message': 'Este email ya tiene una cuenta creada, debe iniciar sesión'}), 400

    # Generar contraseña aleatoria
    password = generate_random_password()
    
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
        # Enviar correo con la contraseña
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
            # Si hay un error al enviar el correo, eliminamos el usuario creado
            mongo.db.usuarios.delete_one({"_id": result.inserted_id})
            return jsonify({"msg": f"Error al enviar el correo: {str(e)}"}), 500
    else:
        return jsonify({"msg": "Hubo un error, no se pudieron guardar los datos"}), 400
