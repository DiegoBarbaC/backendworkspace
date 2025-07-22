from flask import Blueprint, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from model import mongo, init_db
from config import config
from bson.json_util import ObjectId, dumps, loads
from flask_bcrypt import Bcrypt
from flask_jwt_extended import get_jwt_identity
from bson import ObjectId, Binary
from datetime import timedelta
from flask_cors import CORS
import base64

usuario_bp = Blueprint("usuario", __name__,)
bcrypt=Bcrypt()

#Ruta para eliminar un usuario
@usuario_bp.route('/deleteUser', methods=['DELETE'])
@jwt_required()
def deleteUser():
    data=request.get_json()
    email=data.get('email')
    user = mongo.db.usuarios.find_one({"email":email})
    if (user):
        if(user['admin']):
            existingAdmins=mongo.db.usuarios.count_documents({"admin": True})
            if existingAdmins == 1:
                return jsonify({"msg": "No se puede eliminar el único administrador"}), 400
            else:
                result = mongo.db.usuarios.delete_one({"email":email})
        else:
            result = mongo.db.usuarios.delete_one({"email":email})
    else:
        return jsonify({"msg": "Usuario no encontrado"}), 404
        
    if result.deleted_count == 1:
        return jsonify({"msg": "Usuario eliminado correctamente"}), 200
    else:
        return jsonify({"msg": "Error al eliminar el usuario"}), 400

#Ruta para actualizar un usuario    
@usuario_bp.route ('/updateUser', methods=['PUT'])
@jwt_required()
def updateUser():
    email = request.form.get('email')
    editar = request.form.get('editar')
    admin = request.form.get('admin')
    password = request.form.get('password')
    fechaCumple = request.form.get('fechaCumple')
    foto = request.files.get('foto')
    
    user = mongo.db.usuarios.find_one({"email":email})
    if (user):
        update_data = {}
        if editar is not None:
            update_data['editar'] = editar.lower() == 'true'
        if admin is not None:
            update_data['admin'] = admin.lower() == 'true'
        if password:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            update_data['password'] = hashed_password
        if fechaCumple:
            update_data['fechaCumple'] = fechaCumple
        if foto:
            update_data['foto'] = Binary(foto.read())
        
        if not update_data:
            return jsonify({"msg": "No se proporcionaron datos para actualizar"}), 400
        
        print("Datos a actualizar:", update_data)
        result = mongo.db.usuarios.update_one({"email": email}, {"$set": update_data})
        print("Documentos modificados:", result.modified_count)
        
        if result.modified_count == 1:
            return jsonify({"msg": "Usuario actualizado correctamente"}), 200
        else:
            return jsonify({"msg": "Error al actualizar el usuario"}), 400
    
    return jsonify({"msg": "Usuario no encontrado"}), 404

#Ruta para obtener todos los usuarios
@usuario_bp.route('/getAllUsers', methods=['GET'])
@jwt_required()  # Requiere autenticación
def get_all_users():
    #Verifica si el usuario actual tiene permiso de admin
    current_user = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})

    # Recupera todos los usuarios de la colección
    all_users = list(mongo.db.usuarios.find({}))
    
    # Serializa la lista de usuarios en formato JSON
    user_list = dumps(all_users)
    
    return jsonify({"usuarios": user_list}), 200

#Ruta para obtener un usuario
@usuario_bp.route('/getUser/<user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    current_user = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
    
    if not user:
        return jsonify({"msg": "Usuario no encontrado"}), 404

    # Buscar el usuario por ID
    retrievedUser = mongo.db.usuarios.find_one({"_id": ObjectId(user_id)})
    
    if not retrievedUser:
        return jsonify({"msg": "Usuario no encontrado"}), 404
    
        
    # Preparar la respuesta
    user_data = {
        "email": retrievedUser['email'],
        "admin": retrievedUser['admin'],
        "editar": retrievedUser['editar'],
    
    }
    if retrievedUser.get('foto'):
        user_data['foto'] = base64.b64encode(retrievedUser['foto']).decode('utf-8')
    if retrievedUser.get('fechaCumple'):
        user_data['fechaCumple'] = retrievedUser['fechaCumple']
    return jsonify(user_data), 200

#Ruta para obtener usuarios para notas (sin restricción de admin)
@usuario_bp.route('/getUsersForNotes', methods=['GET'])
@jwt_required()
def get_users_for_notes():
    try:
        current_user = get_jwt_identity()
        print(f"Usuario solicitando lista: {current_user}")
        
        # Recupera todos los usuarios de la colección (campos básicos solamente)
        users = list(mongo.db.usuarios.find({}, {"_id": 1, "email": 1, "nombre": 1}))
        print(f"Usuarios encontrados: {len(users)}")
        
        # Transformar ObjectId a string para JSON
        for user in users:
            user["_id"] = str(user["_id"])
        
        return jsonify(users), 200
    except Exception as e:
        print(f"Error en getUsersForNotes: {str(e)}")
        return jsonify({"msg": f"Error al obtener usuarios: {str(e)}"}), 500

#Ruta para obtener proximo cumpleaños
@usuario_bp.route('/getBirthday', methods=['GET'])
@jwt_required()
def get_birthday():
    try:
        from datetime import datetime, timedelta
        
        # Obtener la fecha actual
        today = datetime.now()
        current_month = today.month
        current_day = today.day
        
        # Buscar todos los usuarios que tienen fecha de cumpleaños
        users = list(mongo.db.usuarios.find({"fechaCumple": {"$exists": True}}))
        
        if not users:
            return jsonify({"msg": "No hay usuarios con fecha de cumpleaños registrada"}), 404
        
        next_birthday = None
        next_birthday_user = None
        days_until_next_birthday = 366  # Más de un año
        
        for user in users:
            if "fechaCumple" not in user or not user["fechaCumple"]:
                continue
                
            # Parsear la fecha de cumpleaños (formato esperado: YYYY-MM-DD)
            try:
                birthday = datetime.strptime(user["fechaCumple"], "%Y-%m-%d")
                
                # Crear fecha de cumpleaños para el año actual
                birthday_this_year = datetime(today.year, birthday.month, birthday.day)
                
                # Si el cumpleaños ya pasó este año, considerar el del próximo año
                if birthday_this_year < today:
                    birthday_this_year = datetime(today.year + 1, birthday.month, birthday.day)
                
                # Calcular días hasta el próximo cumpleaños
                delta = (birthday_this_year - today).days
                
                # Actualizar si este es el próximo cumpleaños
                if delta < days_until_next_birthday:
                    days_until_next_birthday = delta
                    next_birthday = birthday_this_year
                    next_birthday_user = user
            except ValueError:
                # Si el formato de fecha no es válido, ignorar este usuario
                continue
        
        if next_birthday_user:
            # Preparar respuesta con datos del usuario
            user_data = {
                "email": next_birthday_user.get("email", ""),
                "nombre": next_birthday_user.get("nombre", ""),
                "fechaCumple": next_birthday_user.get("fechaCumple", ""),
                "proximoCumple": next_birthday.strftime("%Y-%m-%d"),
                "diasRestantes": days_until_next_birthday
            }
            
            # Agregar foto si existe
            if next_birthday_user.get('foto'):
                user_data['foto'] = base64.b64encode(next_birthday_user['foto']).decode('utf-8')
                
            return jsonify(user_data), 200
        else:
            return jsonify({"msg": "No se pudo determinar el próximo cumpleaños"}), 404
            
    except Exception as e:
        print(f"Error en get_birthday: {str(e)}")
        return jsonify({"msg": f"Error al obtener el próximo cumpleaños: {str(e)}"}), 500