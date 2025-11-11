from flask import Blueprint, jsonify, request
from ..extensions import db
from ..models.warehouse import Warehouse
from ..models.purchase_order import PurchaseOrder, PurchaseOrderItem, OrderStatus
from ..models.inventory_models import InventoryStock, InventoryTransaction
from ..models.product_catalog import Product
from ..services.auth_service import requires_auth
from sqlalchemy import or_, and_
from sqlalchemy.orm import joinedload

inventory_api = Blueprint('inventory_api', __name__)

# --- API 1: Obtener la lista de almacenes ---
@inventory_api.route('/warehouses', methods=['GET'])
@requires_auth(required_permission='manage:inventory')
def get_warehouses(payload):
    try:
        warehouses = Warehouse.query.all()
        return jsonify([w.to_dict() for w in warehouses])
    except Exception as e:
        return jsonify(error=str(e)), 500

# --- API 2: Procesar la Recepción de Inventario ---
@inventory_api.route('/receive', methods=['POST'])
@requires_auth(required_permission='manage:inventory')
def receive_inventory(payload):
    """
    Esta es la API principal. Recibe una lista de items a recepcionar.
    Payload esperado:
    {
        "warehouse_id": 1,
        "order_id": 5,
        "items": [
            { "po_item_id": 10, "product_id": 2, "quantity_received": 50 },
            { "po_item_id": 11, "product_id": 1, "quantity_received": 20 }
        ]
    }
    """
    data = request.get_json()
    user_id = payload['sub']

    required_fields = ['warehouse_id', 'order_id', 'items']
    if not all(field in data for field in required_fields):
        return jsonify(error="Faltan datos (warehouse_id, order_id, items)"), 400

    try:
        warehouse_id = data['warehouse_id']
        order_id = data['order_id']

        # 1. Recorrer cada item que el usuario está recepcionando
        for item_data in data['items']:
            po_item_id = item_data['po_item_id']
            product_id = item_data['product_id']
            quantity_received = float(item_data['quantity_received'])

            if quantity_received <= 0:
                continue # Ignorar items que no se están recibiendo

            # 2. Actualizar el PurchaseOrderItem (le asignamos el product_id)
            po_item = PurchaseOrderItem.query.get(po_item_id)
            if not po_item:
                raise Exception(f"No se encontró el item de orden {po_item_id}")

            po_item.product_id = product_id

            # 3. Encontrar (o crear) el registro de Stock para este producto/almacén
            stock_entry = InventoryStock.query.filter_by(
                product_id=product_id,
                warehouse_id=warehouse_id
            ).first()

            if not stock_entry:
                # Si es la primera vez que este producto entra a este almacén
                stock_entry = InventoryStock(
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    quantity=0.0
                )
                db.session.add(stock_entry)

            # 4. Actualizar la cantidad de stock
            new_stock_quantity = float(stock_entry.quantity) + quantity_received
            stock_entry.quantity = new_stock_quantity

            # 5. Crear la Transacción de Inventario (Kardex)
            transaction = InventoryTransaction(
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity_change=quantity_received, # ej. +50
                new_quantity=new_stock_quantity, # El stock resultante
                type="Recepción de Compra",
                user_id=user_id,
                purchase_order_item_id=po_item_id
            )
            db.session.add(transaction)

        # 6. Actualizar el estado de la Orden de Compra a "Recibida"
        order = PurchaseOrder.query.get(order_id)
        received_status = OrderStatus.query.filter_by(name='Recibida').first()
        if order and received_status:
            order.status_id = received_status.id

        # 7. Guardar todos los cambios en la BD
        db.session.commit()

        return jsonify(success=True, message="Inventario actualizado correctamente.")

    except Exception as e:
        db.session.rollback()
        print(f"--- ERROR AL RECEPCIONAR: {str(e)} ---")
        return jsonify(error=str(e)), 500


# --- ¡NUEVA API! ---
# --- API 3: Reporte de Stock Actual ---
@inventory_api.route('/stock-report', methods=['GET'], strict_slashes=False)
@requires_auth(required_permission='view:inventory')
def get_stock_report(payload):
    """
    Devuelve el stock actual de todos los productos en todos los almacenes.
    """
    try:
        # Esta consulta une Stock con Producto y Almacén
        stock_data = db.session.query(
            InventoryStock.quantity,
            Product.name.label('product_name'),
            Product.sku.label('product_sku'),
            Warehouse.name.label('warehouse_name')
        ).join(
            Product, InventoryStock.product_id == Product.id
        ).join(
            Warehouse, InventoryStock.warehouse_id == Warehouse.id
        ).filter(
            InventoryStock.quantity > 0 # Opcional: mostrar solo items con stock
        ).order_by(
            Warehouse.name, Product.name
        ).all()

        # Convertimos el resultado a un formato JSON amigable
        report = [
            {
                "product_name": row.product_name,
                "product_sku": row.product_sku,
                "warehouse_name": row.warehouse_name,
                "quantity": float(row.quantity)
            } for row in stock_data
        ]

        return jsonify(report)

    except Exception as e:
        print(f"--- ERROR AL OBTENER REPORTE DE STOCK: {str(e)} ---")
        return jsonify(error=str(e)), 500