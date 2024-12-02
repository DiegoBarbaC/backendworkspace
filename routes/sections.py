from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId, Binary
from bson.json_util import dumps

def init_section_routes(app, mongo):
    @app.route('/createGlobalSection', methods=['POST'])
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

        nueva_seccion = {
            "imagen": imagen_data,
            "titulo": titulo,
            "descripcion": descripcion,
            "link": link
        }
        
        result = mongo.db.secciones_globales.insert_one(nueva_seccion)
        seccion_id = result.inserted_id

        mongo.db.usuarios.update_many(
            {},
            {
                "$push": {
                    "secciones": {
                        "seccion_id": seccion_id,
                        "orden": 999999
                    }
                }
            }
        )

        if result.acknowledged:
            return jsonify({"msg": "Sección creada y agregada a todos los usuarios"}), 201
        else:
            return jsonify({"msg": "Error al crear la sección"}), 400

    @app.route('/user/sections', methods=['GET'])
    @jwt_required()
    def getUserSections():
        current_user = get_jwt_identity()
        user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
        
        if not user:
            return jsonify({"msg": "Usuario no encontrado"}), 404
        
        # Obtener las secciones del usuario ordenadas
        secciones_usuario = sorted(user.get('secciones', []), key=lambda x: x['orden'])
        
        # Obtener los detalles de cada sección
        secciones_detalladas = []
        for seccion in secciones_usuario:
            seccion_global = mongo.db.secciones_globales.find_one({"_id": seccion['seccion_id']})
            if seccion_global:
                # Convertir la imagen a base64 si existe
                if 'imagen' in seccion_global:
                    imagen_base64 = dumps(seccion_global['imagen'])
                else:
                    imagen_base64 = None
                
                seccion_detalle = {
                    "id": str(seccion_global['_id']),
                    "titulo": seccion_global['titulo'],
                    "descripcion": seccion_global['descripcion'],
                    "link": seccion_global['link'],
                    "imagen": imagen_base64,
                    "orden": seccion['orden']
                }
                secciones_detalladas.append(seccion_detalle)
        
        return jsonify({"secciones": secciones_detalladas}), 200

    @app.route('/user/sections/order', methods=['PUT'])
    @jwt_required()
    def updateSectionsOrder():
        current_user = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'secciones' not in data:
            return jsonify({"msg": "No se proporcionó el nuevo orden de secciones"}), 400
        
        nuevas_secciones = []
        for idx, seccion in enumerate(data['secciones']):
            nuevas_secciones.append({
                "seccion_id": ObjectId(seccion['id']),
                "orden": idx
            })
        
        result = mongo.db.usuarios.update_one(
            {"_id": ObjectId(current_user)},
            {"$set": {"secciones": nuevas_secciones}}
        )
        
        if result.modified_count == 1:
            return jsonify({"msg": "Orden actualizado correctamente"}), 200
        else:
            return jsonify({"msg": "Error al actualizar el orden"}), 400

    @app.route('/user/sections/<section_id>', methods=['DELETE'])
    @jwt_required()
    def removeUserSection(section_id):
        current_user = get_jwt_identity()
        
        result = mongo.db.usuarios.update_one(
            {"_id": ObjectId(current_user)},
            {"$pull": {"secciones": {"seccion_id": ObjectId(section_id)}}}
        )
        
        if result.modified_count == 1:
            return jsonify({"msg": "Sección eliminada correctamente"}), 200
        else:
            return jsonify({"msg": "Error al eliminar la sección"}), 400

    @app.route('/createSection', methods=['POST'])
    @jwt_required()
    def createSection():
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

        nueva_seccion = {
            "imagen": imagen_data,
            "titulo": titulo,
            "descripcion": descripcion,
            "link": link
        }
        
        result = mongo.db.secciones_globales.insert_one(nueva_seccion)
        
        if result.acknowledged:
            return jsonify({"msg": "Sección creada correctamente"}), 201
        else:
            return jsonify({"msg": "Error al crear la sección"}), 400

    @app.route('/editSection/<section_id>', methods=['PUT'])
    @jwt_required()
    def editSection(section_id):
        current_user = get_jwt_identity()
        user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
        
        if not user or not (user.get("editar", False) or user.get("admin", False)):
            return jsonify({"msg": "Acceso denegado: se requiere el permiso de edición"}), 403

        update_data = {}
        
        titulo = request.form.get('titulo')
        descripcion = request.form.get('descripcion')
        link = request.form.get('link')
        imagen = request.files.get('imagen')

        if titulo:
            update_data['titulo'] = titulo
        if descripcion:
            update_data['descripcion'] = descripcion
        if link:
            update_data['link'] = link
        if imagen:
            update_data['imagen'] = Binary(imagen.read())

        if not update_data:
            return jsonify({"msg": "No se proporcionaron datos para actualizar"}), 400

        result = mongo.db.secciones_globales.update_one(
            {"_id": ObjectId(section_id)},
            {"$set": update_data}
        )

        if result.modified_count == 1:
            return jsonify({"msg": "Sección actualizada correctamente"}), 200
        else:
            return jsonify({"msg": "Error al actualizar la sección"}), 400

    @app.route('/deleteSection/<section_id>', methods=['DELETE'])
    @jwt_required()
    def deleteSection(section_id):
        current_user = get_jwt_identity()
        user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
        
        if not user or not (user.get("editar", False) or user.get("admin", False)):
            return jsonify({"msg": "Acceso denegado: se requiere el permiso de edición"}), 403

        # Eliminar la sección global
        result = mongo.db.secciones_globales.delete_one({"_id": ObjectId(section_id)})
        
        if result.deleted_count == 1:
            # Eliminar la referencia de la sección de todos los usuarios
            mongo.db.usuarios.update_many(
                {},
                {"$pull": {"secciones": {"seccion_id": ObjectId(section_id)}}}
            )
            return jsonify({"msg": "Sección eliminada correctamente"}), 200
        else:
            return jsonify({"msg": "Error al eliminar la sección"}), 400

    @app.route('/sections', methods=['GET'])
    @jwt_required()
    def getSections():
        current_user = get_jwt_identity()
        user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
        
        if not user or not (user.get("editar", False) or user.get("admin", False)):
            return jsonify({"msg": "Acceso denegado: se requiere el permiso de edición"}), 403

        secciones = list(mongo.db.secciones_globales.find())
        secciones_lista = []
        
        for seccion in secciones:
            if 'imagen' in seccion:
                imagen_base64 = dumps(seccion['imagen'])
            else:
                imagen_base64 = None
                
            seccion_detalle = {
                "id": str(seccion['_id']),
                "titulo": seccion['titulo'],
                "descripcion": seccion['descripcion'],
                "link": seccion['link'],
                "imagen": imagen_base64
            }
            secciones_lista.append(seccion_detalle)
        
        return jsonify({"secciones": secciones_lista}), 200
