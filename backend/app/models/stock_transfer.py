from ..extensions import db
from datetime import datetime

# Modelo 1: La cabecera de la transferencia
class StockTransfer(db.Model):
    __tablename__ = 'stock_transfers'
    id = db.Column(db.Integer, primary_key=True)
    transfer_date = db.Column(db.DateTime, default=datetime.now)

    # Origen (Siempre es un almacén interno)
    origin_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    origin_warehouse = db.relationship('Warehouse', foreign_keys=[origin_warehouse_id])

    # Destino (Puede ser interno O externo)
    destination_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True) # Nulo si es externo
    destination_warehouse = db.relationship('Warehouse', foreign_keys=[destination_warehouse_id])

    destination_external_address = db.Column(db.String(255), nullable=True) # Nulo si es interno

    status = db.Column(db.String(50), nullable=False, default='Completada') # Ahora es instantáneo
    user_id = db.Column(db.String(255), nullable=False) # Auth0 sub

    # Relación con los items
    items = db.relationship('StockTransferItem', backref='transfer', lazy='dynamic', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'transfer_date': self.transfer_date.isoformat(),
            'origin_warehouse': self.origin_warehouse.name if self.origin_warehouse else 'N/A',
            'destination_warehouse': self.destination_warehouse.name if self.destination_warehouse else 'N/A',
            'destination_external': self.destination_external_address,
            'status': self.status,
            'items': [item.to_dict() for item in self.items.all()]
        }

# Modelo 2: Los detalles (items) de la transferencia
class StockTransferItem(db.Model):
    __tablename__ = 'stock_transfer_items'
    id = db.Column(db.Integer, primary_key=True)

    transfer_id = db.Column(db.Integer, db.ForeignKey('stock_transfers.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)

    product = db.relationship('Product')

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else 'N/A',
            'product_sku': self.product.sku if self.product else 'N/A',
            'quantity': float(self.quantity)
        }