from flask import Flask
from flask_pymongo import PyMongo

app = Flask(__name__)
app.config["SECRET_KEY"] = "be6d4795c249472432da5d4f0ab0a4ff14096b5d64e36e76da351afe28c73f182c2b86b00a319d8"
app.config["MONGO_URI"] = "mongodb+srv://aceni3500:CLzYR6F2GDy6Wc8@nodeprojects.nd1oe61.mongodb.net/StudentApp?retryWrites=true&w=majority"

# mongodb
mongodb_client = PyMongo(app)
db = mongodb_client.db

from application import routes