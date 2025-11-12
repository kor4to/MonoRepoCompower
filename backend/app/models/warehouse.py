from ..extensions import db

class Warehouse(db.Model):
    __tablename__ = 'warehouses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    location = db.Column(db.String(100)) # ej. "Surco", "Cusco"
    ubigeo = db.Column(db.String(100))
    address =  db.Column(db.String(200))
    status = db.Column(db.Boolean)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'location': self.location, "ubigeo": self.ubigeo, "address": self.address, "status": self.status}