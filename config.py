# https://medium.com/@ccchimento/authentication-and-authorization-with-flask-sqlalchemy-ce9150851b85

from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api
from flask_bcrypt import Bcrypt
from datetime import timedelta

app = Flask(__name__)

app.secret_key = "cefc5e94-190a-47dd-8740-838b48223bd1"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.json.compact = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

bcrypt = Bcrypt(app)

app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_SQLALCHEMY'] = db
app.permanent_session_lifetime = timedelta(minutes=10)

api = Api(app)

CORS(app)