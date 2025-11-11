from flask import Blueprint, jsonify, request, current_app
from ..extensions import db
from ..models.provider import Provider
from ..models.purchase_order import PurchaseOrder, DocumentType, OrderStatus, PurchaseOrderItem
from ..services.auth_service import requires_auth
import requests # ¡Necesitaremos esta librería!
from ..models.cost_center import CostCenter
from sqlalchemy.orm import joinedload

# --- Instala 'requests' ---
# En tu terminal de backend, ejecuta: pip install requests
# --------------------------

purchase_api = Blueprint('purchase_api', __name__)


# --- API 1: La API de SUNAT segura ---
@purchase_api.route('/lookup-provider/<string:ruc>')
@requires_auth(required_permission='create:purchases')
def lookup_provider(ruc, payload):
    provider = Provider.query.filter_by(ruc=ruc).first()
    if provider:
        return jsonify(provider.to_dict())

    print(f"Consultando RUC {ruc} a la API externa...")
    try:
        api_key = current_app.config['SUNAT_API_KEY']
        url = f"https://api.decolecta.com/v1/sunat/ruc?numero={ruc}"
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        data = response.json()

        # --- ¡AÑADIDO PARA DEPURAR! ---
        # Imprimirá la respuesta de la API en tu terminal de Flask
        print("--- RESPUESTA DE API SUNAT ---")
        print(data)
        # ---------------------------------

        # Asumamos que los campos son 'ruc' y 'razon_social'
        new_provider = Provider(
            ruc=data['numero_documento'],  # <-- ¡ESTE ERA EL ERROR!
            name=data['razon_social']  # <-- Esta ya estaba bien
        )

        db.session.add(new_provider)
        db.session.commit()
        return jsonify(new_provider.to_dict())

    except requests.exceptions.RequestException as e:
        try:
            error_msg = e.response.json().get('message', 'Error externo')
        except:
            error_msg = str(e)
        return jsonify(error=f"Error al consultar RUC: {error_msg}"), 404
    except KeyError as e:
        # ¡NUEVO! Esto atrapará el error si 'ruc' o 'razon_social' son incorrectos
        print(f"Error de clave: {e}. La respuesta de la API no tiene esa clave.")
        return jsonify(error=f"Error de clave: {e}. La respuesta de la API no tiene esa clave."), 500
    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500

# --- API 2: Obtener los catálogos ---
@purchase_api.route('/catalogs')
@requires_auth(required_permission='create:purchases')
def get_purchase_catalogs(payload):
    doc_types = DocumentType.query.all()
    statuses = OrderStatus.query.all()
    cost_centers = CostCenter.query.filter_by(status='Activo').all() # <-- ¡NUEVO!

    return jsonify({
        'document_types': [d.to_dict() for d in doc_types],
        'statuses': [s.to_dict() for s in statuses],
        'cost_centers': [cc.to_dict() for cc in cost_centers] # <-- ¡NUEVO!
    })

# --- ¡ARREGLO AQUÍ! ---
@purchase_api.route('/', methods=['GET'], strict_slashes=False)
@requires_auth(required_permission='view:purchases')
def get_purchases(payload):
    try:
        # ¡VOLVEMOS A LA CONSULTA SIMPLE!
        orders = PurchaseOrder.query.order_by(PurchaseOrder.id.desc()).all()

        # Tu función 'to_dict()' segura (del paso anterior) hará el trabajo.
        return jsonify([o.to_dict() for o in orders])

    except Exception as e:
        print(f"--- ERROR AL OBTENER ÓRDENES: {str(e)} ---")
        return jsonify(error=str(e)), 500

# --- API 4: CREAR Órdenes (POST) ---
@purchase_api.route('/', methods=['POST'], strict_slashes=False)
@requires_auth(required_permission='create:purchases')
def create_purchase(payload):
    data = request.get_json()

    # Validación de datos de cabecera
    required_fields = ['provider_id', 'document_type_id', 'document_number', 'status_id', 'cost_center_id', 'items']
    if not all(field in data for field in required_fields):
        return jsonify(error="Faltan datos (provider, doc_type, status, cost_center, items)"), 400

    if not data['items'] or len(data['items']) == 0:
        return jsonify(error="La orden debe tener al menos un item"), 400

    try:
        # 1. Crear la Orden de Compra (Cabecera)
        new_po = PurchaseOrder(
            document_number=data['document_number'],
            owner_id=payload['sub'],
            provider_id=data['provider_id'],
            document_type_id=data['document_type_id'],
            status_id=data['status_id'],
            cost_center_id=data['cost_center_id']
        )

        db.session.add(new_po)

        # 2. Crear los Items
        # 2. Crear los Items
        for item_data in data['items']:

            # ¡NUEVA VALIDACIÓN!
            if not item_data.get('invoice_detail_text'):
                raise ValueError("El 'Detalle (Factura)' es requerido para todos los items")

            try:
                quantity = float(item_data.get('quantity') or 0.0)
            except (ValueError, TypeError):
                quantity = 0.0

            try:
                unit_price = float(item_data.get('unit_price') or 0.0)
            except (ValueError, TypeError):
                unit_price = 0.0

            new_item = PurchaseOrderItem(
                order=new_po,
                product_id=None,  # <-- Se guarda como NULO
                invoice_detail_text=item_data['invoice_detail_text'],  # <-- Se guarda el texto
                unit_of_measure=item_data.get('um', 'UND'),
                quantity=quantity,
                unit_price=unit_price
            )
            db.session.add(new_item)

        # 3. Guardar TODO (Cabecera e Items) en una sola transacción
        db.session.commit()
        # Refresca el objeto 'new_po' para cargar las relaciones
        db.session.refresh(new_po)
        return jsonify(new_po.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        print(f"--- ERROR AL GUARDAR ORDEN: {str(e)} ---")
        return jsonify(error=str(e)), 500


# --- API 5: OBTENER UNA SOLA ORDEN POR ID ---
@purchase_api.route('/<int:order_id>', methods=['GET'])
@requires_auth(required_permission='view:purchases')
def get_purchase_by_id(order_id, payload):
    try:
        # ¡VOLVEMOS A LA CONSULTA SIMPLE!
        order = PurchaseOrder.query.get_or_404(order_id)

        return jsonify(order.to_dict())

    except Exception as e:
        return jsonify(error=str(e)), 500

# --- API 6: OBTENER ÓRDENES PENDIENTES DE RECEPCIÓN ---
@purchase_api.route('/receivable', methods=['GET'])
@requires_auth(required_permission='manage:inventory')
def get_receivable_orders(payload):
    """
    Devuelve una lista de todas las órdenes que están "Aprobadas"
    o en "Borrador" y están listas para ser recibidas.
    """
    try:
        # Busca órdenes que no estén "Recibidas"
        # (Asumimos que "Aprobada" y "Borrador" son los estados previos)
        orders = PurchaseOrder.query.join(OrderStatus).filter(
            OrderStatus.name != 'Recibida'
        ).order_by(PurchaseOrder.id.desc()).all()

        return jsonify([o.to_dict() for o in orders])
    except Exception as e:
        return jsonify(error=str(e)), 500