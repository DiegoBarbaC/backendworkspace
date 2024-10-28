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
#from bson.binary import Binary
import gridfs


app = Flask(__name__)
app.config.from_object(config)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)



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
    result = mongo.db.usuarios.insert_one({"email":email,"password": hashed_password, "admin":admin, "editar":editar})
    if result.acknowledged:
        return jsonify({"msg": "Usuario Creado Correctamente"}), 201
    else:
        return jsonify({"msg": "Hubo un error, no se pudieron guardar los datos"}),400
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




@app.route('/createSection', methods=['POST'])
@jwt_required()  # Requiere autenticación
def createSection():
    # Verifica si el usuario actual tiene permiso de edición
    current_user = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"_id": ObjectId(current_user)})
    
    if not user or not (user.get("editar", False) or user.get("admin", False)):
        return jsonify({"msg": "Acceso denegado: se requiere el permiso de edición"}), 403

    # Obtén los datos del formulario
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







if __name__ == '__main__':
    app.run(debug=True)