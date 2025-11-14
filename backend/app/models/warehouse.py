from ..extensions import db

class Warehouse(db.Model):
    __tablename__ = 'warehouses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    location = db.Column(db.String(100)) # ej. "Surco", "Cusco"
    address = db.Column(db.String(255), nullable=True) # Dirección fiscal completa
    ubigeo = db.Column(db.String(10), nullable=True) # Código de Ubigeo

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'location': self.location,
            'address': self.address,
            'ubigeo': self.ubigeo
        }