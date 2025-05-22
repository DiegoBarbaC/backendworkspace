from flask import Blueprint, jsonify, request, Flask
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from model import mongo, init_db
from config import config
from bson.json_util import ObjectId
from flask_bcrypt import Bcrypt
from flask_jwt_extended import get_jwt_identity
from bson import ObjectId, Binary
from datetime import timedelta
from bson.json_util import dumps

notas_bp = Blueprint("notas", __name__,)

#Ruta para obtener las notas en las que participa el usuario
@notas_bp.route("/notes", methods=["GET"])
@jwt_required()
def get_notas():
    current_user = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
    if not user:
        return jsonify({"msg": "Usuario no encontrado"}), 404
    else:
        try:
            notas = mongo.db.notas.find({"usuarios": current_user})
            return dumps(notas)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

#Ruta para crear una nueva nota
@notas_bp.route("/createNote", methods=["POST"])
@jwt_required()
def create_note():
    current_user = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
    if not user:
        return jsonify({"msg": "Usuario no encontrado"}), 404
    else:
        try:
            data = request.get_json()
            titulo = data.get("titulo")
            contenido = data.get("contenido", "<p><br></p>")  # Contenido inicial con formato Quill válido
            usuarios = data.get("usuarios")
            creador = user['_id']
            
            # Insertar la nota y obtener el ID
            result = mongo.db.notas.insert_one({"creador": creador, "titulo": titulo, "contenido": contenido, "usuarios": usuarios})
            note_id = str(result.inserted_id)
            
            return jsonify({"msg": "Nota creada correctamente", "id": note_id}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

#Ruta para obtener una nota por su ID
@notas_bp.route("/getNote/<note_id>", methods=["GET"])
@jwt_required()
def get_note(note_id):
    current_user = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
    if not user:
        return jsonify({"msg": "Usuario no encontrado"}), 404
    else:
        try:
            note = mongo.db.notas.find_one({"_id": ObjectId(note_id)})
            if note:
                # Convertir ObjectId a string para JSON
                note['_id'] = str(note['_id'])
                if 'creador' in note:
                    note['creador'] = str(note['creador'])
                if 'usuarios' in note and isinstance(note['usuarios'], list):
                    note['usuarios'] = [str(uid) if isinstance(uid, ObjectId) else uid for uid in note['usuarios']]
                return jsonify(note)
            else:
                return jsonify({"error": "Nota no encontrada"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

#Ruta para actualizar el contenido de una nota
@notas_bp.route("/updateNote/<note_id>", methods=["PUT"])
@jwt_required()
def update_note(note_id):
    current_user = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
    if not user:
        return jsonify({"msg": "Usuario no encontrado"}), 404
    else:
        try:
            data = request.get_json()
            contenido = data.get("contenido")
            
            note = mongo.db.notas.find_one({"_id": ObjectId(note_id)})
            if not note:
                return jsonify({"msg": "Nota no encontrada"}), 404
            elif current_user not in note['usuarios']:
                return jsonify({"msg": "No tienes permiso para editar esta nota"}), 403
            else:
                mongo.db.notas.update_one({"_id": ObjectId(note_id)}, {"$set": {"contenido": contenido}})
                return jsonify({"msg": "Nota actualizada correctamente"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

#Ruta para eliminar una nota
@notas_bp.route("/deleteNote/<note_id>", methods=["DELETE"])
@jwt_required()
def delete_note(note_id):
    current_user = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
    if not user:
        return jsonify({"msg": "Usuario no encontrado"}), 404
    else:
        try:
            note = mongo.db.notas.find_one({"_id": ObjectId(note_id)})
            if not note:
                return jsonify({"msg": "Nota no encontrada"}), 404
            elif str(note['creador']) != current_user:
                return jsonify({"msg": "Solo el creador puede eliminar esta nota"}), 403
            else:
                mongo.db.notas.delete_one({"_id": ObjectId(note_id)})
                return jsonify({"msg": "Nota eliminada correctamente"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
