from flask import Blueprint, jsonify, request
from ..extensions import db
from ..models.warehouse import Warehouse
from ..models.purchase_order import PurchaseOrder, PurchaseOrderItem, OrderStatus
from ..models.inventory_models import InventoryStock, InventoryTransaction
from ..models.product_catalog import Product, Category
from ..services.auth_service import requires_auth
from sqlalchemy import or_, and_
from sqlalchemy.orm import joinedload
import pandas as pd

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

            # --- CÁLCULO DE COSTO PROMEDIO PONDERADO ---
            # 1. Obtener datos actuales
            product = Product.query.get(product_id)
            current_total_stock = db.session.query(db.func.sum(InventoryStock.quantity)).filter_by(
                product_id=product_id).scalar() or 0.0
            current_total_stock = float(current_total_stock)
            current_avg_price = float(product.standard_price)

            # Precio de esta compra específica (buscamos en el item de la orden)
            incoming_price = float(po_item.unit_price)

            # 2. Fórmula: (Valor Actual + Valor Nuevo) / Cantidad Total Nueva
            current_total_value = current_total_stock * current_avg_price
            incoming_total_value = quantity_received * incoming_price

            new_total_quantity = current_total_stock + quantity_received

            if new_total_quantity > 0:
                new_avg_price = (current_total_value + incoming_total_value) / new_total_quantity
                # Actualizamos el precio maestro del producto
                product.standard_price = new_avg_price
            # -------------------------------------------

            # 4. Actualizar la cantidad de stock (en este almacén específico)
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


# --- API 3: Reporte de Stock Consolidado (con filtros) ---
@inventory_api.route('/stock-report', methods=['GET'], strict_slashes=False)
@requires_auth(required_permission='view:inventory')
def get_stock_report(payload):
    try:
        warehouse_id = request.args.get('warehouse_id')

        query = db.session.query(
            Product.sku.label('product_sku'),
            Product.name.label('product_name'),
            Category.name.label('category_name'),
            Category.id.label('category_id'), # <-- ¡IMPORTANTE! Necesitamos el ID para filtrar hijos
            Product.standard_price.label('unit_price'),
            db.func.sum(InventoryStock.quantity).label('total_quantity')
        ).join(
            Category, Product.category_id == Category.id
        ).join(
            InventoryStock, Product.id == InventoryStock.product_id
        )

        if warehouse_id and warehouse_id != 'all':
            query = query.filter(InventoryStock.warehouse_id == warehouse_id)

        # Agrupar por producto
        stock_data = query.group_by(Product.id).having(db.func.sum(InventoryStock.quantity) > 0).all()

        report = []
        for row in stock_data:
            qty = float(row.total_quantity)
            # Si el precio es nulo, usamos 0.0
            price = float(row.unit_price or 0.0)

            report.append({
                "product_sku": row.product_sku,
                "product_name": row.product_name,
                "category_name": row.category_name,
                "category_id": row.category_id, # <-- Enviamos el ID al frontend
                "quantity": qty,
                "unit_price": price,
                "total_value": qty * price
            })

        return jsonify(report)

    except Exception as e:
        print(f"--- ERROR AL OBTENER REPORTE DE STOCK: {str(e)} ---")
        return jsonify(error=str(e)), 500

# --- API 4: Carga Masiva de Stock (Ajuste de Inventario) ---
@inventory_api.route('/adjust-mass', methods=['POST'], strict_slashes=False)
@requires_auth(required_permission='manage:inventory')
def adjust_inventory_mass(payload):
    if 'file' not in request.files or 'warehouse_id' not in request.form:
        return jsonify(error="Faltan datos (archivo o almacén)"), 400

    file = request.files['file']
    warehouse_id = request.form['warehouse_id']
    user_id = payload['sub']

    try:
        df = pd.read_excel(file)

        # Columnas esperadas: SKU, Cantidad
        if 'SKU' not in df.columns or 'Cantidad' not in df.columns:
            return jsonify(error="El Excel debe tener las columnas: SKU, Cantidad"), 400

        updated_count = 0
        errors = []

        for index, row in df.iterrows():
            sku = str(row['SKU']).strip()
            try:
                real_quantity = float(row['Cantidad'])
            except:
                continue  # Saltar si la cantidad no es número

            # 1. Buscar el producto
            product = Product.query.filter_by(sku=sku).first()
            if not product:
                errors.append(f"SKU no encontrado: {sku}")
                continue

            # 2. Buscar (o crear) el registro de stock actual
            stock_entry = InventoryStock.query.filter_by(
                product_id=product.id,
                warehouse_id=warehouse_id
            ).first()

            if not stock_entry:
                stock_entry = InventoryStock(
                    product_id=product.id,
                    warehouse_id=warehouse_id,
                    quantity=0.0
                )
                db.session.add(stock_entry)

            current_qty = float(stock_entry.quantity)

            # 3. Calcular la diferencia
            # Si Excel dice 100 y Sistema dice 0, diferencia es +100.
            # Si Excel dice 80 y Sistema dice 100, diferencia es -20.
            difference = real_quantity - current_qty

            if difference != 0:
                # 4. Actualizar Stock
                stock_entry.quantity = real_quantity

                # 5. Crear Transacción (Kardex)
                transaction = InventoryTransaction(
                    product_id=product.id,
                    warehouse_id=warehouse_id,
                    quantity_change=difference,
                    new_quantity=real_quantity,
                    type="Carga Inicial / Ajuste",
                    user_id=user_id
                )
                db.session.add(transaction)
                updated_count += 1

        db.session.commit()

        return jsonify({
            "message": "Proceso completado",
            "updated_products": updated_count,
            "errors": errors
        })

    except Exception as e:
        db.session.rollback()
        print(f"--- ERROR CARGA MASIVA: {e} ---")
        return jsonify(error=str(e)), 500




