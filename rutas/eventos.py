from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from model import mongo
from bson.json_util import ObjectId
from flask_jwt_extended import get_jwt_identity
from bson import ObjectId
from datetime import datetime, timedelta




eventos_bp = Blueprint("eventos", __name__,)


def parse_event_datetime(value):
    if not value:
        return None
    normalized_value = value.strip()
    if normalized_value.endswith('Z'):
        normalized_value = f"{normalized_value[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized_value)
        if parsed.tzinfo:
            return parsed.astimezone().replace(tzinfo=None)
        return parsed
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(normalized_value, fmt)
        except ValueError:
            continue
    return None

#Ruta para agregar un nuevo evento
@eventos_bp.route('/addEvent', methods=['POST'])
@jwt_required()  # Requiere autenticación
def addEvent():
    # Obtén los datos del formulario
    titulo = request.form.get('titulo')
    descripcion = request.form.get('descripcion')
    fechaInicio = request.form.get('fechaInicio')
    fechaFin = request.form.get('fechaFin')
    usuarios = request.form.getlist('usuarios')

    # Verificaciones de campos requeridos
    if not titulo:
        return jsonify({'message': 'Se requiere un título para crear el evento'}), 400
    if not descripcion:
        return jsonify({'message': 'Se requiere una descripción para crear el evento'}), 400
    if not fechaInicio:
        return jsonify({'message': 'Se requiere una fecha de inicio para crear el evento'}), 400
    if not fechaFin:
        return jsonify({'message': 'Se requiere una fecha de fin para crear el evento'}), 400

    fecha_inicio_dt = parse_event_datetime(fechaInicio)
    fecha_fin_dt = parse_event_datetime(fechaFin)
    now = datetime.now().replace(second=0, microsecond=0)  # Redondear al minuto actual
    if not fecha_inicio_dt or not fecha_fin_dt:
        return jsonify({'message': 'Formato de fecha inválido'}), 400
    
    if fecha_fin_dt < fecha_inicio_dt:
        return jsonify({'message': 'La fecha de fin debe ser posterior a la fecha de inicio'}), 400
    
    # Restar 5 minutos a la fecha de inicio para dar margen
    fecha_inicio_dt += timedelta(minutes=5)
    
    if fecha_inicio_dt < now:
        return jsonify({'message': 'La fecha de inicio no puede estar en el pasado'}), 400

    # Obtener el usuario actual
    current_user = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
    
    # Verificación de permisos
    if not user or not (user.get("editar", False) or user.get("admin", False)):
        return jsonify({"msg": "Acceso denegado: se requiere el permiso de edición"}), 403

    # Asegurarse de que el usuario actual esté incluido en la lista de usuarios
    if current_user not in usuarios:
        usuarios.append(current_user)

    # Crear el nuevo evento
    nuevo_evento = {
        "titulo": titulo,
        "descripcion": descripcion,
        "fechaInicio": fechaInicio,
        "fechaFin": fechaFin,
        "usuarios": usuarios
    }
    result = mongo.db.eventos.insert_one(nuevo_evento)
    if result.acknowledged:
        return jsonify({"msg": "Evento creado correctamente"}), 200
    else:
        return jsonify({"msg": "Error al crear el evento"}), 400


#Ruta para obtener todos los eventos
@eventos_bp.route('/getEvents', methods=['GET'])
@jwt_required()
def getEvents():
    try:
        # Obtener el usuario actual
        current_user = get_jwt_identity()
        
        # Buscar eventos donde el usuario actual está incluido
        eventos = list(mongo.db.eventos.find({"usuarios": current_user}))
        
        # Formatear los eventos para el calendario
        eventos_formateados = []
        for evento in eventos:
            eventos_formateados.append({
                'id': str(evento['_id']),
                'title': evento['titulo'],
                'start': evento['fechaInicio'],
                'end': evento['fechaFin'],
                'description': evento['descripcion'],
                'usuarios': evento['usuarios']
            })
        
        return jsonify({"eventos": eventos_formateados}), 200
    except Exception as e:
        print("Error al obtener eventos:", str(e))
        return jsonify({"msg": "Error al obtener los eventos"}), 500

#Ruta para eliminar un evento
@eventos_bp.route('/deleteEvent/<event_id>', methods=['DELETE'])
@jwt_required()  # Requiere autenticación
def deleteEvent(event_id):
    # Obtener el usuario actual
    current_user = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
    
    # Verificación de permisos
    if not user or not (user.get("editar", False) or user.get("admin", False)):
        return jsonify({"msg": "Acceso denegado: se requiere el permiso de edición"}), 403

    # Eliminar el evento
    result = mongo.db.eventos.delete_one({"_id": ObjectId(event_id)})
    
    if result.deleted_count == 1:
        return jsonify({"msg": "Evento eliminado correctamente"}), 200
    else:
        return jsonify({"msg": "Error al eliminar el evento"}), 400

#Ruta para actualizar un evento
@eventos_bp.route('/updateEvent/<event_id>', methods=['PUT'])
@jwt_required()  # Requiere autenticación
def updateEvent(event_id):
    # Obtener el usuario actual
    current_user = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
    
    # Verificación de permisos
    if not user or not (user.get("editar", False) or user.get("admin", False)):
        return jsonify({"msg": "Acceso denegado: se requiere el permiso de edición"}), 403

    # Obtener los datos de la solicitud
    data = request.form
    titulo = data.get('titulo')
    descripcion = data.get('descripcion')
    fechaInicio = data.get('fechaInicio')
    fechaFin = data.get('fechaFin')
    usuarios = request.form.getlist('usuarios')

    evento_existente = mongo.db.eventos.find_one({"_id": ObjectId(event_id)})
    if not evento_existente:
        return jsonify({"msg": "Evento no encontrado"}), 404

    final_fecha_inicio = fechaInicio if fechaInicio else evento_existente.get('fechaInicio')
    final_fecha_fin = fechaFin if fechaFin else evento_existente.get('fechaFin')

    final_fecha_inicio_dt = parse_event_datetime(final_fecha_inicio)
    final_fecha_fin_dt = parse_event_datetime(final_fecha_fin)
    now = datetime.now().replace(second=0, microsecond=0)
    if not final_fecha_inicio_dt or not final_fecha_fin_dt:
        return jsonify({'message': 'Formato de fecha inválido'}), 400
    
    if final_fecha_fin_dt < final_fecha_inicio_dt:
        return jsonify({'message': 'La fecha de fin debe ser posterior a la fecha de inicio'}), 400
    
    # Restar 5 minutos a la fecha de inicio para dar margen
    final_fecha_inicio_dt -= timedelta(minutes=5)
    
    if final_fecha_inicio_dt < now:
        return jsonify({'message': 'La fecha de inicio no puede estar en el pasado'}), 400

    # Construir un diccionario solo con los campos a actualizar
    update_data = {}
    if titulo:
        update_data['titulo'] = titulo
    if descripcion:
        update_data['descripcion'] = descripcion
    if fechaInicio:
        update_data['fechaInicio'] = fechaInicio
    if fechaFin:
        update_data['fechaFin'] = fechaFin
    if usuarios:
        # Asegurarse de que el usuario actual esté incluido en la lista de usuarios
        if current_user not in usuarios:
            usuarios.append(current_user)
        update_data['usuarios'] = usuarios

    # Actualizar el evento
    result = mongo.db.eventos.update_one({"_id": ObjectId(event_id)}, {"$set": update_data})

    if result.modified_count == 1:
        return jsonify({"msg": "Evento actualizado correctamente"}), 200
    else:
        return jsonify({"msg": "Error al actualizar el evento"}), 400

    