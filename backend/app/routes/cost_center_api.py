from flask import Blueprint, jsonify, request
from ..extensions import db
from ..models.cost_center import CostCenter # <-- Modelo actualizado
from ..services.auth_service import requires_auth

cost_center_api = Blueprint('cost_center_api', __name__) # <-- Blueprint renombrado

# --- RUTA 1: Obtener todos ---
@cost_center_api.route('/', strict_slashes=False)
@requires_auth(required_permission='view:cost_centers') # <-- Permiso actualizado
def get_cost_centers(payload):
    try:
        cost_centers = CostCenter.query.order_by(CostCenter.name).all()
        return jsonify([cc.to_dict() for cc in cost_centers])
    except Exception as e:
        return jsonify(error=str(e)), 500

# --- RUTA 2: Crear uno nuevo ---
@cost_center_api.route('/', methods=['POST'])
@requires_auth(required_permission='create:cost_centers')
def create_cost_center(payload):
    data = request.get_json()
    if not data or not data.get('name') or not data.get('code'):
        return jsonify(error="Los campos 'name' y 'code' son requeridos"), 400

    try:
        owner_id = payload['sub']

        # --- ¡BLOQUE CORREGIDO! ---
        # Ahora leemos todos los campos del formulario (data)
        new_cc = CostCenter(
            code=data['code'],
            name=data['name'],
            description=data.get('description'),
            status=data.get('status', 'Activo'),
            budget=data.get('budget', 0.00), # <-- ¡LÍNEA AÑADIDA!
            owner_id=owner_id
        )
        # ---------------------------

        db.session.add(new_cc)
        db.session.commit()

        return jsonify(new_cc.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500
# --- ¡NUEVA RUTA! 3: Actualizar (para el presupuesto) ---
@cost_center_api.route('/<int:cc_id>', methods=['PUT'])
@requires_auth(required_permission='edit:cost_centers') # <-- Nuevo permiso
def update_cost_center(cc_id, payload):
    """
    Actualiza un centro de costos.
    Permite cambiar nombre, descripción, estado y presupuesto.
    """
    data = request.get_json()
    if not data:
        return jsonify(error="No se recibieron datos"), 400

    try:
        cc = CostCenter.query.get_or_404(cc_id)

        # Actualiza los campos si vienen en el JSON
        if 'name' in data:
            cc.name = data['name']
        if 'description' in data:
            cc.description = data['description']
        if 'status' in data:
            cc.status = data['status']
        if 'budget' in data:
            cc.budget = data['budget']

        db.session.commit()
        return jsonify(cc.to_dict())

    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500