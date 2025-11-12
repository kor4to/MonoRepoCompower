import requests
from lxml import etree
from datetime import date, datetime
from signxml import XMLSigner, methods
from flask import current_app
import os
import zipfile
import io
import base64
import zeep
from zeep.wsse.username import UsernameToken
import ssl
import traceback
import hashlib

# --- Definición de Namespaces ---
NSMAP = {
    None: "urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "sac": "urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    # Añadimos namespaces del XML de ejemplo
    "qdt": "urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2",
    "udt": "urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2",
    "ccts": "urn:un:unece:uncefact:documentation:2"
}


# --- Función para Guardar XML ---
def guardar_xml_en_base(nombre_archivo, xml_contenido_bytes):
    try:
        base_dir = os.getcwd()
        ruta_completa = os.path.join(base_dir, nombre_archivo)
        with open(ruta_completa, 'wb') as f:
            f.write(xml_contenido_bytes)
        print(f"--- 💾 XML Guardado Exitosamente en: {ruta_completa} ---")
    except Exception as e:
        print(f"--- ❌ ERROR al guardar XML: {e} ---")


# --- Función obtener_token_oauth2 (Sin cambios) ---
def obtener_token_oauth2():
    try:
        client_id = current_app.config['SUNAT_CLIENT_ID']
        client_secret = current_app.config['SUNAT_CLIENT_SECRET']
        ruc = current_app.config['TU_RUC']
        sol_user = current_app.config['SUNAT_SOL_USER']
        sol_pass = current_app.config['SUNAT_SOL_PASS']

        username_completo = f"{ruc}{sol_user}"
        token_url = f'https://api-seguridad.sunat.gob.pe/v1/clientessol/{client_id}/oauth2/token/'

        data = {
            'grant_type': 'password',
            'scope': 'https://api.sunat.gob.pe/v1/contribuyente/contribuyentes',
            'client_id': client_id,
            'client_secret': client_secret,
            'username': username_completo,
            'password': sol_pass
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        print("\n--- Solicitando token OAuth2 a SUNAT... ---")
        print(f"URL: {token_url}")
        print(f"Client ID: {client_id}")
        print(f"Client Secret: {client_secret[:4]}...{client_secret[-4:]}")
        print(f"Sol User: {sol_user}")
        print(f"Password: {'*' * len(sol_pass)}")
        print(f"Username (RUC+Usuario): {username_completo}")

        response = requests.post(token_url, data=data, headers=headers)

        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access_token')
            print("--- Token OAuth2 obtenido exitosamente ---")
            print(f"Token: {access_token[:20]}...")
            return access_token
        else:
            print(f"ERROR al obtener token: {response.status_code}")
            print(f"Respuesta: {response.text}")
            return None

    except Exception as e:
        print(f"ERROR en obtener_token_oauth2: {e}")
        traceback.print_exc()
        return None


# --- Función enviar_guia_sunat_oauth2 (Sin cambios) ---
def enviar_guia_sunat_oauth2(nombre_zip, zip_base64, access_token, hash_zip):
    try:
        base_envio_url = 'https://api-cpe.sunat.gob.pe/v1/contribuyente/gem/comprobantes/'
        parametros_url = nombre_zip.replace('.zip', '')
        envio_url = f"{base_envio_url}{parametros_url}"

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        payload = {
            'archivo': {
                'nomArchivo': nombre_zip,
                'arcGreZip': zip_base64,
                'hashZip': hash_zip
            }
        }

        print("\n--- Enviando GRE a SUNAT con OAuth2 (REST)... ---")
        print(f"URL de envío: {envio_url}")
        print(f"Payload (hash): {hash_zip}")
        response = requests.post(envio_url, json=payload, headers=headers)

        print(f"--- Respuesta de SUNAT: {response.status_code} ---")

        if response.status_code == 200:
            respuesta_data = response.json()
            print("--- Documento enviado exitosamente ---")
            print(f"Respuesta SUNAT: {respuesta_data}")
            return respuesta_data
        else:
            print(f"ERROR en el envío: {response.status_code}")
            print(f"Detalle: {response.text}")
            return None

    except Exception as e:
        print(f"ERROR al enviar a SUNAT: {e}")
        return None




# --- Función crear_xml_guia_remisión ---1

def crear_xml_guia_remision(datos_guia):
    """
    Crea la estructura del XML para una Guía de Remisión Remitente (UBL 2.1)
    CORREGIDA para coincidir EXACTAMENTE con el XML de ejemplo TTT1-2.xml
    """
    print("\n--- 📋 Creando XML de Guía (UBL 2.1 - ESTRUCTURA TTT1-2) ---")
    print(datos_guia)
    print("----------------------------------------------------------\n")

    root = etree.Element("DespatchAdvice", nsmap=NSMAP)

    # --- 1. Firma Placeholder (Va primero) ---
    ext_ubl = etree.SubElement(root, etree.QName(NSMAP["ext"], "UBLExtensions"))
    ext_sig = etree.SubElement(ext_ubl, etree.QName(NSMAP["ext"], "UBLExtension"))
    etree.SubElement(ext_sig, etree.QName(NSMAP["ext"], "ExtensionContent"))

    # --- 2. Cabecera (UBL 2.1 y Customization 2.0) ---
    etree.SubElement(root, etree.QName(NSMAP["cbc"], "UBLVersionID")).text = "2.1"
    etree.SubElement(root, etree.QName(NSMAP["cbc"], "CustomizationID")).text = "2.0"
    etree.SubElement(root, etree.QName(NSMAP["cbc"], "ID")).text = f"{datos_guia['serie']}-{datos_guia['numero']}"
    etree.SubElement(root, etree.QName(NSMAP["cbc"], "IssueDate")).text = datos_guia['fecha_de_emision'].strftime(
        '%Y-%m-%d')
    etree.SubElement(root, etree.QName(NSMAP["cbc"], "IssueTime")).text = datetime.now().strftime('%H:%M:%S')
    etree.SubElement(root, etree.QName(NSMAP["cbc"], "DespatchAdviceTypeCode")).text = "09"  # Guía Remitente

    if datos_guia.get('observaciones'):
        etree.SubElement(root, etree.QName(NSMAP["cbc"], "Note")).text = datos_guia['observaciones']

    # --- 3. Bloque <cac:Signature> (Referencia a la firma) ---
    remitente_ruc = current_app.config['TU_RUC']
    remitente_razon_social = current_app.config['TU_RAZON_SOCIAL']

    sig_block = etree.SubElement(root, etree.QName(NSMAP["cac"], "Signature"))
    # El ID del XML de ejemplo es el RUC, no la serie-número
    etree.SubElement(sig_block, etree.QName(NSMAP["cbc"], "ID")).text = remitente_ruc
    sig_party = etree.SubElement(sig_block, etree.QName(NSMAP["cac"], "SignatoryParty"))
    sig_party_id = etree.SubElement(sig_party, etree.QName(NSMAP["cac"], "PartyIdentification"))
    etree.SubElement(sig_party_id, etree.QName(NSMAP["cbc"], "ID")).text = remitente_ruc
    sig_party_name = etree.SubElement(sig_party, etree.QName(NSMAP["cac"], "PartyName"))
    etree.SubElement(sig_party_name, etree.QName(NSMAP["cbc"], "Name")).text = remitente_razon_social
    sig_attach = etree.SubElement(sig_block, etree.QName(NSMAP["cac"], "DigitalSignatureAttachment"))
    sig_ext_ref = etree.SubElement(sig_attach, etree.QName(NSMAP["cac"], "ExternalReference"))
    # El XML de ejemplo usa el RUC, pero '#Sign' es más estándar para referenciar el ID de la firma
    etree.SubElement(sig_ext_ref, etree.QName(NSMAP["cbc"], "URI")).text = "#Sign"

    # --- 4. Remitente (DespatchSupplierParty) ---
    supplier_party = etree.SubElement(root, etree.QName(NSMAP["cac"], "DespatchSupplierParty"))
    etree.SubElement(supplier_party, etree.QName(NSMAP["cbc"], "CustomerAssignedAccountID"),
                     schemeID="6").text = remitente_ruc
    party_supplier = etree.SubElement(supplier_party, etree.QName(NSMAP["cac"], "Party"))
    party_id_supplier = etree.SubElement(party_supplier, etree.QName(NSMAP["cac"], "PartyIdentification"))
    etree.SubElement(party_id_supplier, etree.QName(NSMAP["cbc"], "ID"),
                     schemeID="6",
                     schemeName="Documento de Identidad",
                     schemeAgencyName="PE:SUNAT",
                     schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06").text = remitente_ruc
    party_legal_supplier = etree.SubElement(party_supplier, etree.QName(NSMAP["cac"], "PartyLegalEntity"))
    etree.SubElement(party_legal_supplier, etree.QName(NSMAP["cbc"], "RegistrationName")).text = remitente_razon_social

    # --- 5. Destinatario (DeliveryCustomerParty) ---
    # El XML de ejemplo no usa 'CustomerAssignedAccountID', solo 'Party'
    customer_party = etree.SubElement(root, etree.QName(NSMAP["cac"], "DeliveryCustomerParty"))
    party_customer = etree.SubElement(customer_party, etree.QName(NSMAP["cac"], "Party"))
    party_id_customer = etree.SubElement(party_customer, etree.QName(NSMAP["cac"], "PartyIdentification"))
    etree.SubElement(party_id_customer, etree.QName(NSMAP["cbc"], "ID"),
                     schemeID=str(datos_guia['cliente_tipo_de_documento']),
                     schemeName="Documento de Identidad",
                     schemeAgencyName="PE:SUNAT",
                     schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06").text = datos_guia[
        'cliente_numero_de_documento']
    party_legal_customer = etree.SubElement(party_customer, etree.QName(NSMAP["cac"], "PartyLegalEntity"))
    etree.SubElement(party_legal_customer, etree.QName(NSMAP["cbc"], "RegistrationName")).text = datos_guia[
        'cliente_denominacion']

    # --- 6. Datos del Envío (Shipment) ---
    shipment = etree.SubElement(root, etree.QName(NSMAP["cac"], "Shipment"))
    etree.SubElement(shipment, etree.QName(NSMAP["cbc"], "ID")).text = "SUNAT_Envio"
    etree.SubElement(shipment, etree.QName(NSMAP["cbc"], "HandlingCode"),
                     listAgencyName="PE:SUNAT",
                     listName="Motivo de traslado",
                     listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo20").text = datos_guia[
        'motivo_de_traslado']
    etree.SubElement(shipment, etree.QName(NSMAP["cbc"], "HandlingInstructions")).text = datos_guia['motivo']
    etree.SubElement(shipment, etree.QName(NSMAP["cbc"], "GrossWeightMeasure"),
                     unitCode="KGM").text = str(datos_guia['peso_bruto_total'])

    # --- 7. Datos del Transporte (ShipmentStage) ---
    shipment_stage = etree.SubElement(shipment, etree.QName(NSMAP["cac"], "ShipmentStage"))
    etree.SubElement(shipment_stage, etree.QName(NSMAP["cbc"], "TransportModeCode"),
                     listName="Modalidad de traslado",
                     listAgencyName="PE:SUNAT",
                     listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo18").text = datos_guia[
        'tipo_de_transporte']
    transit_period = etree.SubElement(shipment_stage, etree.QName(NSMAP["cac"], "TransitPeriod"))
    etree.SubElement(transit_period, etree.QName(NSMAP["cbc"], "StartDate")).text = datos_guia[
        'fecha_de_inicio_de_traslado'].strftime('%Y-%m-%d')

    # --- ¡INICIO DE LA CORRECCIÓN! (Basado en TTT1-2.xml) ---
    if datos_guia['tipo_de_transporte'] == '01':  # Público
        carrier_party = etree.SubElement(shipment_stage, etree.QName(NSMAP["cac"], "CarrierParty"))
        party_id_carrier = etree.SubElement(carrier_party, etree.QName(NSMAP["cac"], "PartyIdentification"))
        etree.SubElement(party_id_carrier, etree.QName(NSMAP["cbc"], "ID"), schemeID="6").text = datos_guia[
            'transportista_documento_numero']
        party_legal_carrier = etree.SubElement(carrier_party, etree.QName(NSMAP["cac"], "PartyLegalEntity"))
        etree.SubElement(party_legal_carrier, etree.QName(NSMAP["cbc"], "RegistrationName")).text = datos_guia[
            'transportista_denominacion']

    elif datos_guia['tipo_de_transporte'] == '02':  # Privado

        # 7.1 Vehículo Principal
        transport_means = etree.SubElement(shipment_stage, etree.QName(NSMAP["cac"], "TransportMeans"))
        road_transport = etree.SubElement(transport_means, etree.QName(NSMAP["cac"], "RoadTransport"))
        placa_limpia = datos_guia['transportista_placa_numero'].replace('-', '')
        etree.SubElement(road_transport, etree.QName(NSMAP["cbc"], "LicensePlateID")).text = placa_limpia

        # 7.2 Conductor Principal
        driver_person = etree.SubElement(shipment_stage, etree.QName(NSMAP["cac"], "DriverPerson"))
        etree.SubElement(driver_person, etree.QName(NSMAP["cbc"], "ID"),
                         schemeID=str(datos_guia['conductor_documento_tipo'])).text = datos_guia[
            'conductor_documento_numero']
        etree.SubElement(driver_person, etree.QName(NSMAP["cbc"], "FirstName")).text = datos_guia['conductor_nombre']
        etree.SubElement(driver_person, etree.QName(NSMAP["cbc"], "FamilyName")).text = datos_guia[
            'conductor_apellidos']

        # --- ¡AQUÍ ESTÁ LA LÍNEA QUE FALTA! ---
        etree.SubElement(driver_person, etree.QName(NSMAP["cbc"], "JobTitle")).text = "Principal"

        # --- ¡AQUÍ ESTÁ EL BLOQUE DE LICENCIA QUE FALTA! ---
        if datos_guia.get('licencia'):
            licence = etree.SubElement(driver_person, etree.QName(NSMAP["cac"], "IdentityDocumentReference"))
            etree.SubElement(licence, etree.QName(NSMAP["cbc"], "ID")).text = datos_guia['licencia']

    # --- 8. Direcciones (Estructura de Ejemplo) ---
    delivery = etree.SubElement(shipment, etree.QName(NSMAP["cac"], "Delivery"))

    # Punto de Llegada
    delivery_address = etree.SubElement(delivery, etree.QName(NSMAP["cac"], "DeliveryAddress"))
    etree.SubElement(delivery_address, etree.QName(NSMAP["cbc"], "ID"),
                     schemeAgencyName="PE:INEI",
                     schemeName="Ubigeos").text = datos_guia['punto_de_llegada_ubigeo']
    delivery_address_line = etree.SubElement(delivery_address, etree.QName(NSMAP["cac"], "AddressLine"))
    etree.SubElement(delivery_address_line, etree.QName(NSMAP["cbc"], "Line")).text = datos_guia[
        'punto_de_llegada_direccion']

    # (El tag SAC se eliminó porque no está en el XML TTT1-2)

    # Punto de Partida
    despatch = etree.SubElement(delivery, etree.QName(NSMAP["cac"], "Despatch"))
    despatch_address = etree.SubElement(despatch, etree.QName(NSMAP["cac"], "DespatchAddress"))
    etree.SubElement(despatch_address, etree.QName(NSMAP["cbc"], "ID"),
                     schemeAgencyName="PE:INEI",
                     schemeName="Ubigeos").text = datos_guia['punto_de_partida_ubigeo']
    despatch_address_line = etree.SubElement(despatch_address, etree.QName(NSMAP["cac"], "AddressLine"))
    etree.SubElement(despatch_address_line, etree.QName(NSMAP["cbc"], "Line")).text = datos_guia[
        'punto_de_partida_direccion']

    # (El tag SAC se eliminó porque no está en el XML TTT1-2)

    # --- 9. Vehículo Secundario / Unidad de Transporte (Placa) ---
    # El XML TTT1-2 (privado) añade este bloque para la placa, ADEMÁS del principal.
    if datos_guia['tipo_de_transporte'] == '02':
        handling_unit = etree.SubElement(shipment, etree.QName(NSMAP["cac"], "TransportHandlingUnit"))
        equipment = etree.SubElement(handling_unit, etree.QName(NSMAP["cac"], "TransportEquipment"))
        placa_limpia = datos_guia['transportista_placa_numero'].replace('-', '')
        etree.SubElement(equipment, etree.QName(NSMAP["cbc"], "ID")).text = placa_limpia
    # -----------------------------------------------------------------

    # --- 10. Items (DespatchLine) ---
    line_count = 0
    for item_data in datos_guia.get('items', []):
        line_count += 1
        despatch_line = etree.SubElement(root, etree.QName(NSMAP["cac"], "DespatchLine"))
        etree.SubElement(despatch_line, etree.QName(NSMAP["cbc"], "ID")).text = str(line_count)
        etree.SubElement(despatch_line, etree.QName(NSMAP["cbc"], "DeliveredQuantity"),
                         unitCode=item_data['unidad_de_medida'],
                         unitCodeListID="UN/ECE rec 20",
                         unitCodeListAgencyName="United Nations Economic Commission for Europe").text = str(
            item_data['cantidad'])

        # El XML TTT1-2 usa un LineID = ID + 1. Lo replicamos.
        order_line_ref = etree.SubElement(despatch_line, etree.QName(NSMAP["cac"], "OrderLineReference"))
        etree.SubElement(order_line_ref, etree.QName(NSMAP["cbc"], "LineID")).text = str(line_count + 1)

        item = etree.SubElement(despatch_line, etree.QName(NSMAP["cac"], "Item"))
        etree.SubElement(item, etree.QName(NSMAP["cbc"], "Description")).text = item_data['descripcion']
        if item_data.get('codigo'):
            sellers_item_id = etree.SubElement(item, etree.QName(NSMAP["cac"], "SellersItemIdentification"))
            etree.SubElement(sellers_item_id, etree.QName(NSMAP["cbc"], "ID")).text = item_data['codigo']

    # --- Guardado ---
    xml_bytes = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='utf-8')
    print("\n--- 📄 XML de Guía (UBL 2.1 - ESTRUCTURA TTT1-2) Generado (sin firmar) ---")
    print("--------------------------------------------------------------------\n")

    nombre_archivo_xml = f"{datos_guia['serie']}-{datos_guia['numero']}-GUIA-SIN-FIRMAR.xml"
    guardar_xml_en_base(nombre_archivo_xml, xml_bytes)

    return xml_bytes


# --- FUNCIÓN firmar_xml (Usa SHA256 y añade Id="Sign") ---
def firmar_xml(xml_string_sin_firmar, nombre_base_archivo):
    """
    Firma un string XML (con SHA256) y guarda el resultado.
    """
    try:
        certificado_path = current_app.config['CERTIFICADO_PFX_PATH']
        certificado_pass = current_app.config['CERTIFICADO_PASS']

        with open(certificado_path, "rb") as f:
            pfx_data = f.read()

        root = etree.fromstring(xml_string_sin_firmar)

        xpath_nsmap = {
            "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            "ds": "http://www.w3.org/2000/09/xmldsig#",
            "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
            "sac": "urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance"
        }

        extension_content_node = root.xpath(
            "//ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent",
            namespaces=xpath_nsmap
        )[0]

        from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, NoEncryption, PrivateFormat
        from cryptography.hazmat.backends import default_backend

        try:
            password_bytes = certificado_pass.encode('utf-8') if certificado_pass else None
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                pfx_data,
                password_bytes,
                backend=default_backend()
            )

            if private_key is None or certificate is None:
                raise ValueError("No se pudo extraer la clave privada o el certificado del PFX")

            private_key_bytes = private_key.private_bytes(
                encoding=Encoding.PEM,
                format=PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=NoEncryption()
            )
            certificate_bytes = certificate.public_bytes(Encoding.PEM)

            # Firma con SHA256
            signed_root = XMLSigner(
                method=methods.enveloped,
                digest_algorithm='sha256',  # <-- SHA256
                signature_algorithm='rsa-sha256',  # <-- SHA256
                c14n_algorithm='http://www.w3.org/2001/10/xml-exc-c14n#'  # <-- Algoritmo C14N del ejemplo
            ).sign(root, key=private_key_bytes, cert=certificate_bytes)

            signature_node = signed_root.xpath("//ds:Signature", namespaces=xpath_nsmap)[0]

            # --- ¡NUEVO! Añadimos el Id="Sign" que requiere el template ---
            signature_node.set("Id", "Sign")

            extension_content_node.append(signature_node)

        except Exception as e:
            print(f"ERROR en la carga o firma del certificado: {e}")
            raise

        xml_firmado_bytes = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='utf-8')

        nombre_archivo_firmado = f"{nombre_base_archivo}-GUIA-FIRMADA.xml"
        guardar_xml_en_base(nombre_archivo_firmado, xml_firmado_bytes)

        return xml_firmado_bytes

    except Exception as e:
        print(f"ERROR al firmar el XML: {e}")
        return None


