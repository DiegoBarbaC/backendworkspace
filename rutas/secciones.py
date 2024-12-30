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
from flask_cors import CORS
import gridfs
import base64

secciones_bp = Blueprint("secciones", __name__,)

#Ruta para obtener las secciones del usuario
@secciones_bp.route('/user/sections', methods=['GET'])
@jwt_required()
def getUserSections():
    current_user = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
    
    if not user:
        return jsonify({"msg": "Usuario no encontrado"}), 404

    # Obtener las secciones del usuario con su orden
    user_sections = user.get('secciones', [])
    
    # Ordenar por el campo orden
    user_sections.sort(key=lambda x: x['orden'])
    
    # Obtener los detalles completos de cada sección
    result = []
    for section_info in user_sections:
        section = mongo.db.secciones_globales.find_one({"_id": section_info['seccion_id']})
        if section:
            section_data = {
                "_id": str(section['_id']),
                "titulo": section['titulo'],
                "descripcion": section['descripcion'],
                "link": section['link'],
                "orden": section_info['orden']
            }
            if 'imagen' in section:
                section_data['imagen'] = base64.b64encode(section['imagen']).decode('utf-8')
            result.append(section_data)

    return jsonify(result), 200

@secciones_bp.route('/user/sections/order', methods=['PUT'])
@jwt_required()
def updateSectionsOrder():
    current_user = get_jwt_identity()
    data = request.get_json()
    
    if not data or 'sections' not in data:
        return jsonify({"msg": "Se requiere la lista de secciones con su orden"}), 400
    
    # Obtener el usuario y sus secciones actuales
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
    if not user:
        return jsonify({"msg": "Usuario no encontrado"}), 404
        
    current_sections = user.get('secciones', [])
    
    # Crear un diccionario con las secciones actuales para fácil acceso
    sections_dict = {str(section['seccion_id']): section for section in current_sections}
    
    # Actualizar solo el orden de las secciones especificadas
    for section in data['sections']:
        section_id = section['seccion_id']
        if section_id in sections_dict:
            sections_dict[section_id]['orden'] = section['orden']
    
    # Convertir el diccionario actualizado de vuelta a lista
    updated_sections = [
        {
            "seccion_id": ObjectId(section_id) if isinstance(section_id, str) else section_id,
            "orden": section_data['orden']
        }
        for section_id, section_data in sections_dict.items()
    ]
    
    # Actualizar en la base de datos
    result = mongo.db.usuarios.update_one(
        {"_id": ObjectId(current_user)},
        {"$set": {"secciones": updated_sections}}
    )
    
    if result.modified_count == 1:
        return jsonify({"msg": "Orden actualizado correctamente"}), 200
    else:
        return jsonify({"msg": "Error al actualizar el orden"}), 400

#Ruta para eliminar una sección global (se elimina para todos los usuarios)
@secciones_bp.route('/user/sections/<section_id>', methods=['DELETE'])
@jwt_required()
def removeUserSection(section_id):
    current_user = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})

    if not user or not (user.get("editar", False) or user.get("admin", False)):
        return jsonify({"msg": "Acceso denegado: se requiere el permiso de edición"}), 403

    result = mongo.db.secciones_globales.delete_one({"_id": ObjectId(section_id)})
      
    
    if result.deleted_count == 1:
        return jsonify({"msg": "Sección eliminada de tu dashboard"}), 200
    else:
        return jsonify({"msg": "Error al eliminar la sección"}), 404

#Ruta para crear una sección única para el usuario (no se crea para todos los usuarios)
#No implementada por ahora
@secciones_bp.route('/createSection', methods=['POST'])
@jwt_required()  # Requiere autenticación
def createSection():
    # Verifica si el usuario actual tiene permiso de edición
    current_user = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
    
    if not user or not (user.get("editar", False) or user.get("admin", False)):
        return jsonify({"msg": "Acceso denegado: se requiere el permiso de edición"}), 403

    # Obtén los datos del formulario
    orden = request.form.get('orden')
    titulo = request.form.get('titulo')
    descripcion = request.form.get('descripcion')
    link = request.form.get('link')
    imagen = request.files.get('imagen')  # Aquí se obtiene el archivo de imagen

    # Verificaciones de campos requeridos
    if not imagen:
        return jsonify({'message': 'Se requiere una imagen para crear la sección'}), 400
    if not titulo:
        return jsonify({'message': 'Se requiere un título para crear la sección'}), 400
    if not descripcion:
        return jsonify({'message': 'Se requiere una descripción para crear la sección'}), 400
    if not link:
        return jsonify({'message': 'Se requiere un link para crear la sección'}), 400

    # Lee la imagen en formato binario
    imagen_data = Binary(imagen.read())

    # Inserta la sección en MongoDB
    result = mongo.db.secciones.insert_one({
        "imagen": imagen_data,
        "titulo": titulo,
        "descripcion": descripcion,
        "link": link
    })

    # Confirma la creación
    if result.acknowledged:
        return jsonify({"msg": "Sección creada correctamente"}), 201
    else:
        return jsonify({"msg": "Hubo un error, no se pudieron guardar los datos"}), 400


