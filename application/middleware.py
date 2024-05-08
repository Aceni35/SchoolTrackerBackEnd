from functools import wraps
import jwt
from flask import  request, g, jsonify
from application import app

def authorization(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        token = request.headers['Authorization'].split(" ")[1]
        if not token:
            return jsonify({'Alert' :"Token is missing"}), 400
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            g.token = payload
            print(payload)
            return func(*args, **kwargs) 
        except:
            return jsonify({'Alert' :"Invalid token"}), 400
    return decorated
