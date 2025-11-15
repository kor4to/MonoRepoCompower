from flask import Blueprint, jsonify, request
from ..models.product_catalog import Product, Category # <-- Importa Category
from ..extensions import db # <-- Importa db
from ..services.auth_service import requires_auth
from sqlalchemy import or_
import pandas as pd

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
            standard_price=data.get('standard_price', 0.00),
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
        prod.standard_price = data.get('standard_price', prod.standard_price)
        prod.category_id = data.get('category_id', prod.category_id)

        db.session.commit()
        return jsonify(prod.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500


# --- API 5: Importación Masiva desde Excel ---
@product_api.route('/import', methods=['POST'], strict_slashes=False)
@requires_auth(required_permission='manage:catalog')
def import_products(payload):
    if 'file' not in request.files:
        return jsonify(error="No se envió ningún archivo"), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify(error="No se seleccionó ningún archivo"), 400

    try:
        # 1. Leer el Excel con Pandas
        df = pd.read_excel(file)

        # 2. Validar columnas requeridas
        required_columns = ['SKU', 'Nombre', 'Categoria'] # (UM, Descripcion y Precio son opcionales)
        if not all(col in df.columns for col in required_columns):
            return jsonify(error=f"El Excel debe tener las columnas: {', '.join(required_columns)}"), 400

        created_count = 0
        updated_count = 0
        errors = []

        # 3. Iterar sobre cada fila
        for index, row in df.iterrows():
            sku = str(row['SKU']).strip()
            name = str(row['Nombre']).strip()
            cat_name = str(row['Categoria']).strip()

            # Buscar la categoría por nombre
            category = Category.query.filter(db.func.lower(Category.name) == cat_name.lower()).first()
            if not category:
                # Si no existe, la creamos automáticamente (Opcional, pero útil)
                category = Category(name=cat_name, description="Creada por importación")
                db.session.add(category)
                db.session.flush() # Para obtener el ID inmediatamente

            # Buscar si el producto ya existe (por SKU)
            product = Product.query.filter_by(sku=sku).first()

            if product:
                # ACTUALIZAR existente
                product.name = name
                product.category_id = category.id
                if 'Descripcion' in row and pd.notna(row['Descripcion']):
                    product.description = str(row['Descripcion'])
                if 'UM' in row and pd.notna(row['UM']):
                    product.unit_of_measure = str(row['UM'])
                if 'Precio' in row and pd.notna(row['Precio']):
                    product.standard_price = float(row['Precio'])
                updated_count += 1
            else:
                # CREAR nuevo
                new_prod = Product(
                    sku=sku,
                    name=name,
                    category_id=category.id,
                    description=str(row['Descripcion']) if 'Descripcion' in row and pd.notna(row['Descripcion']) else '',
                    unit_of_measure=str(row['UM']) if 'UM' in row and pd.notna(row['UM']) else 'UND',
                    standard_price=float(row['Precio']) if 'Precio' in row and pd.notna(row['Precio']) else 0.00
                )
                db.session.add(new_prod)
                created_count += 1

        db.session.commit()

        return jsonify({
            "message": "Importación completada",
            "created": created_count,
            "updated": updated_count
        })

    except Exception as e:
        db.session.rollback()
        print(f"--- ERROR EN IMPORTACIÓN: {e} ---")
        return jsonify(error=f"Error al procesar el archivo: {str(e)}"), 500

# --- API 6: Eliminar un Producto ---
@product_api.route('/<int:product_id>', methods=['DELETE'])
@requires_auth(required_permission='manage:catalog')
def delete_product(product_id, payload):
    prod = Product.query.get_or_404(product_id)
    try:
        db.session.delete(prod)
        db.session.commit()
        return jsonify(message="Producto eliminado correctamente"), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500


