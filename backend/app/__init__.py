import os
from flask import Flask, jsonify
from .extensions import db, cors
from config import Config

# --- 1. IMPORTACIÓN DE MODELOS (Limpia) ---
# Importamos todas las clases que la BD necesita conocer
from .models.role import Role
from .models.permission import Permission
from .models.cost_center import CostCenter
from .models.provider import Provider
from .models.product_catalog import Category, Product
from .models.warehouse import Warehouse
from .models.inventory_models import InventoryStock, InventoryTransaction
from .models.purchase_order import PurchaseOrder, DocumentType, OrderStatus, PurchaseOrderItem
from .models.stock_transfer import StockTransfer, StockTransferItem

# Importa el decorador y el error
from .services.auth_service import AuthError, requires_auth


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    # --- 2. INICIALIZACIÓN DE EXTENSIONES ---
    db.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": [
                    "http://localhost:5173",
                    "https://192.168.1.59:5173",
                    "https://localhost:5173"
    ]}},
    allow_headers = ["Authorization", "Content-Type"],
    expose_headers = ["Authorization"],
    supports_credentials = True
    )

    # --- 3. REGISTRO DE BLUEPRINTS (Rutas) ---
    from .routes.main_api import main_api
    from .routes.admin_api import admin_api
    from .routes.cost_center_api import cost_center_api
    from .routes.purchase_api import purchase_api  # <-- ¡ASEGÚRATE QUE ESTA LÍNEA EXISTA!
    from .routes.product_api import product_api
    from .routes.inventory_api import inventory_api
    from .routes.warehouse_api import warehouse_api
    from .routes.category_api import category_api
    from .routes.transfer_api import transfer_api
    from .routes.gre_api import gre_bp





    app.register_blueprint(transfer_api, url_prefix='/api/transfers')
    app.register_blueprint(warehouse_api, url_prefix='/api/warehouses')
    app.register_blueprint(category_api, url_prefix='/api/categories')
    app.register_blueprint(inventory_api, url_prefix='/api/inventory')
    app.register_blueprint(main_api, url_prefix='/api')
    app.register_blueprint(admin_api, url_prefix='/api/admin')
    app.register_blueprint(cost_center_api, url_prefix='/api/cost-centers')
    app.register_blueprint(purchase_api, url_prefix='/api/purchases')  # <-- ¡Y QUE ESTA TAMBIÉN EXISTA!
    app.register_blueprint(product_api, url_prefix='/api/products')
    app.register_blueprint(gre_bp, url_prefix='/api/gre')

    # --- 4. MANEJADOR DE ERRORES ---
    @app.errorhandler(AuthError)
    def handle_auth_error(ex):
        response = jsonify(ex.error)
        response.status_code = ex.status_code
        return response

    # --- 5. CREACIÓN DE BASE DE DATOS Y SEEDING ---
    with app.app_context():
        # Crea la carpeta 'instance' si no existe
        os.makedirs(app.instance_path, exist_ok=True)

        # Crea todas las tablas definidas en los modelos importados
        db.create_all()

        # Llama a la función de seeding (definida abajo)
        _seed_database()

    return app