#Ruta para editar una sección global (se edita para todos los usuarios)
@secciones_bp.route('/editSection/<section_id>', methods=['PUT'])
@jwt_required()
def editSection(section_id):
    # Obtener los datos del usuario actual
    current_user = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
    
    # Verificación de permisos
    if not user or not (user.get("editar", False) or user.get("admin", False)):
        return jsonify({"msg": "Acceso denegado: se requiere el permiso de edición"}), 403
    
    # Obtener los datos de la solicitud
    data = request.form
    imagen = request.files.get('imagen')  # Obtiene la imagen si se envía
    titulo = data.get('titulo')
    descripcion = data.get('descripcion')
    link = data.get('link')

    # Construir un diccionario solo con los campos a actualizar
    update_data = {}
    if imagen:
        imagen_data = imagen.read()  # Leer el archivo de imagen como bytes
        update_data['imagen'] = imagen_data
    if titulo:
        update_data['titulo'] = titulo
    if descripcion:
        update_data['descripcion'] = descripcion
    if link:
        update_data['link'] = link

    # Verificar si hay datos para actualizar
    if not update_data:
        return jsonify({"msg": "No se proporcionaron datos para actualizar"}), 400

    # Actualizar la sección en la base de datos
    result = mongo.db.secciones_globales.update_one({"_id": ObjectId(section_id)}, {"$set": update_data})

    # Verificar el resultado de la actualización
    if result.modified_count == 1:
        return jsonify({"msg": "Sección actualizada correctamente"}), 200
    else:
        return jsonify({"msg": "Error al actualizar la sección o no se encontraron cambios"}), 400


#Ruta para crear una sección global (se crea para todos los usuarios)
@secciones_bp.route('/createGlobalSection', methods=['POST'])
@jwt_required()
def createGlobalSection():
    current_user = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
    
    if not user or not (user.get("editar", False) or user.get("admin", False)):
        return jsonify({"msg": "Acceso denegado: se requiere el permiso de edición"}), 403

    titulo = request.form.get('titulo')
    descripcion = request.form.get('descripcion')
    link = request.form.get('link')
    imagen = request.files.get('imagen')

    if not all([imagen, titulo, descripcion, link]):
        return jsonify({'message': 'Todos los campos son requeridos'}), 400

    imagen_data = Binary(imagen.read())

    # Crear la sección global
    nueva_seccion = {
        "imagen": imagen_data,
        "titulo": titulo,
        "descripcion": descripcion,
        "link": link
    }
    
    result = mongo.db.secciones_globales.insert_one(nueva_seccion)
    seccion_id = result.inserted_id

    # Agregar la sección a todos los usuarios al final de su lista
    mongo.db.usuarios.update_many(
        {},
        {
            "$push": {
                "secciones": {
                    "seccion_id": seccion_id,
                    "orden": 999999  # Un número alto para agregarlo al final
                }
            }
        }
    )

    if result.acknowledged:
        return jsonify({"msg": "Sección creada y agregada a todos los usuarios"}), 201
    else:
        return jsonify({"msg": "Error al crear la sección"}), 400

    
@secciones_bp.route('/user/sections/<section_id>', methods=['GET'])
@jwt_required()
def getSection(section_id):
    current_user = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
    
    if not user:
        return jsonify({"msg": "Usuario no encontrado"}), 404

    # Buscar la sección global por ID
    section = mongo.db.secciones_globales.find_one({"_id": ObjectId(section_id)})
    
    if not section:
        return jsonify({"msg": "Sección no encontrada"}), 404

    # Preparar la respuesta
    section_data = {
        "_id": str(section['_id']),
        "titulo": section['titulo'],
        "descripcion": section['descripcion'],
        "link": section['link'],
        "imagen":base64.b64encode(section['imagen']).decode('utf-8')
    }
    print (section_data)

    return jsonify(section_data), 200
    