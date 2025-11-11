from ..extensions import db

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))

    # --- ¡NUEVO! Para Subcategorías ---
    # parent_id apunta al id de otra categoría en esta misma tabla
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    # Relación para obtener las subcategorías (ej. Categoria "Cables" -> subcategorías "Red", "Eléctrico")
    subcategories = db.relationship('Category', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')

    # Relación: Una categoría tiene muchos productos
    products = db.relationship('Product', backref='category', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'parent_name': self.parent.name if self.parent else None
        }

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    # SKU = Stock Keeping Unit (Código único)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    unit_of_measure = db.Column(db.String(20), nullable=False, default='UND')

    # Llave foránea a la categoría
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'sku': self.sku,
            'name': self.name,
            'unit_of_measure': self.unit_of_measure,
            'category_name': self.category.name if self.category else 'N/A'
        }