from flask import Blueprint, jsonify, request
from ..extensions import db
from sqlalchemy.orm import joinedload
from ..services.auth_service import requires_auth
from datetime import datetime

# Importamos TODOS los modelos que necesitamos
from ..models.stock_transfer import StockTransfer, StockTransferItem
from ..models.inventory_models import InventoryStock, InventoryTransaction
from ..models.product_catalog import Product
from ..models.warehouse import Warehouse

transfer_api = Blueprint('transfer_api', __name__)

# --- RUTA 1: Obtener TODAS las transferencias ---
@transfer_api.route('/', methods=['GET'], strict_slashes=False)
@requires_auth(required_permission='view:transfers')
def get_transfers(payload):
    """Devuelve una lista de todas las transferencias."""
    try:
        transfers = StockTransfer.query.options(
            joinedload(StockTransfer.origin_warehouse),
            joinedload(StockTransfer.destination_warehouse)
        ).order_by(StockTransfer.id.desc()).all()

        return jsonify([t.to_dict() for t in transfers])
    except Exception as e:
        return jsonify(error=str(e)), 500


# --- RUTA 2: Crear una nueva transferencia (SIN GRE) ---
@transfer_api.route('/', methods=['POST'], strict_slashes=False)
@requires_auth(required_permission='manage:transfers')
def create_transfer(payload):
    data = request.get_json()
    user_id = payload['sub']

    # --- ¡CORRECCIÓN AQUÍ! ---
    # 1. Obtenemos el objeto 'transfer_data' anidado primero
    transfer_data = data.get('transfer_data')
    if not transfer_data:
        return jsonify(error="Falta el objeto 'transfer_data'"), 400

    # 2. Ahora validamos DENTRO de ese objeto
    if not transfer_data.get('origin_warehouse_id') or not transfer_data.get('items'):
        return jsonify(error="Faltan 'origin_warehouse_id' o 'items'"), 400
    # --- FIN DE LA CORRECCIÓN ---

    try:
        # --- 1. Lógica de Inventario y Base de Datos ---
        new_transfer = StockTransfer(
            user_id=user_id,
            origin_warehouse_id=transfer_data['origin_warehouse_id'],  # <-- Usamos transfer_data
            destination_warehouse_id=transfer_data.get('destination_warehouse_id'),  # <-- Usamos transfer_data
            destination_external_address=transfer_data.get('destination_external_address'),  # <-- Usamos transfer_data
            status="Completada",  # Es instantáneo
            transfer_date=datetime.now()
        )
        db.session.add(new_transfer)

        # 1.2 Crear los items y mover el stock
        for item_data in transfer_data['items']:  # <-- Usamos transfer_data
            product_id = item_data['product_id']
            quantity = float(item_data['quantity'])

            if quantity <= 0:
                raise ValueError("La cantidad debe ser mayor a 0.")

            # Verificamos que el producto exista
            product = Product.query.get(product_id)
            if not product:
                raise ValueError(f"Producto ID {product_id} no encontrado.")

            new_item = StockTransferItem(
                transfer=new_transfer,
                product_id=product_id,
                quantity=quantity
            )
            db.session.add(new_item)

            # --- Lógica de Stock (Salida) ---
            stock_origen = InventoryStock.query.filter_by(
                product_id=product_id,
                warehouse_id=transfer_data['origin_warehouse_id']
            ).first()

            if not stock_origen or float(stock_origen.quantity) < quantity:
                raise ValueError(f"Stock insuficiente para {product.name} en el almacén de origen.")

            stock_origen.quantity = float(stock_origen.quantity) - quantity

            trans_salida = InventoryTransaction(
                product_id=product_id,
                warehouse_id=transfer_data['origin_warehouse_id'],
                quantity_change=-quantity,
                new_quantity=stock_origen.quantity,
                type="Transferencia Salida",
                user_id=user_id
            )
            db.session.add(trans_salida)

            # --- Lógica de Stock (Entrada) ---
            if new_transfer.destination_warehouse_id:
                stock_destino = InventoryStock.query.filter_by(
                    product_id=product_id,
                    warehouse_id=new_transfer.destination_warehouse_id
                ).first()

                if not stock_destino:
                    stock_destino = InventoryStock(product_id=product_id,
                                                   warehouse_id=new_transfer.destination_warehouse_id, quantity=0.0)
                    db.session.add(stock_destino)

                stock_destino.quantity = float(stock_destino.quantity) + quantity

                trans_entrada = InventoryTransaction(
                    product_id=product_id,
                    warehouse_id=new_transfer.destination_warehouse_id,
                    quantity_change=quantity,
                    new_quantity=stock_destino.quantity,
                    type="Transferencia Entrada",
                    user_id=user_id
                )
                db.session.add(trans_entrada)

        # 1.3 Guardar todo
        db.session.commit()

        print(f"--- Transferencia ID {new_transfer.id} creada. ---")

        db.session.refresh(new_transfer)
        return jsonify(new_transfer.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        print(f"--- ERROR AL CREAR TRANSFERENCIA: {str(e)} ---")
        return jsonify(error=str(e)), 500

# --- RUTA 3: Obtener el detalle de UNA transferencia ---
@transfer_api.route('/<int:transfer_id>', methods=['GET'])
@requires_auth(required_permission='view:transfers')
def get_transfer_detail(transfer_id, payload):
    """Devuelve el detalle de una transferencia específica."""
    try:
        transfer = StockTransfer.query.options(
            joinedload(StockTransfer.origin_warehouse),
            joinedload(StockTransfer.destination_warehouse),
            joinedload(StockTransfer.items).joinedload(StockTransferItem.product)
        ).get(transfer_id)

        if not transfer:
            return jsonify(error="Transferencia no encontrada"), 404

        return jsonify(transfer.to_dict())
    except Exception as e:
        print(f"--- ERROR OBTENIENDO DETALLE DE TRANSFERENCIA: {e} ---")
        return jsonify(error=str(e)), 500