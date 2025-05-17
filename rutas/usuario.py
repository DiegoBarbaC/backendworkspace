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
    
    if not user or not user.get("admin", False):
        return jsonify({"msg": "Acceso denegado: se requiere rol de administrador"}), 403

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