from flask import Blueprint, jsonify, request

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login", methods=["POST"])
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