# --- Función para Comprimir y Codificar ---
def comprimir_y_codificar_base64(xml_firmado_bytes, nombre_archivo_zip):
    try:
        nombre_archivo_xml = nombre_archivo_zip.replace('.zip', '.xml')
        in_memory_zip = io.BytesIO()
        with zipfile.ZipFile(in_memory_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(nombre_archivo_xml, xml_firmado_bytes)
        in_memory_zip.seek(0)
        contenido_zip_bytes = in_memory_zip.read()

        hash_sha256 = hashlib.sha256(contenido_zip_bytes).hexdigest()
        contenido_zip_base64 = base64.b64encode(contenido_zip_bytes).decode('utf-8')

        return contenido_zip_base64, nombre_archivo_xml, hash_sha256

    except Exception as e:
        print(f"ERROR al comprimir o codificar: {e}")
        return None, None, None


# --- Función para Consultar Ticket ---
def consultar_ticket_sunat(ticket_id, access_token):
    try:
        base_url = "https://api-cpe.sunat.gob.pe/v1/contribuyente/gem/comprobantes/envios/"
        consult_url = f"{base_url}{ticket_id}"

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        print(f"\n--- Consultando estado del Ticket: {ticket_id} ---")
        print(f"URL de Consulta: {consult_url}")

        response = requests.get(consult_url, headers=headers)

        print(f"--- Respuesta de SUNAT: {response.status_code} ---")

        if response.status_code == 200:
            data = response.json()
            print(f"Respuesta de Consulta: {data}")

            if data.get('arcCdr'):
                print("--- Descargando CDR (Respuesta XML)... ---")
                cdr_zip_bytes = base64.b64decode(data['arcCdr'])

                cdr_zip_filename = f"CDR-{ticket_id}.zip"
                guardar_xml_en_base(cdr_zip_filename, cdr_zip_bytes)

                try:
                    with zipfile.ZipFile(io.BytesIO(cdr_zip_bytes), 'r') as zf:
                        for filename in zf.namelist():
                            if filename.lower().endswith('.xml'):
                                xml_content = zf.read(filename)
                                xml_filename = f"R-{filename}"
                                guardar_xml_en_base(xml_filename, xml_content)
                                print(f"--- XML de Respuesta (CDR) guardado como: {xml_filename} ---")
                except Exception as e:
                    print(f"--- ADVERTENCIA: No se pudo descomprimir el ZIP del CDR: {e} ---")

            return data
        else:
            print(f"Error en consulta: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print(f"ERROR en consultar_ticket_sunat: {e}")
        traceback.print_exc()
        return None


# --- Función para Enviar Factura (SOAP) ---
def enviar_documento_soap(nombre_zip, zip_base64):
    try:
        wsdl_url = "https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService?wsdl"
        ruc = current_app.config['TU_RUC']
        sol_user = current_app.config.get['SUNAT_SOL_USER']
        sol_pass = current_app.config['SUNAT_SOL_PASS']
        username_token = f"{ruc}{sol_user}"
        wsse = UsernameToken(username_token, sol_pass)
        client = zeep.Client(wsdl=wsdl_url, wsse=wsse)
        print(f"\n--- Enviando {nombre_zip} a SUNAT (SOAP)... ---")
        print(f"URL WSDL: {wsdl_url}")
        print(f"Username Token: {username_token}")
        response = client.service.sendBill(fileName=nombre_zip, contentFile=zip_base64)
        cdr_base64 = response.applicationResponse
        print("--- Respuesta de SUNAT (CDR) recibida ---")
        return cdr_base64
    except zeep.exceptions.Fault as fault:
        print(f"ERROR SOAP (Fault): {fault.message}")
        print(f"Detalle: {fault.detail}")
        return None
    except Exception as e:
        print(f"ERROR al enviar a SUNAT (SOAP): {e}")
        return None


# --- FUNCIÓN PARA CREAR EL XML DE LA FACTURA (con typos corregidos) ---
def crear_xml_factura(datos_factura):
    print("\n--- 📋 Creando XML de Factura con los siguientes datos: ---")
    print(datos_factura)
    print("--------------------------------------------------------\n")

    NSMAP_FACTURA = {
        None: "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        "ds": "http://www.w3.org/2000/09/xmldsig#",
        "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        "sac": "urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance"
    }
    emisor_ruc = current_app.config.TU_RUC
    emisor_razon_social = current_app.config.TU_RAZON_SOCIAL
    emisor_ubigeo = "150101"
    emisor_direccion = "AV. MI DIRECCION 123"
    emisor_departamento = "LIMA"
    emisor_provincia = "LIMA"
    emisor_distrito = "LIMA"
    emisor_codigo_pais = "PE"

    root = etree.Element("Invoice", nsmap=NSMAP_FACTURA)

    # Cabecera (Firma primero)
    ext_ubl = etree.SubElement(root, etree.QName(NSMAP_FACTURA["ext"], "UBLExtensions"))
    ext_sig = etree.SubElement(ext_ubl, etree.QName(NSMAP_FACTURA["ext"], "UBLExtension"))
    etree.SubElement(ext_sig, etree.QName(NSMAP_FACTURA["ext"], "ExtensionContent"))

    etree.SubElement(root, etree.QName(NSMAP_FACTURA["cbc"], "UBLVersionID")).text = "2.1"
    etree.SubElement(root, etree.QName(NSMAP_FACTURA["cbc"], "CustomizationID")).text = "2.0"
    etree.SubElement(root, etree.QName(NSMAP_FACTURA["cbc"], "ID")).text = datos_factura['serie_numero']
    etree.SubElement(root, etree.QName(NSMAP_FACTURA["cbc"], "IssueDate")).text = datos_factura['fecha_emision']
    etree.SubElement(root, etree.QName(NSMAP_FACTURA["cbc"], "IssueTime")).text = datos_factura['hora_emision']
    etree.SubElement(root, etree.QName(NSMAP_FACTURA["cbc"], "InvoiceTypeCode"), listID="0101").text = "01"
    etree.SubElement(root, etree.QName(NSMAP_FACTURA["cbc"], "Note"), languageLocaleID="1000").text = datos_factura[
        'monto_en_letras']
    etree.SubElement(root, etree.QName(NSMAP_FACTURA["cbc"], "DocumentCurrencyCode")).text = "PEN"

    # Emisor
    supplier_party = etree.SubElement(root, etree.QName(NSMAP_FACTURA["cac"], "AccountingSupplierParty"))
    party_supplier = etree.SubElement(supplier_party, etree.QName(NSMAP_FACTURA["cac"], "Party"))
    party_id_supplier = etree.SubElement(party_supplier, etree.QName(NSMAP_FACTURA["cac"], "PartyIdentification"))
    etree.SubElement(party_id_supplier, etree.QName(NSMAP_FACTURA["cbc"], "ID"), schemeID="6").text = emisor_ruc
    party_name_supplier = etree.SubElement(party_supplier, etree.QName(NSMAP_FACTURA["cac"], "PartyName"))
    etree.SubElement(party_name_supplier, etree.QName(NSMAP_FACTURA["cbc"], "Name")).text = emisor_razon_social
    party_legal_supplier = etree.SubElement(party_supplier, etree.QName(NSMAP_FACTURA["cac"], "PartyLegalEntity"))
    etree.SubElement(party_legal_supplier,
                     etree.QName(NSMAP_FACTURA["cbc"], "RegistrationName")).text = emisor_razon_social
    reg_address_supplier = etree.SubElement(party_legal_supplier,
                                            etree.QName(NSMAP_FACTURA["cac"], "RegistrationAddress"))
    etree.SubElement(reg_address_supplier, etree.QName(NSMAP_FACTURA["cbc"], "ID")).text = emisor_ubigeo
    etree.SubElement(reg_address_supplier, etree.QName(NSMAP_FACTURA["cbc"], "AddressTypeCode")).text = "0000"
    etree.SubElement(reg_address_supplier,
                     etree.QName(NSMAP_FACTURA["cbc"], "CitySubdivisionName")).text = "URBANIZACION"
    etree.SubElement(reg_address_supplier, etree.QName(NSMAP_FACTURA["cbc"], "CityName")).text = emisor_provincia
    etree.SubElement(reg_address_supplier,
                     etree.QName(NSMAP_FACTURA["cbc"], "CountrySubentity")).text = emisor_departamento
    etree.SubElement(reg_address_supplier, etree.QName(NSMAP_FACTURA["cbc"], "District")).text = emisor_distrito
    address_line_supplier = etree.SubElement(reg_address_supplier, etree.QName(NSMAP_FACTURA["cac"], "AddressLine"))
    etree.SubElement(address_line_supplier, etree.QName(NSMAP_FACTURA["cbc"], "Line")).text = emisor_direccion
    country_supplier = etree.SubElement(reg_address_supplier, etree.QName(NSMAP_FACTURA["cac"], "Country"))
    etree.SubElement(country_supplier,
                     etree.QName(NSMAP_FACTURA["cbc"], "IdentificationCode")).text = emisor_codigo_pais

    # Cliente
    customer_party = etree.SubElement(root, etree.QName(NSMAP_FACTURA["cac"], "AccountingCustomerParty"))
    party_customer = etree.SubElement(customer_party, etree.QName(NSMAP_FACTURA["cac"], "Party"))
    party_id_customer = etree.SubElement(party_customer, etree.QName(NSMAP_FACTURA["cac"], "PartyIdentification"))
    etree.SubElement(party_id_customer, etree.QName(NSMAP_FACTURA["cbc"], "ID"),
                     schemeID=datos_factura['cliente_tipo_doc']).text = datos_factura['cliente_num_doc']
    party_legal_customer = etree.SubElement(party_customer, etree.QName(NSMAP_FACTURA["cac"], "PartyLegalEntity"))
    etree.SubElement(party_legal_customer, etree.QName(NSMAP_FACTURA["cbc"], "RegistrationName")).text = datos_factura[
        'cliente_denominacion']

    # Totales (Impuestos)
    tax_total = etree.SubElement(root, etree.QName(NSMAP_FACTURA["cac"], "TaxTotal"))
    etree.SubElement(tax_total, etree.QName(NSMAP_FACTURA["cbc"], "TaxAmount"),
                     currencyID="PEN").text = f"{datos_factura['total_igv']:.2f}"
    tax_subtotal = etree.SubElement(tax_total, etree.QName(NSMAP_FACTURA["cac"], "TaxSubtotal"))
    etree.SubElement(tax_subtotal, etree.QName(NSMAP_FACTURA["cbc"], "TaxableAmount"),
                     currencyID="PEN").text = f"{datos_factura['total_gravado']:.2f}"
    etree.SubElement(tax_subtotal, etree.QName(NSMAP_FACTURA["cbc"], "TaxAmount"),
                     currencyID="PEN").text = f"{datos_factura['total_igv']:.2f}"
    tax_category = etree.SubElement(tax_subtotal, etree.QName(NSMAP_FACTURA["cac"], "TaxCategory"))
    tax_scheme = etree.SubElement(tax_category, etree.QName(NSMAP_FACTURA["cac"], "TaxScheme"))
    etree.SubElement(tax_scheme, etree.QName(NSMAP_FACTURA["cbc"], "ID")).text = "1000"
    etree.SubElement(tax_scheme, etree.QName(NSMAP_FACTURA["cbc"], "Name")).text = "IGV"
    etree.SubElement(tax_scheme, etree.QName(NSMAP_FACTURA["cbc"], "TaxTypeCode")).text = "VAT"

    # Total General
    legal_monetary_total = etree.SubElement(root, etree.QName(NSMAP_FACTURA["cac"], "LegalMonetaryTotal"))
    etree.SubElement(legal_monetary_total, etree.QName(NSMAP_FACTURA["cbc"], "LineExtensionAmount"),
                     currencyID="PEN").text = f"{datos_factura['total_gravado']:.2f}"
    etree.SubElement(legal_monetary_total, etree.QName(NSMAP_FACTURA["cbc"], "TaxInclusiveAmount"),
                     currencyID="PEN").text = f"{datos_factura['total_general']:.2f}"
    etree.SubElement(legal_monetary_total, etree.QName(NSMAP_FACTURA["cbc"], "PayableAmount"),
                     currencyID="PEN").text = f"{datos_factura['total_general']:.2f}"

    # Items
    line_count = 0
    for item in datos_factura['items']:
        line_count += 1
        line = etree.SubElement(root, etree.QName(NSMAP_FACTURA["cac"], "InvoiceLine"))
        etree.SubElement(line, etree.QName(NSMAP_FACTURA["cbc"], "ID")).text = str(line_count)
        etree.SubElement(line, etree.QName(NSMAP_FACTURA["cbc"], "InvoicedQuantity"),
                         unitCode=item['unidad_de_medida']).text = f"{item['cantidad']:.2f}"
        etree.SubElement(line, etree.QName(NSMAP_FACTURA["cbc"], "LineExtensionAmount"),
                         currencyID="PEN").text = f"{item['valor_total_item']:.2f}"

        price = etree.SubElement(line, etree.QName(NSMAP_FACTURA["cac"], "Price"))
        etree.SubElement(price, etree.QName(NSMAP_FACTURA["cbc"], "PriceAmount"),
                         currencyID="PEN").text = f"{item['valor_unitario']:.2f}"

        pricing_ref = etree.SubElement(line, etree.QName(NSMAP_FACTURA["cac"], "PricingReference"))
        alt_cond_price = etree.SubElement(pricing_ref, etree.QName(NSMAP_FACTURA["cac"], "AlternativeConditionPrice"))
        etree.SubElement(alt_cond_price, etree.QName(NSMAP_FACTURA["cbc"], "PriceAmount"),
                         currencyID="PEN").text = f"{item['precio_unitario']:.2f}"
        etree.SubElement(alt_cond_price, etree.QName(NSMAP_FACTURA["cbc"], "PriceTypeCode")).text = "01"

        item_node = etree.SubElement(line, etree.QName(NSMAP_FACTURA["cac"], "Item"))
        etree.SubElement(item_node, etree.QName(NSMAP_FACTURA["cbc"], "Description")).text = item['descripcion']
        sellers_item_id = etree.SubElement(item_node, etree.QName(NSMAP_FACTURA["cac"], "SellersItemIdentification"))
        etree.SubElement(sellers_item_id, etree.QName(NSMAP_FACTURA["cbc"], "ID")).text = item['codigo']

        tax_total_line = etree.SubElement(line, etree.QName(NSMAP_FACTURA["cac"], "TaxTotal"))
        etree.SubElement(tax_total_line, etree.QName(NSMAP_FACTURA["cbc"], "TaxAmount"),
                         currencyID="PEN").text = f"{item['igv_item']:.2f}"

        tax_subtotal_line = etree.SubElement(tax_total_line, etree.QName(NSMAP_FACTURA["cac"], "TaxSubtotal"))
        etree.SubElement(tax_subtotal_line, etree.QName(NSMAP_FACTURA["cbc"], "TaxableAmount"),
                         currencyID="PEN").text = f"{item['valor_total_item']:.2f}"
        etree.SubElement(tax_subtotal_line, etree.QName(NSMAP_FACTURA["cbc"], "TaxAmount"),
                         currencyID="PEN").text = f"{item['igv_item']:.2f}"

        tax_category_line = etree.SubElement(tax_subtotal_line, etree.QName(NSMAP_FACTURA["cac"], "TaxCategory"))
        etree.SubElement(tax_category_line, etree.QName(NSMAP_FACTURA["cbc"], "Percent")).text = "18.00"
        etree.SubElement(tax_category_line, etree.QName(NSMAP_FACTURA["cbc"], "TaxExemptionReasonCode")).text = "10"

        tax_scheme_line = etree.SubElement(tax_category_line, etree.QName(NSMAP_FACTURA["cac"], "TaxScheme"))
        etree.SubElement(tax_scheme_line, etree.QName(NSMAP_FACTURA["cbc"], "ID")).text = "1000"
        etree.SubElement(tax_scheme_line, etree.QName(NSMAP_FACTURA["cbc"], "Name")).text = "IGV"
        etree.SubElement(tax_scheme_line, etree.QName(NSMAP_FACTURA["cbc"], "TaxTypeCode")).text = "VAT"

    # --- Capturar, imprimir y guardar el XML ---
    xml_bytes = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='utf-8')

    print("\n--- 📄 XML de Factura Generado (sin firmar): ---")
    # print(xml_bytes.decode('utf-8')) # XML Ocultado
    print("-----------------------------------------------\n")

    nombre_archivo_xml = f"{datos_factura['serie_numero']}-FACTURA.xml"
    guardar_xml_en_base(nombre_archivo_xml, xml_bytes)

    return xml_bytes


