from flask import Flask, request, jsonify
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


app = Flask(__name__)
app.config.from_object(config)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
CORS(app)


#Inicializamos el acceso a MongoDB
init_db(app)
fs = gridfs.GridFS(mongo.db)

@app.route('/register', methods=['POST'])

def register():
    data = request.get_json()

    # Verificar que el correo y la contraseña están presentes en la solicitud
    email = data.get('email')
    password = data.get('password')
    editar=data.get('editar', False)
    admin=data.get('admin', False)

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
    data= request.get_json()
    email=data.get('email')
    password = data.get('password')

    user = mongo.db.usuarios.find_one({"email":email})

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
    
@app.route('/api1', methods=['GET'])
def hola():
    return ("Hola Infra")
    
@app.route('/deleteUser', methods=['DELETE'])
@jwt_required()
def deleteUser():
    data=request.get_json()
    email=data.get('email')
    user = mongo.db.usuarios.find_one({"email":email})
    if (user):
        result = mongo.db.usuarios.delete_one({"email":email})

    if result.deleted_count == 1:
        return jsonify({"msg": "Usuario eliminado correctamente"}), 200
    else:
        return jsonify({"msg": "Error al eliminar el usuario"}), 400

        
@app.route ('/updateUser', methods=['PUT'])
@jwt_required()
def updateUser():
    data=request.get_json()
    email=data.get('email')
    editar=data.get('editar')
    admin=data.get('admin')
    password=data.get('password')
    user = mongo.db.usuarios.find_one({"email":email})
    if (user):
        update_data={}
        if editar is not None:
            update_data['editar']=bool(editar)
        if admin is not None:
            update_data['admin']=bool(admin)
        if password:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            update_data['password']=hashed_password
        if not update_data:
            return jsonify({"msg": "No se proporcionaron datos para actualizar"}), 400
        print(update_data)
        result=mongo.db.usuarios.update_one({"email": email}, {"$set":update_data})
        print(result.modified_count)
        if result.modified_count == 1:
            return jsonify({"msg": "Usuario actualizado correctamente"}), 200
        else:
            return jsonify({"msg": "Error al actualizar el usuario"}), 400

@app.route('/getAllUsers', methods=['GET'])
@jwt_required()  # Requiere autenticación
def get_all_users():
    #Verifica si el usuario actual tiene permiso de admin
    current_user = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
    
    if not user or not user.get("admin", False):
        return jsonify({"msg": "Acceso denegado: se requiere rol de administrador"}), 403

    # Recupera todos los usuarios de la colección
    all_users = list(mongo.db.usuarios.find({}))
    print(all_users)
    # Serializa la lista de usuarios en formato JSON
    user_list = dumps(all_users)
    
    return jsonify({"usuarios": user_list}), 200

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

@app.route('/user/sections', methods=['GET'])
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

@app.route('/user/sections/order', methods=['PUT'])
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

@app.route('/user/sections/<section_id>', methods=['DELETE'])
@jwt_required()
def removeUserSection(section_id):
    current_user = get_jwt_identity()
    
    result = mongo.db.usuarios.update_one(
        {"_id": ObjectId(current_user)},
        {"$pull": {"secciones": {"seccion_id": ObjectId(section_id)}}}
    )
    
    if result.modified_count == 1:
        return jsonify({"msg": "Sección eliminada de tu dashboard"}), 200
    else:
        return jsonify({"msg": "Error al eliminar la sección"}), 404

@app.route('/createSection', methods=['POST'])
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

@app.route('/editSection/<section_id>', methods=['PUT'])
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
    result = mongo.db.secciones.update_one({"_id": ObjectId(section_id)}, {"$set": update_data})

    # Verificar el resultado de la actualización
    if result.modified_count == 1:
        return jsonify({"msg": "Sección actualizada correctamente"}), 200
    else:
        return jsonify({"msg": "Error al actualizar la sección o no se encontraron cambios"}), 400
    

@app.route('/deleteSection/<section_id>', methods=['DELETE'])
@jwt_required()  # Requiere autenticación
def deleteSection(section_id):
    # Obtiene la identidad del usuario actual
    current_user = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
    
    # Verifica si el usuario tiene permiso para editar o es administrador
    if not user or not (user.get("editar", False) or user.get("admin", False)):
        return jsonify({"msg": "Acceso denegado: se requiere el permiso de edición"}), 403

    # Intenta eliminar la sección de la base de datos
    result = mongo.db.secciones.delete_one({"_id": ObjectId(section_id)})
    
    # Verifica si se eliminó alguna sección
    if result.deleted_count == 1:
        return jsonify({"msg": "Sección eliminada correctamente"}), 200
    else:
        return jsonify({"msg": "Error al eliminar la sección o no existe"}), 404
    

@app.route('/sections', methods=['GET'])
@jwt_required()  # Requiere autenticación
def getSections():
    # Verifica si el usuario está autenticado
    current_user = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
    
    if not user:
        return jsonify({"msg": "Acceso denegado: usuario no encontrado"}), 403

    # Recupera todas las secciones de la base de datos
    secciones = mongo.db.secciones.find()  # Obtener todas las secciones

    # Prepara la respuesta
    result = []
    for section in secciones:
        # Convierte la imagen de Binary a Base64 si es necesario
        if 'imagen' in section:
            #section['imagen'] = section['imagen'].encode('utf-8')  
            section['imagen'] = base64.b64encode(section['imagen']).decode('utf-8')

        # También puedes eliminar el campo '_id' si no deseas que se muestre
        section['_id'] = str(section['_id'])  # Convierte ObjectId a string
        result.append(section)

    return jsonify(result), 200








if __name__ == '__main__':
    app.run(debug=True)
