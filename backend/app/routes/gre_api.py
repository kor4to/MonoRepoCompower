# En un nuevo archivo de rutas de Flask (ej. routes/gre.py)
# O añádelo a tus rutas existentes

from flask import Blueprint, request, jsonify
from app.services import gre_service  # Importa tu lógica
from datetime import datetime
import time
from flask import current_app
# Crea un "Blueprint" para organizar tus rutas de GRE
gre_bp = Blueprint('gre_api', __name__, url_prefix='/api/gre')


@gre_bp.route('/enviar', methods=['POST'])
def enviar_guia_endpoint():
    """
    Este es el endpoint que tu Vue llamará.
    Contiene la lógica que estaba en main.py de FastAPI.
    """
    datos_guia = request.get_json()

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

        # --- ¡ÉXITO! Devolver el CDR a Vue ---
        return jsonify(resultado_consulta), 200

    except Exception as e:
        print(f"Error general en /api/gre/enviar: {e}")
        return jsonify({"error": str(e)}), 500




# No olvides registrar este Blueprint en el __init__.py de tu app Flask
# from .routes.gre import gre_bp
# app.register_blueprint(gre_bp)