# --- FUNCIÓN DE SEEDING (Limpia) ---
def _seed_database():
    """
    Crea los roles, permisos y catálogos por defecto.
    """
    # --- 1. PERMISOS ---
    # Solo se ejecuta si la tabla de permisos está vacía
    if Permission.query.count() == 0:
        print("Creando permisos por defecto...")
        permissions_list = [
            Permission(name='view:home', display_name='Novedades', description='Acceso a la página de bienvenida'),
            Permission(name='view:modulo_1', display_name='Módulo 1', description='Acceso al Módulo 1'),
            Permission(name='view:modulo_2', display_name='Módulo 2', description='Acceso al Módulo 2'),
            Permission(name='view:modulo_3', display_name='Módulo 3', description='Acceso al Módulo 3'),
            Permission(name='access:admin_panel', display_name='Panel de Admin', description='Acceso para gestionar roles'),
            Permission(name='view:cost_centers', display_name='Ver Centros de Costos', description='Ver la lista de centros de costos'),
            Permission(name='create:cost_centers', display_name='Crear Centros de Costos', description='Crear nuevos centros de costos'),
            Permission(name='edit:cost_centers', display_name='Editar Centros de Costos', description='Editar centros de costos'),
            Permission(name='view:purchases', display_name='Ver Órdenes de Compra', description='Ver la lista de órdenes de compra'),
            Permission(name='create:purchases', display_name='Crear Órdenes de Compra', description='Crear nuevas órdenes de compra'),
            Permission(name='view:catalog', display_name='Ver Catálogo', description='Ver lista de productos y categorías'),
            Permission(name='manage:catalog', display_name='Gestionar Catálogo', description='Crear/editar productos y categorías'),
            Permission(name='view:inventory', display_name='Ver Inventario', description='Ver stock actual'),
            Permission(name='manage:inventory', display_name='Gestionar Inventario', description='Hacer recepciones y ajustes de stock'),
            Permission(name='view:transfers', display_name='Ver Movimientos de Stock',
                       description='Ver la lista de transferencias de stock'),
            Permission(name='manage:transfers', display_name='Gestionar Movimientos',
                       description='Crear transferencias y enviar GRE a SUNAT')
        ]
        db.session.add_all(permissions_list)
        db.session.commit() # Commit solo para permisos

    # --- 2. CATÁLOGOS (Cada uno en su propio check) ---
    if Category.query.count() == 0:
        print("Creando categorías por defecto...")
        cat_cables = Category(name='Cables', description='Cables eléctricos y de red')
        cat_herr = Category(name='Herramientas', description='Herramientas manuales')
        db.session.add_all([cat_cables, cat_herr])
        db.session.commit()

        prod_cable = Product(
            sku='CB-THW-14',
            name='CABLE/THW #14',
            unit_of_measure='Metros',
            standard_price=2.50,  # <-- Precio
            category_id=cat_cables.id
        )
        prod_clavo = Product(
            sku='HR-CLV-3',
            name='Clavos de 3"',
            unit_of_measure='Kilos',
            standard_price=15.00,  # <-- Precio
            category_id=cat_herr.id
        )
        db.session.add_all([prod_cable, prod_clavo])
        db.session.commit()

    if Warehouse.query.count() == 0:
        print("Creando almacenes por defecto...")
        db.session.add_all([
            Warehouse(name='Almacén Surco', location='Lima'),
            Warehouse(name='Almacén Cusco', location='Cusco')
        ])
        db.session.commit()

    if DocumentType.query.count() == 0:
        print("Creando tipos de documento...")
        db.session.add_all([
            DocumentType(name='Factura'),
            DocumentType(name='Orden de Compra'),
            DocumentType(name='Boleta')
        ])
        db.session.commit()

    if OrderStatus.query.count() == 0:
        print("Creando estados de orden...")
        db.session.add_all([
            OrderStatus(name='Borrador'),
            OrderStatus(name='Aprobada'),
            OrderStatus(name='Recibida')
        ])
        db.session.commit()

    # --- 3. ROLES (Se ejecutan al final) ---
    permissions_map = {p.name: p for p in Permission.query.all()}

    if Role.query.filter_by(name='Admin').first() is None:
        print("Creando rol 'Admin' por defecto...")
        admin_perms = list(permissions_map.values())
        admin_role = Role(name='Admin', permissions=admin_perms)
        db.session.add(admin_role)
        db.session.commit()

    if Role.query.filter_by(name='Usuario').first() is None:
        print("Creando rol 'Usuario' por defecto...")
        user_perms_names = [
            'view:home', 'view:modulo_1', 'view:cost_centers',
            'view:purchases', 'create:purchases', 'view:catalog', 'view:inventory',
            'view:transfers', 'manage:transfers'
        ]
        user_perms = [permissions_map.get(name) for name in user_perms_names if permissions_map.get(name)]
        user_role = Role(name='Usuario', permissions=user_perms)
        db.session.add(user_role)
        db.session.commit()