from flask import Blueprint, jsonify, request
from ..extensions import db
from ..models.product_catalog import Category
from ..services.auth_service import requires_auth

category_api = Blueprint('category_api', __name__)

# --- RUTA 1: Obtener TODAS las categorías ---
@category_api.route('/', methods=['GET'], strict_slashes=False)
@requires_auth(required_permission='view:catalog')
def get_categories(payload):
    """Devuelve una lista de todas las categorías."""
    try:
        categories = Category.query.order_by(Category.name).all()
        return jsonify([c.to_dict() for c in categories])
    except Exception as e:
        return jsonify(error=str(e)), 500

# --- RUTA 2: Crear una nueva categoría ---
@category_api.route('/', methods=['POST'], strict_slashes=False)
@requires_auth(required_permission='manage:catalog')
def create_category(payload):
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify(error="El campo 'name' es requerido"), 400

    try:
        new_cat = Category(
            name=data['name'],
            description=data.get('description', ''),
            # Si se envía un 'parent_id', se crea como subcategoría
            parent_id=data.get('parent_id')
        )
        db.session.add(new_cat)
        db.session.commit()
        return jsonify(new_cat.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500

# --- RUTA 3: Actualizar una categoría ---
@category_api.route('/<int:cat_id>', methods=['PUT'])
@requires_auth(required_permission='manage:catalog')
def update_category(cat_id, payload):
    data = request.get_json()
    cat = Category.query.get_or_404(cat_id)

    try:
        cat.name = data.get('name', cat.name)
        cat.description = data.get('description', cat.description)
        cat.parent_id = data.get('parent_id', cat.parent_id)

        db.session.commit()
        return jsonify(cat.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500

# --- RUTA 4: Eliminar una categoría ---
@category_api.route('/<int:cat_id>', methods=['DELETE'])
@requires_auth(required_permission='manage:catalog')
def delete_category(cat_id, payload):
    cat = Category.query.get_or_404(cat_id)

    try:
        db.session.delete(cat)
        db.session.commit()
        return jsonify(success=True, message="Categoría eliminada")
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"No se pudo eliminar: {str(e)}"), 500