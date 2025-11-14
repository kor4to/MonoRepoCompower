# En un nuevo archivo de rutas de Flask (ej. routes/gre.py)
# O añádelo a tus rutas existentes

from flask import Blueprint, request, jsonify
from app.services import gre_service  # Importa tu lógica
from datetime import datetime
import time
from flask import current_app

# --- INICIO DE CAMBIOS: Importaciones para movimiento de stock ---
from ..extensions import db
from ..services.auth_service import requires_auth
from ..models.stock_transfer import StockTransfer, StockTransferItem
from ..models.inventory_models import InventoryStock, InventoryTransaction
from ..models.product_catalog import Product
from ..models.warehouse import Warehouse # <-- AÑADIDO
# --- FIN DE CAMBIOS ---

# Crea un "Blueprint" para organizar tus rutas de GRE
gre_bp = Blueprint('gre_api', __name__, url_prefix='/api/gre')


# --- INICIO DE CAMBIOS: Se añade autenticación para obtener el user_id ---
@gre_bp.route('/enviar', methods=['POST'])
@requires_auth(required_permission='manage:transfers')
def enviar_guia_endpoint(payload):
# --- FIN DE CAMBIOS ---
    """
    Este es el endpoint que tu Vue llamará.
    Contiene la lógica que estaba en main.py de FastAPI.
    Ahora también registra el movimiento de stock si la GRE es aceptada.
    """
    datos_guia = request.get_json()
    user_id = payload['sub'] # ID del usuario autenticado

    # --- Paso 1: Obtener el Token ---
    print("\n--- Paso 1: Obteniendo Token de SUNAT... ---")
    access_token = gre_service.obtener_token_oauth2()
    if not access_token:
        return jsonify({"error": "Error al obtener el token de SUNAT"}), 401

    try:
        # --- Paso 2: Convertir Fechas ---
        datos_guia['fecha_de_emision'] = datetime.strptime(
            datos_guia['fecha_de_emision'], '%Y-%m-%d'
        ).date()
        datos_guia['fecha_de_inicio_de_traslado'] = datetime.strptime(
            datos_guia['fecha_de_inicio_de_traslado'], '%Y-%m-%d'
        ).date()

        # --- Paso 3: Crear el XML ---
        xml_sin_firmar_bytes = gre_service.crear_xml_guia_remision(datos_guia)

        # --- Paso 4: Firmar el XML ---
        nombre_base_archivo = f"{datos_guia['serie']}-{datos_guia['numero']}"
        xml_firmado_bytes = gre_service.firmar_xml(xml_sin_firmar_bytes, nombre_base_archivo)

        # --- Paso 5: Comprimir, Hashear y Codificar ---
        ruc_emisor = current_app.config['TU_RUC']
        nombre_zip = f"{ruc_emisor}-09-{nombre_base_archivo}.zip"
        zip_base64, _, hash_zip = gre_service.comprimir_y_codificar_base64(xml_firmado_bytes, nombre_zip)

        # --- Paso 6: Enviar a SUNAT ---
        respuesta_envio = gre_service.enviar_guia_sunat_oauth2(
            nombre_zip, zip_base64, access_token, hash_zip
        )
        if not respuesta_envio:
            return jsonify({"error": "Error en la respuesta de SUNAT (Envío)"}), 500

        # --- Paso 7: Consultar el Ticket ---
        ticket_id = respuesta_envio.get('numTicket')
        if not ticket_id:
            return jsonify({"error": "SUNAT no devolvió numTicket."}), 500

        print(f"--- Ticket {ticket_id} recibido. Esperando 3 segundos... ---")
        time.sleep(3)

        resultado_consulta = gre_service.consultar_ticket_sunat(ticket_id, access_token)
        if not resultado_consulta:
            return jsonify({"error": f"Error al consultar el ticket {ticket_id}."}), 500

        # --- INICIO DE CAMBIOS: Lógica de movimiento de stock ---
        # --- INICIO DE CAMBIO: Depuración de la respuesta de SUNAT ---
        print(f"--- DEBUG: Respuesta de SUNAT (Consulta): {resultado_consulta} ---")
        # --- FIN DE CAMBIO ---

        # Solo si la SUNAT aceptó la guía (código de respuesta '0')
        if resultado_consulta.get('codRespuesta') == '0':
            print(f"--- GRE Aceptada. Registrando movimiento de stock... ---")
            try:
                # --- ¡NUEVO! Búsqueda de IDs ---
                # 1. Buscar el ID del almacén de origen por su nombre/dirección
                origin_address = datos_guia.get('punto_de_partida_direccion')
                if not origin_address:
                    raise ValueError("El campo 'punto_de_partida_direccion' es requerido para buscar el almacén de origen.")
                
                warehouse_origen = Warehouse.query.filter_by(address=origin_address).first()
                if not warehouse_origen:
                    raise ValueError(f"No se encontró un almacén con la dirección exacta: '{origin_address}'.")
                origin_warehouse_id = warehouse_origen.id
                
                # 2. Validar que hay items
                if not datos_guia.get('items'):
                    raise ValueError("No hay 'items' en los datos para registrar el movimiento.")

                # 3. Crear el registro de la transferencia
                new_transfer = StockTransfer(
                    user_id=user_id,
                    origin_warehouse_id=origin_warehouse_id, # <-- ID encontrado
                    destination_external_address=datos_guia.get('punto_de_llegada_direccion'),
                    status="Completada (GRE)",
                    transfer_date=datetime.now(),
                    gre_series=datos_guia.get('serie'),
                    gre_number=datos_guia.get('numero'),
                    gre_ticket=ticket_id
                )
                db.session.add(new_transfer)

                # 4. Crear los items y descontar el stock
                for item_data in datos_guia['items']:
                    # --- ¡NUEVO! Buscar el ID del producto por su SKU/código ---
                    item_sku = item_data.get('codigo')
                    if not item_sku:
                        raise ValueError("Cada ítem debe tener un 'codigo' (SKU) para buscarlo en la base de datos.")
                    
                    product = Product.query.filter_by(sku=item_sku).first()
                    if not product:
                        raise ValueError(f"No se encontró un producto con el SKU: '{item_sku}'.")
                    product_id = product.id
                    # --- Fin búsqueda ---

                    # --- INICIO DE CAMBIO: Lógica robusta para obtener la cantidad ---
                    quantity_val = item_data.get('quantity')
                    if quantity_val is None:
                        quantity_val = item_data.get('cantidad')

                    if quantity_val is None:
                        raise ValueError(f"El ítem con SKU {item_sku} no tiene un campo de cantidad ('quantity' o 'cantidad').")
                    
                    quantity = float(quantity_val)
                    # --- FIN DE CAMBIO ---
                    if quantity <= 0:
                        raise ValueError("La cantidad debe ser mayor a 0.")

                    # Crear el item de la transferencia
                    new_item = StockTransferItem(
                        transfer=new_transfer,
                        product_id=product_id, # <-- ID encontrado
                        quantity=quantity
                    )
                    db.session.add(new_item)

                    # Descontar del stock de origen
                    stock_origen = InventoryStock.query.filter_by(
                        product_id=product_id,
                        warehouse_id=origin_warehouse_id
                    ).first()

                    if not stock_origen or float(stock_origen.quantity) < quantity:
                        raise ValueError(f"Stock insuficiente para '{product.name}' (SKU: {item_sku}) en el almacén '{warehouse_origen.name}'.")

                    stock_origen.quantity = float(stock_origen.quantity) - quantity

                    # Registrar la transacción de salida
                    trans_salida = InventoryTransaction(
                        product_id=product_id,
                        warehouse_id=origin_warehouse_id,
                        quantity_change=-quantity,
                        new_quantity=stock_origen.quantity,
                        type="Envío a Terceros (GRE)",
                        user_id=user_id,
                        reference=f"GRE: {datos_guia.get('serie')}-{datos_guia.get('numero')}"
                    )
                    db.session.add(trans_salida)

                # 5. Guardar todos los cambios en la base de datos
                db.session.commit()
                print(f"--- Movimiento de stock para Transferencia ID {new_transfer.id} registrado exitosamente. ---")

            except Exception as db_error:
                db.session.rollback()
                print(f"--- ERROR CRÍTICO: La GRE fue aceptada por SUNAT pero falló el registro en BD: {db_error} ---")
                resultado_consulta['advertencia_interna'] = f"La GRE fue ACEPTADA por SUNAT, pero ocurrió un error al registrar el movimiento de stock: {str(db_error)}"
                return jsonify(resultado_consulta), 500
        # --- FIN DE CAMBIOS ---

        # --- ¡ÉXITO! Devolver el CDR a Vue ---
        return jsonify(resultado_consulta), 200

    except Exception as e:
        print(f"Error general en /api/gre/enviar: {e}")
        return jsonify({"error": str(e)}), 500




# No olvides registrar este Blueprint en el __init__.py de tu app Flask
# from .routes.gre import gre_bp
# app.register_blueprint(gre_bp)