from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# Creamos las instancias de las extensiones sin vincularlas a una app
db = SQLAlchemy()
cors = CORS()