<script setup>
import { ref, onMounted, watch, computed } from 'vue' // <-- Añadido 'computed'
import { useAuth0 } from '@auth0/auth0-vue'
import { useRouter } from 'vue-router'
import { Button } from '@/components/ui/button/index.js'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card/index.js'
import { Input } from '@/components/ui/input/index.js'
import { Label } from '@/components/ui/label/index.js'
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Loader2, Plus, Trash2, Search } from 'lucide-vue-next' // <-- Modificado
// --- ¡NUEVO! Importar RadioGroup ---
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group/index.js'

const { getAccessTokenSilently } = useAuth0()
const router = useRouter()

// --- Refs de Estado ---
const isLoading = ref(true)
const isSubmitting = ref(false)
const isLookingUpRuc = ref(false)
const error = ref(null)
const successMessage = ref(null)

// --- Refs de Datos ---
const warehouses = ref([])
const productCatalog = ref([])
const lineItems = ref([]) // Esta será la lista de items agregados

// --- URL del Backend de Flask ---
const FLASK_API_URL = 'https://192.168.1.59:5000/api'

// --- ¡NUEVO! Ref para los Radio Buttons ---
const transferType = ref('sin_gre') // 'sin_gre' o 'con_gre'

// --- DATOS DEL FORMULARIO ---
// 1. Datos de Transferencia (Lo que ya tenías)
const transferData = ref({
  origin_warehouse_id: null,
  destination_warehouse_id: null,
  destination_external_address: '',
})

// 2. Datos para la Guía de Remisión (GRE)
const greData = ref({
  serie: 'T002',
  numero: 1, // Deberías obtener esto de tu backend
  fecha_de_emision: new Date().toISOString().split('T')[0],
  fecha_de_inicio_de_traslado: new Date().toISOString().split('T')[0],
  observaciones: 'Prueba de GRE desde Vue',
  peso_bruto_total: 1.0,

  // Req #2: Destinatario
  cliente_tipo_de_documento: 6, // 6 = RUC
  cliente_numero_de_documento: '',
  cliente_denominacion: '',

  // Req #4: Motivo
  motivo_de_traslado: '01', // 01 = Venta (default)
  motivo_otros_descripcion: '', // Para "Otros"

  // Req #3: Transporte
  tipo_de_transporte: '02', // 02 = Privado (default)
  transportista_placa_numero: '',
  marca_vehiculo: '', // ¡Campo digitable!
  conductor_documento_tipo: '1', // 1 = DNI (default)
  conductor_documento_numero: '',
  licencia: '',
  conductor_nombre: '',
  conductor_apellidos: '',

  // Direcciones (Se llenan automáticamente)
  punto_de_partida_ubigeo: '',
  punto_de_partida_direccion: '',
  punto_de_llegada_ubigeo: '',
  punto_de_llegada_direccion: '',
})


// --- ¡NUEVO! Refs para el buscador de productos ---
const productSearchQuery = ref('')
const filteredProductCatalog = computed(() => {
  if (!productSearchQuery.value || productSearchQuery.value.length < 2) {
    return [] // No mostrar nada si la búsqueda es corta
  }
  return productCatalog.value.filter(p =>
    (p.name && p.name.toLowerCase().includes(productSearchQuery.value.toLowerCase())) ||
    (p.sku && p.sku.toLowerCase().includes(productSearchQuery.value.toLowerCase()))
  ).slice(0, 10) // Limitar a 10 resultados
})
// ------------------------------------------------

