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

#Ruta para actualizar una nota (contenido, título o usuarios)
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
            update_fields = {}
            
            # Verificar qué campos se están actualizando
            if "contenido" in data:
                update_fields["contenido"] = data.get("contenido")
            
            if "titulo" in data:
                update_fields["titulo"] = data.get("titulo")
            
            # Obtener la nota para verificar permisos
            note = mongo.db.notas.find_one({"_id": ObjectId(note_id)})
            if not note:
                return jsonify({"msg": "Nota no encontrada"}), 404
            
            # Verificar si se está actualizando la lista de usuarios
            if "usuarios" in data:
                # Solo el creador puede modificar la lista de usuarios
                if str(note.get('creador', '')) != current_user:
                    return jsonify({"msg": "Solo el creador puede modificar la lista de usuarios"}), 403
                
                new_users = data.get("usuarios", [])
                if not isinstance(new_users, list):
                    return jsonify({"msg": "El campo 'usuarios' debe ser una lista"}), 400
                
                # Validar que los usuarios existan
                valid_users = []
                invalid_users = []
                
                for user_id in new_users:
                    try:
                        # Verificar si el ID es válido
                        if not ObjectId.is_valid(user_id):
                            invalid_users.append(user_id)
                            continue
                        
                        # Verificar si el usuario existe
                        user_exists = mongo.db.usuarios.find_one({"_id": ObjectId(user_id)})
                        if user_exists:
                            valid_users.append(user_id)
                        else:
                            invalid_users.append(user_id)
                    except Exception:
                        invalid_users.append(user_id)
                
                # Asegurarse de que el creador siempre esté en la lista de usuarios
                creator_id = str(note.get('creador', ''))
                if creator_id and creator_id not in valid_users:
                    valid_users.append(creator_id)
                
                if invalid_users:
                    return jsonify({"msg": "Algunos usuarios no son válidos", "invalid_users": invalid_users}), 400
                
                # Actualizar la lista de usuarios
                update_fields["usuarios"] = valid_users
            
            # Si no hay campos para actualizar, devolver error
            if not update_fields:
                return jsonify({"msg": "No se proporcionaron campos para actualizar"}), 400
            
            # Para actualizaciones de contenido o título, verificar que el usuario esté en la lista de usuarios
            if "usuarios" not in data and current_user not in note.get('usuarios', []):
                return jsonify({"msg": "No tienes permiso para editar esta nota"}), 403
            
            # Realizar la actualización
            mongo.db.notas.update_one({"_id": ObjectId(note_id)}, {"$set": update_fields})
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

#Ruta para agregar usuarios a una nota
@notas_bp.route("/addUsers/<note_id>", methods=["POST"])
@jwt_required()
def add_users_to_note(note_id):
    current_user = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
    if not user:
        return jsonify({"msg": "Usuario no encontrado"}), 404
    else:
        try:
            # Obtener la nota
            note = mongo.db.notas.find_one({"_id": ObjectId(note_id)})
            if not note:
                return jsonify({"msg": "Nota no encontrada"}), 404
            
            # Verificar que el usuario actual sea el creador de la nota
            if str(note['creador']) != current_user:
                return jsonify({"msg": "Solo el creador puede agregar usuarios a esta nota"}), 403
            
            # Obtener la lista de usuarios a agregar
            data = request.get_json()
            new_users = data.get("usuarios", [])
            
            if not new_users or not isinstance(new_users, list):
                return jsonify({"msg": "Se debe proporcionar una lista de usuarios"}), 400
            
            # Verificar que los usuarios existan
            valid_users = []
            invalid_users = []
            for user_id in new_users:
                try:
                    # Verificar si el ID es válido
                    if not ObjectId.is_valid(user_id):
                        invalid_users.append(user_id)
                        continue
                    
                    # Verificar si el usuario existe
                    user_exists = mongo.db.usuarios.find_one({"_id": ObjectId(user_id)})
                    if user_exists:
                        valid_users.append(user_id)
                    else:
                        invalid_users.append(user_id)
                except Exception:
                    invalid_users.append(user_id)
            
            if not valid_users:
                return jsonify({"msg": "Ninguno de los usuarios proporcionados es válido", "invalid_users": invalid_users}), 400
            
            # Obtener la lista actual de usuarios de la nota
            current_users = note.get('usuarios', [])
            current_users_str = [str(uid) if isinstance(uid, ObjectId) else uid for uid in current_users]
            
            # Filtrar usuarios que ya están en la nota
            users_to_add = [user_id for user_id in valid_users if user_id not in current_users_str]
            already_added = [user_id for user_id in valid_users if user_id in current_users_str]
            
            if not users_to_add:
                return jsonify({"msg": "Todos los usuarios válidos ya están agregados a la nota", "already_added": already_added, "invalid_users": invalid_users}), 200
            
            # Actualizar la lista de usuarios de la nota
            mongo.db.notas.update_one(
                {"_id": ObjectId(note_id)},
                {"$addToSet": {"usuarios": {"$each": users_to_add}}}
            )
            
            return jsonify({
                "msg": "Usuarios agregados correctamente a la nota",
                "added_users": users_to_add,
                "already_added": already_added,
                "invalid_users": invalid_users
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
