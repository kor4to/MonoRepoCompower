from ..extensions import db

class Site(db.Model):
    __tablename__ = 'sites'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(100), unique=True)
    ubigeo = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)

    def to_dict(self):
        return {'id': self.id, "name": self.name, "code": self.code, "ubigeo": self.ubigeo, "address": self.address}