// Cargar Almacenes y Productos
onMounted(async () => {
  try {
    const token = await getAccessTokenSilently()
    const whRes = await fetch(`${FLASK_API_URL}/warehouses`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    warehouses.value = await whRes.json()

    const prodRes = await fetch(`${FLASK_API_URL}/products`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    productCatalog.value = await prodRes.json()

    // Ya no añadimos una fila por defecto
    // addNewLineItem()
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
})

// --- Watchers para Origen y Destino ---
watch(() => transferData.value.origin_warehouse_id, (whId) => {
  const wh = warehouses.value.find(w => w.id === whId)
  if (wh) {
    greData.value.punto_de_partida_ubigeo = wh.ubigeo
    greData.value.punto_de_partida_direccion = wh.location
  }
})

// --- ¡NUEVO! Limpiar campos al cambiar de tipo de transferencia ---
watch(transferType, (newVal) => {
  // Limpiar mensajes
  error.value = null
  successMessage.value = null

  if (newVal === 'sin_gre') {
    // Modo "Sin GRE": Limpiar dirección externa
    transferData.value.destination_external_address = ''
    greData.value.punto_de_llegada_direccion = ''
    greData.value.punto_de_llegada_ubigeo = ''
  } else {
    // Modo "Con GRE": Limpiar almacén destino interno
    transferData.value.destination_warehouse_id = null
  }
})

watch(() => transferData.value.destination_warehouse_id, (newVal) => {
  // Solo se activa si estamos en modo "Sin GRE"
  if (transferType.value === 'sin_gre' && newVal) {
      transferData.value.destination_external_address = '' // (redundant, but safe)
      const wh = warehouses.value.find(w => w.id === newVal)
      if (wh) {
        greData.value.punto_de_llegada_ubigeo = wh.ubigeo
        greData.value.punto_de_llegada_direccion = wh.location
      }
  }
})
watch(() => transferData.value.destination_external_address, (newVal) => {
  // Solo se activa si estamos en modo "Con GRE"
  if (transferType.value === 'con_gre' && newVal) {
      transferData.value.destination_warehouse_id = null
      greData.value.punto_de_llegada_direccion = newVal
      greData.value.punto_de_llegada_ubigeo = "" // Requiere ingreso manual
  }
})

// --- Lógica de Items (MODIFICADA) ---
function addProduct(product) {
  const existingItem = lineItems.value.find(item => item.product_id === product.id)
  if (existingItem) {
    existingItem.quantity = parseFloat(existingItem.quantity) + 1
  } else {
    lineItems.value.push({
      temp_id: crypto.randomUUID(),
      product_id: product.id,
      product_name: product.name,
      product_sku: product.sku,
      um: product.unit_of_measure || 'UND',
      quantity: 1
    })
  }
  productSearchQuery.value = '' // Limpiar búsqueda
}

function removeLineItem(index) {
  lineItems.value.splice(index, 1)
}

// --- Buscar RUC (Req #2) ---
async function handleRucLookup() {
  if (!greData.value.cliente_numero_de_documento || greData.value.cliente_numero_de_documento.length !== 11) {
    error.value = "Por favor, ingresa un RUC válido de 11 dígitos."
    return
  }
  isLookingUpRuc.value = true
  error.value = null
  try {
    const token = await getAccessTokenSilently()
    const ruc = greData.value.cliente_numero_de_documento

    // Llama al endpoint de Flask que creaste
    const response = await fetch(`${FLASK_API_URL}/purchases/lookup-provider/${ruc}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (!response.ok) {
      const errData = await response.json()
      throw new Error(errData.error || 'RUC no encontrado.')
    }
    const rucData = await response.json()

    // Solo llena la Razón Social
    greData.value.cliente_denominacion = rucData.name

  } catch (e) {
    error.value = e.message
    greData.value.cliente_denominacion = ''
  } finally {
    isLookingUpRuc.value = false
  }
}


// --- ¡FUNCIÓN handleFormSubmit ACTUALIZADA! ---
async function handleFormSubmit() {
  isSubmitting.value = true
  error.value = null
  successMessage.value = null

  // --- Validaciones Base ---
  if (!transferData.value.origin_warehouse_id) {
    error.value = "Debes seleccionar un Almacén de Origen."; isSubmitting.value = false; return;
  }
  if (lineItems.value.length === 0) {
    error.value = "Debes agregar al menos un item."; isSubmitting.value = false; return;
  }
  if (lineItems.value.some(item => !item.product_id || item.quantity <= 0)) {
    error.value = "Todos los items deben tener un producto válido y cantidad mayor a 0."; isSubmitting.value = false; return;
  }

  try {
    const token = await getAccessTokenSilently()

    // --- LÓGICA CONDICIONAL: Generar GRE o solo Transferencia ---
    if (transferType.value === 'con_gre') {
      // --- CAMINO 1: Enviar a SUNAT (GRE) ---

      // Validaciones específicas de GRE
      if (!transferData.value.destination_external_address) {
         error.value = "Para 'Con GRE', debe ingresar una Dirección Externa."; isSubmitting.value = false; return;
      }
      if (!greData.value.cliente_numero_de_documento || !greData.value.cliente_denominacion) {
         error.value = "Debe ingresar y validar un RUC de destinatario."; isSubmitting.value = false; return;
      }
      if (greData.value.tipo_de_transporte === '02' && (!greData.value.transportista_placa_numero || !greData.value.conductor_documento_numero || !greData.value.licencia)) {
         error.value = "Para transporte privado, la placa, DNI de conductor y licencia son obligatorios."; isSubmitting.value = false; return;
      }

      // 1. Prepara el payload de la guía
      const gre_payload = {
        ...greData.value,
        // ¡Importante! Usar la dirección externa
        punto_de_llegada_direccion: transferData.value.destination_external_address,

        observaciones: greData.value.motivo_de_traslado === '13'
                       ? greData.value.motivo_otros_descripcion
                       : greData.value.observaciones,
        items: lineItems.value.map(item => ({
          unidad_de_medida: item.um,
          codigo: item.product_sku,
          descripcion: item.product_name,
          cantidad: parseFloat(item.quantity)
        }))
      }

      // 2. Llama al endpoint de Flask para emitir la guía
      const response = await fetch(`${FLASK_API_URL}/gre/enviar`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(gre_payload)
      })

      const resData = await response.json()
      if (!response.ok) throw new Error(resData.error || resData.detail || 'Error al emitir la GRE.')

      // 3. ¡Éxito de SUNAT!
      if (resData.codRespuesta === "0") {
           successMessage.value = `¡Guía Aceptada por SUNAT! Ticket: ${resData.numTicket || resData.ticket}`
           // Aquí también deberías llamar a /api/transfers para registrar el movimiento
           // await registerInternalTransfer(token); // (Función a crear)
      } else {
           throw new Error(`SUNAT Rechazado (Error ${resData.error?.numError}): ${resData.error?.desError}`)
      }

    } else {
      // --- CAMINO 2: Registrar solo Transferencia Interna ---

      // Validación "Sin GRE"
      if (!transferData.value.destination_warehouse_id) {
        error.value = "Debes seleccionar un Almacén Destino (Interno)."; isSubmitting.value = false; return;
      }

      const payload = {
        transfer_data: {
          ...transferData.value,
          items: lineItems.value.map(item => ({
            product_id: item.product_id,
            quantity: parseFloat(item.quantity),
            um: item.um
          }))
        }
      }

      const response = await fetch(`${FLASK_API_URL}/transfers`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      const resData = await response.json()
      if (!response.ok) throw new Error(resData.error || 'Error al crear la transferencia.')

      successMessage.value = "¡Transferencia interna creada exitosamente!"
      // router.push('/inventory/transfers') // Descomenta para redirigir
    }

  } catch (e) {
    error.value = e.message
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div>
    <h1 class="text-3xl font-bold mb-4">
      Crear Transferencia de Stock
    </h1>

    <div v-if="isLoading">Cargando datos...</div>

    <div v-if="error" class="text-red-500 p-4 bg-red-50 rounded-md mb-4">{{ error }}</div>
    <div v-if="successMessage" class="text-green-700 p-4 bg-green-50 rounded-md mb-4">{{ successMessage }}</div>

    <div v-else class="space-y-6">

      <Card>
        <CardHeader><CardTitle>1. Tipo de Transferencia</CardTitle></CardHeader>
        <CardContent>
          <RadioGroup v-model="transferType" class="flex space-x-4">
            <div class="flex items-center space-x-2">
              <RadioGroupItem id="r-sin-gre" value="sin_gre" />
              <Label for="r-sin-gre">Transferencia Interna (Sin GRE)</Label>
            </div>
            <div class="flex items-center space-x-2">
              <RadioGroupItem id="r-con-gre" value="con_gre" />
              <Label for="r-con-gre">Envío a Terceros (Con GRE)</Label>
            </div>
          </RadioGroup>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>2. Origen y Destino</CardTitle></CardHeader>
        <CardContent class="grid grid-cols-2 gap-6">

          <div class="space-y-2">
            <Label for="wh-origin">Almacén Origen (Punto de Partida)</Label>
            <Select v-model="transferData.origin_warehouse_id">
              <SelectTrigger id="wh-origin"><SelectValue placeholder="Selecciona..." /></SelectTrigger>
              <SelectContent><SelectGroup>
                <SelectItem v-for="wh in warehouses" :key="wh.id" :value="wh.id">
                  {{ wh.name }} ({{ wh.location }})
                </SelectItem>
              </SelectGroup></SelectContent>
            </Select>
          </div>

          <div v-if="transferType === 'sin_gre'" class="space-y-2">
            <Label for="wh-dest">Almacén Destino (Interno)</Label>
            <Select v-model="transferData.destination_warehouse_id">
              <SelectTrigger id="wh-dest"><SelectValue placeholder="Selecciona..." /></SelectTrigger>
              <SelectContent><SelectGroup>
                <SelectItem v-for="wh in warehouses" :key="wh.id" :value="wh.id">
                  {{ wh.name }} ({{ wh.location }})
                </SelectItem>
              </SelectGroup></SelectContent>
            </Select>
          </div>
          <div v-if="transferType === 'sin_gre'" class="space-y-2 col-span-2">
             </div>

          <div v-if="transferType === 'con_gre'" class="space-y-2 col-span-2">
            <Label for="dest-ext">Destino Externo (Dirección)</Label>
            <Input
              id="dest-ext"
              v-model="transferData.destination_external_address"
              placeholder="Ej. Av. Principal 123, Miraflores"
            />
          </div>
        </CardContent>
      </Card>

      <div v-if="transferType === 'con_gre'" class="space-y-6">

        <Card>
          <CardHeader><CardTitle>3. Destinatario y Datos de Guía</CardTitle></CardHeader>
          <CardContent class="space-y-6">
            <div>
              <h3 class="font-semibold mb-2">Destinatario</h3>
              <div class="grid grid-cols-3 gap-6">
                <div class="space-y-2">
                  <Label for="gre-cliente-num">RUC Destinatario</Label>
                  <div class="flex gap-2">
                    <Input id="gre-cliente-num" v-model="greData.cliente_numero_de_documento" />
                    <Button variant="outline" size="icon" @click="handleRucLookup" :disabled="isLookingUpRuc">
                      <Loader2 v-if="isLookingUpRuc" class="h-4 w-4 animate-spin" />
                      <Search v-else class="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <div class="space-y-2 col-span-2">
                  <Label for="gre-cliente-nombre">Razón Social (auto)</Label>
                  <Input id="gre-cliente-nombre" v-model="greData.cliente_denominacion" disabled />
                </div>
              </div>
            </div>

            <div class="border-t pt-4">
              <h3 class="font-semibold mb-2">Datos Generales (GRE)</h3>
              <div class="grid grid-cols-3 gap-6">
                <div class="space-y-2">
                  <Label for="gre-serie">Serie</Label>
                  <Input id="gre-serie" v-model="greData.serie" />
                </div>
                <div class="space-y-2">
                  <Label for="gre-numero">Número</Label>
                  <Input id="gre-numero" v-model.number="greData.numero" type="number" />
                </div>
                <div class="space-y-2">
                  <Label for="gre-peso">Peso Bruto (KGM)</Label>
                  <Input id="gre-peso" v-model.number="greData.peso_bruto_total" type="number" step="0.1" />
                </div>
                <div class="space-y-2">
                  <Label for="gre-fecha-emision">Fecha Emisión</Label>
                  <Input id="gre-fecha-emision" v-model="greData.fecha_de_emision" type="date" />
                </div>
                <div class="space-y-2">
                  <Label for="gre-fecha-traslado">Fecha Traslado</Label>
                  <Input id="gre-fecha-traslado" v-model="greData.fecha_de_inicio_de_traslado" type="date" />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>4. Motivo de Traslado</CardTitle></CardHeader>
          <CardContent class="grid grid-cols-2 gap-6">
            <div class="space-y-2">
              <Label for="gre-motivo">Motivo (Cat. 20)</Label>
              <Select v-model="greData.motivo_de_traslado">
                <SelectTrigger id="gre-motivo"><SelectValue /></SelectTrigger>
                <SelectContent><SelectGroup>
                  <SelectItem value="01">Venta</SelectItem>
                  <SelectItem value="02">Compra</SelectItem>
                  <SelectItem value="04">Traslado entre estab. de la misma empresa</SelectItem>
                  <SelectItem value="08">Importación</SelectItem>
                  <SelectItem value="09">Exportación</SelectItem>
                  <SelectItem value="18">Traslado por emisor itinerante</SelectItem>
                  <SelectItem value="13">Otros</SelectItem>
                </SelectGroup></SelectContent>
              </Select>
            </div>
            <div v-if="greData.motivo_de_traslado === '13'" class="space-y-2">
              <Label for="gre-motivo-otros">Descripción (Otros)</Label>
              <Input id="gre-motivo-otros" v-model="greData.motivo_otros_descripcion" placeholder="Escribe el motivo aquí..." />
            </div>
            <div v-else class="space-y-2">
              <Label for="gre-obs">Observaciones (Opcional)</Label>
              <Input id="gre-obs" v-model="greData.observaciones" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>5. Unidad de Transporte y Conductor</CardTitle></CardHeader>
          <CardContent class="space-y-6">
            <div class="space-y-2">
              <Label for="gre-transporte-tipo">Modalidad (Cat. 18)</Label>
              <Select v-model="greData.tipo_de_transporte">
                <SelectTrigger id="gre-transporte-tipo"><SelectValue /></SelectTrigger>
                <SelectContent><SelectGroup>
                  <SelectItem value="02">Transporte Privado</SelectItem>
                  <SelectItem value="01">Transporte Público</SelectItem>
                </SelectGroup></SelectContent>
              </Select>
            </div>

            <div v-if="greData.tipo_de_transporte === '02'" class="grid grid-cols-3 gap-6">
              <div class="space-y-2">
                <Label for="gre-placa">Placa Vehículo (sin guion)</Label>
                <Input id="gre-placa" v-model="greData.transportista_placa_numero" />
              </div>
              <div class="space-y-2">
                <Label for="gre-marca">Marca Vehículo</Label>
                <Input id="gre-marca" v-model="greData.marca_vehiculo" />
              </div>
              <div class="space-y-2">
                <Label for="gre-licencia">Licencia Conducir</Label>
                <Input id="gre-licencia" v-model="greData.licencia" />
              </div>
              <div class="space-y-2">
                  <Label for="gre-cond-tipo">Tipo Doc. Conductor</Label>
                  <Select v-model="greData.conductor_documento_tipo">
                    <SelectTrigger id="gre-cond-tipo"><SelectValue /></SelectTrigger>
                    <SelectContent><SelectGroup>
                      <SelectItem value="1">DNI (1)</SelectItem>
                      <SelectItem value="4">CARNET EXT. (4)</SelectItem>
                      <SelectItem value="7">PASAPORTE (7)</SelectItem>
                    </SelectGroup></SelectContent>
                  </Select>
              </div>
              <div class="space-y-2">
                <Label for="gre-cond-doc">Nro Doc. Conductor</Label>
                <Input id="gre-cond-doc" v-model="greData.conductor_documento_numero" />
              </div>
              <div class="space-y-2" /> <div class="space-y-2">
                <Label for="gre-cond-nombre">Nombres Conductor</Label>
                <Input id="gre-cond-nombre" v-model="greData.conductor_nombre" />
              </div>
              <div class="space-y-2">
                <Label for="gre-cond-ape">Apellidos Conductor</Label>
                <Input id="gre-cond-ape" v-model="greData.conductor_apellidos" />
              </div>
            </div>

            <div v-if="greData.tipo_de_transporte === '01'" class="grid grid-cols-2 gap-6">
              <p>Campos para transporte público (RUC, Razón Social) irían aquí.</p>
            </div>
          </CardContent>
        </Card>
      </div> <Card>
        <CardHeader><CardTitle>{{ transferType === 'con_gre' ? '6.' : '3.' }} Items a Transferir</CardTitle></CardHeader>
        <CardContent class="space-y-4">

          <div class="space-y-2">
            <Label for="product-search">Buscar Producto</Label>
            <Input id="product-search" v-model="productSearchQuery" placeholder="Escribe el nombre o SKU del producto..." />
          </div>

          <div v-if="filteredProductCatalog.length > 0" class="border rounded-md max-h-[200px] overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Producto Encontrado</TableHead>
                  <TableHead>SKU</TableHead>
                  <TableHead class="text-right">Acción</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="product in filteredProductCatalog" :key="product.id">
                  <TableCell class="font-medium">{{ product.name }}</TableCell>
                  <TableCell>{{ product.sku }}</TableCell>
                  <TableCell class="text-right">
                    <Button variant="outline" size="sm" @click="addProduct(product)">
                      <Plus class="h-4 w-4 mr-2" />
                      Agregar
                    </Button>
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>

          <div class="border-t pt-4">
            <h3 class="font-semibold mb-2">Items Agregados</h3>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead class="w-[40%]">Producto</TableHead>
                  <TableHead>UM</TableHead>
                  <TableHead>Cantidad</TableHead>
                  <TableHead>Acción</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-if="lineItems.length === 0">
                  <TableCell colspan="4" class="text-center">Aún no hay productos agregados.</TableCell>
                </TableRow>
                <TableRow v-for="(item, index) in lineItems" :key="item.temp_id">
                  <TableCell class="font-medium">
                    <div>{{ item.product_name }}</div>
                    <div class="text-xs text-muted-foreground">{{ item.product_sku }}</div>
                  </TableCell>
                  <TableCell><Input v-model="item.um" class="w-16" /></TableCell>
                  <TableCell><Input v-model.number="item.quantity" type="number" class="w-20" /></TableCell>
                  <TableCell>
                    <Button variant="outline" size="icon" @click="removeLineItem(index)">
                      <Trash2 class="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
      <div classs="flex justify-end">
        <Button @click="handleFormSubmit" :disabled="isSubmitting" size="lg">
          <Loader2 v-if="isSubmitting" class="h-4 w-4 animate-spin mr-2" />
          {{ transferType === 'con_gre' ? 'Emitir Guía de Remisión' : 'Guardar Transferencia' }}
        </Button>
      </div>
    </div>
  </div>
</template>
