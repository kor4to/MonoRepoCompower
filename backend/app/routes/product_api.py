from flask import Blueprint, jsonify, request
from ..models.product_catalog import Product, Category # <-- Importa Category
from ..extensions import db # <-- Importa db
from ..services.auth_service import requires_auth
from sqlalchemy import or_

product_api = Blueprint('product_api', __name__)

# --- API 1: Buscar Productos ---
@product_api.route('/search')
@requires_auth(required_permission='view:catalog') # Usamos el permiso de catálogo
def search_products(payload):
    """
    Busca productos por SKU o Nombre.
    Se usa con un parámetro query: /api/products/search?q=cable
    """
    query = request.args.get('q', '') # Obtiene el parámetro 'q' de la URL
    if not query:
        return jsonify([]) # Devuelve vacío si no hay búsqueda

    try:
        search_term = f"%{query.lower()}%"
        products = Product.query.filter(
            or_(
                db.func.lower(Product.name).like(search_term),
                db.func.lower(Product.sku).like(search_term)
            )
        ).limit(20).all() # Limita a 20 resultados

        return jsonify([p.to_dict() for p in products])

    except Exception as e:
        return jsonify(error=str(e)), 500

# --- API 2: Obtener TODOS los productos ---
@product_api.route('/', strict_slashes=False)
@requires_auth(required_permission='view:catalog')
def get_all_products(payload):
    """Devuelve una lista de todos los productos."""
    try:
        products = Product.query.order_by(Product.name).all()
        return jsonify([p.to_dict() for p in products])
    except Exception as e:
        return jsonify(error=str(e)), 500


# --- API 3: Crear un nuevo Producto ---
@product_api.route('/', methods=['POST'])
@requires_auth(required_permission='manage:catalog')
def create_product(payload):
    data = request.get_json()
    if not data.get('sku') or not data.get('name') or not data.get('category_id'):
        return jsonify(error="SKU, Nombre y Categoría son requeridos"), 400

    try:
        new_prod = Product(
            sku=data['sku'],
            name=data['name'],
            description=data.get('description', ''),
            unit_of_measure=data.get('um', 'UND'),
            category_id=data['category_id']
        )
        db.session.add(new_prod)
        db.session.commit()
        return jsonify(new_prod.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500

# --- API 4: Actualizar un Producto ---
@product_api.route('/<int:product_id>', methods=['PUT'])
@requires_auth(required_permission='manage:catalog')
def update_product(product_id, payload):
    data = request.get_json()
    prod = Product.query.get_or_404(product_id)

    try:
        prod.sku = data.get('sku', prod.sku)
        prod.name = data.get('name', prod.name)
        prod.description = data.get('description', prod.description)
        prod.unit_of_measure = data.get('um', prod.unit_of_measure)
        prod.category_id = data.get('category_id', prod.category_id)

        db.session.commit()
        return jsonify(prod.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500