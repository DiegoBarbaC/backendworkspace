from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.json_util import dumps, ObjectId
from datetime import timedelta
from flask_jwt_extended import create_access_token

def init_auth_routes(app, mongo, bcrypt):
    @app.route('/register', methods=['POST'])
    def register():
        data = request.get_json()

        # Verificar que el correo y la contraseña están presentes en la solicitud
        email = data.get('email')
        password = data.get('password')
        editar = data.get('editar', False)
        admin = data.get('admin', False)

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

    @app.route('/login', methods=['POST'])
    def login():
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        user = mongo.db.usuarios.find_one({"email": email})

        if user and bcrypt.check_password_hash(user['password'], password):
            expires = timedelta(days=1)
            additional_claims = {
                "admin": user.get("admin", False),
                "editar": user.get("editar", False)   
            }
            access_token = create_access_token(
                identity=str(user["_id"]), 
                expires_delta=expires, 
                additional_claims=additional_claims
            )
            return jsonify(access_token=access_token), 200
        else:
            return jsonify({"msg": "Credenciales incorrectas"}), 401

    @app.route('/deleteUser', methods=['DELETE'])
    @jwt_required()
    def deleteUser():
        data = request.get_json()
        email = data.get('email')
        user = mongo.db.usuarios.find_one({"email": email})
        if user:
            result = mongo.db.usuarios.delete_one({"email": email})

        if result.deleted_count == 1:
            return jsonify({"msg": "Usuario eliminado correctamente"}), 200
        else:
            return jsonify({"msg": "Error al eliminar el usuario"}), 400

    @app.route('/updateUser', methods=['PUT'])
    @jwt_required()
    def updateUser():
        data = request.get_json()
        email = data.get('email')
        editar = data.get('editar')
        admin = data.get('admin')
        password = data.get('password')
        user = mongo.db.usuarios.find_one({"email": email})
        if user:
            update_data = {}
            if editar is not None:
                update_data['editar'] = bool(editar)
            if admin is not None:
                update_data['admin'] = bool(admin)
            if password:
                hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
                update_data['password'] = hashed_password
            if not update_data:
                return jsonify({"msg": "No se proporcionaron datos para actualizar"}), 400
            
            result = mongo.db.usuarios.update_one({"email": email}, {"$set": update_data})
            if result.modified_count == 1:
                return jsonify({"msg": "Usuario actualizado correctamente"}), 200
            else:
                return jsonify({"msg": "Error al actualizar el usuario"}), 400

    @app.route('/getAllUsers', methods=['GET'])
    @jwt_required()
    def get_all_users():
        current_user = get_jwt_identity()
        user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
        
        if not user or not user.get("admin", False):
            return jsonify({"msg": "Acceso denegado: se requiere rol de administrador"}), 403

        all_users = list(mongo.db.usuarios.find({}))
        user_list = dumps(all_users)
        
        return jsonify({"usuarios": user_list}), 200
