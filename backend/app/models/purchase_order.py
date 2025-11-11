from ..extensions import db
from datetime import datetime
from .cost_center import CostCenter

# --- Catálogos (Sin cambios) ---
class DocumentType(db.Model):
    __tablename__ = 'document_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    def to_dict(self): return {'id': self.id, 'name': self.name}

class OrderStatus(db.Model):
    __tablename__ = 'order_statuses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    def to_dict(self): return {'id': self.id, 'name': self.name}

# --- ¡REFACTOR! Detalles de la Orden ---
# --- ¡REFACTOR! Detalles de la Orden ---
class PurchaseOrderItem(db.Model):
    __tablename__ = 'purchase_order_items'
    id = db.Column(db.Integer, primary_key=True)

    # --- Vínculo al Catálogo (para Inventario) ---
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    product = db.relationship('Product')

    # --- ¡NUEVO CAMPO! Texto Libre (para Contabilidad) ---
    invoice_detail_text = db.Column(db.String(255), nullable=False)

    # --- Campos de la transacción ---
    unit_of_measure = db.Column(db.String(20), nullable=True, default='UND')
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=1.00)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)

    order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)

    def to_dict(self):
        # --- ¡BLOQUE CORREGIDO! ---
        # Revisa si self.product existe antes de intentar leerlo
        product_name = self.product.name if self.product else "Producto no asignado"
        product_sku = self.product.sku if self.product else "N/A"
        # ---------------------------

        return {
            'id': self.id,
            'product_name': product_name,
            'product_sku': product_sku,
            'invoice_detail_text': self.invoice_detail_text,
            'unit_of_measure': self.unit_of_measure,
            'quantity': float(self.quantity),
            'unit_price': float(self.unit_price)
        }

# --- MODELO PRINCIPAL (Actualizado) ---
class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'
    id = db.Column(db.Integer, primary_key=True)
    document_number = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # --- Relaciones (Llaves Foráneas) ---
    owner_id = db.Column(db.String(255), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), nullable=False)
    provider = db.relationship('Provider')

    document_type_id = db.Column(db.Integer, db.ForeignKey('document_types.id'), nullable=False)
    document_type = db.relationship('DocumentType')

    status_id = db.Column(db.Integer, db.ForeignKey('order_statuses.id'), nullable=False)
    status = db.relationship('OrderStatus')

    cost_center_id = db.Column(db.Integer, db.ForeignKey('cost_centers.id'), nullable=True)
    cost_center = db.relationship('CostCenter')

    # La relación ahora apunta al 'PurchaseOrderItem' refactorizado
    items = db.relationship('PurchaseOrderItem', backref='order', lazy='dynamic', cascade="all, delete-orphan")

    def to_dict(self):
        # Calcular el total dinámicamente
        total = sum(item.quantity * item.unit_price for item in self.items.all())

        # --- ¡BLOQUE CORREGIDO! ---
        return {
            'id': self.id,
            'document_number': self.document_number,
            'created_at': self.created_at.isoformat(),
            'provider': self.provider.name if self.provider else 'N/A',
            'document_type': self.document_type.name if self.document_type else 'N/A',
            'status': self.status.name if self.status else 'N/A',
            'cost_center': self.cost_center.name if self.cost_center else 'N/A',
            'items': [item.to_dict() for item in self.items.all()],
            'total_amount': float(total)
        }