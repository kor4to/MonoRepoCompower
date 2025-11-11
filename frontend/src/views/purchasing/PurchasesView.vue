<script setup>
import { ref, onMounted } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Button } from '@/components/ui/button/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger, DialogClose } from '@/components/ui/dialog/index.js'
import { Input } from '@/components/ui/input/index.js'
import { Label } from '@/components/ui/label/index.js'
import { Badge } from '@/components/ui/badge/index.js'
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select/index.js'
import { Loader2, Plus, Trash2 } from 'lucide-vue-next'
import { Card } from '@/components/ui/card/index.js' // <-- ¡IMPORTANTE! Asegúrate de que Card esté instalado
import { RouterLink } from 'vue-router' // <-- ¡IMPORTANTE! Faltaba esta importación

const { getAccessTokenSilently } = useAuth0()

// --- Refs de la Tabla Principal ---
const orders = ref([])
const isLoadingTable = ref(true)
const tableError = ref(null)

// --- Refs del Modal Principal ---
const isDialogOpen = ref(false)
const isSubmitting = ref(false)
const isLookingUpRuc = ref(false)
const formError = ref(null)

// --- Refs de Catálogos ---
const catalogs = ref({
  document_types: [],
  statuses: [],
  cost_centers: [],
})

// --- Refs del Formulario ---
const lineItems = ref([])
const initialFormData = {
  ruc: '',
  provider_id: null,
  provider_name: '',
  document_type_id: null,
  document_number: '',
  status_id: null,
  cost_center_id: null,
}
const formData = ref({ ...initialFormData })

// Helper de moneda
const currencyFormatter = new Intl.NumberFormat('es-PE', {
  style: 'currency',
  currency: 'PEN',
})

// --- 1. Cargar la Tabla de Órdenes ---
async function fetchOrders() {
  isLoadingTable.value = true
  tableError.value = null
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch('https://192.168.1.59:5000/api/purchases', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (response.status === 403) throw new Error('No tienes permiso para ver las órdenes.')
    if (!response.ok) throw new Error('No se pudieron cargar las órdenes.')
    orders.value = await response.json()
  } catch (e) {
    tableError.value = e.message
  } finally {
    isLoadingTable.value = false
  }
}

// --- 2. Cargar los Catálogos ---
async function fetchCatalogs() {
  if (catalogs.value.document_types.length > 0) return
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch('https://192.168.1.59:5000/api/purchases/catalogs', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error('No se pudieron cargar los catálogos.')
    const data = await response.json()
    catalogs.value = data

    const defaultStatus = data.statuses.find(s => s.name === 'Borrador')
    if (defaultStatus) {
        initialFormData.status_id = defaultStatus.id
        formData.value.status_id = defaultStatus.id
    }
  } catch (e) {
    formError.value = e.message
  }
}


// --- 3. Abrir el Modal de Creación ---
async function openCreateModal() {
  formData.value = { ...initialFormData }
  lineItems.value = []
  addNewLineItem() // Añade una fila en blanco
  formError.value = null
  isDialogOpen.value = true
  await fetchCatalogs()

  const defaultStatus = catalogs.value.statuses.find(s => s.name === 'Aprobada')
  if (defaultStatus) formData.value.status_id = defaultStatus.id
}

// --- 4. Buscar RUC ---
async function handleRucLookup() {
  if (!formData.value.ruc || formData.value.ruc.length !== 11) {
    formError.value = "Por favor, ingresa un RUC válido de 11 dígitos."
    return
  }
  isLookingUpRuc.value = true
  formError.value = null
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`https://192.168.1.59:5000/api/purchases/lookup-provider/${formData.value.ruc}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) {
      const errData = await response.json()
      throw new Error(errData.error || 'RUC no encontrado.')
    }
    const providerData = await response.json()
    formData.value.provider_id = providerData.id
    formData.value.provider_name = providerData.name
  } catch (e) {
    formError.value = e.message
    formData.value.provider_id = null
    formData.value.provider_name = ''
  } finally {
    isLookingUpRuc.value = false
  }
}

// --- 5. Guardar el Formulario ---
async function handleFormSubmit() {
  isSubmitting.value = true
  formError.value = null

  // Validación
  if (!formData.value.provider_id || !formData.value.document_type_id || !formData.value.status_id || !formData.value.cost_center_id) {
    formError.value = "Completa todos los campos (RUC, Tipo, Estado, Centro de Costo)."
    isSubmitting.value = false
    return
  }

  for (const item of lineItems.value) {
    if (!item.invoice_detail_text || item.invoice_detail_text.trim() === '') {
      formError.value = "Todos los items deben tener un 'Detalle (Factura)'."
      isSubmitting.value = false
      return;
    }
  }

  try {
    const token = await getAccessTokenSilently()
    const payload = {
      ...formData.value,
      items: lineItems.value.map(item => ({
        invoice_detail_text: item.invoice_detail_text,
        quantity: item.quantity,
        unit_price: item.unit_price,
        um: item.um
      }))
    }

    const response = await fetch('https://192.168.1.59:5000/api/purchases', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    if (!response.ok) {
      if (response.status === 403) throw new Error('No tienes permiso para crear órdenes.')
      throw new Error('Error al guardar la orden.')
    }

    isDialogOpen.value = false
    await fetchOrders()

  } catch (e) {
    formError.value = e.message
  } finally {
    isSubmitting.value = false
  }
}

// --- 6. Funciones de Items de Línea ---
function addNewLineItem() {
  lineItems.value.push({
    temp_id: crypto.randomUUID(),
    invoice_detail_text: '',
    um: 'UND',
    quantity: 1,
    unit_price: 0.00
  })
}
function removeLineItem(index) {
  lineItems.value.splice(index, 1)
}

onMounted(fetchOrders)
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h1 class="text-3xl font-bold">
        Órdenes de Compra
      </h1>
      <Button @click="openCreateModal">Ingresar Orden de Compra</Button>
    </div>

    <div v-if="isLoadingTable">Cargando órdenes...</div>
    <div v-else-if="tableError" class="text-red-500">{{ tableError }}</div>

    <Card v-else>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Nro. Documento</TableHead>
            <TableHead>Proveedor</TableHead>
            <TableHead>Centro de Costo</TableHead>
            <TableHead>Monto Total</TableHead>
            <TableHead>Estado</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-if="orders.length === 0">
            <TableCell colspan="5" class="text-center">No hay órdenes de compra.</TableCell>
          </TableRow>
          <TableRow v-for="order in orders" :key="order.id">
            <TableCell class="font-medium">
              <RouterLink :to="`/purchases/${order.id}`" class="text-blue-600 hover:underline">
                {{ order.document_number }}
              </RouterLink>
            </TableCell>
            <TableCell>{{ order.provider }}</TableCell>
            <TableCell>{{ order.cost_center }}</TableCell>
            <TableCell>{{ currencyFormatter.format(order.total_amount) }}</TableCell>
            <TableCell>
              <Badge :variant="order.status === 'Borrador' ? 'secondary' : 'default'">
                {{ order.status }}
              </Badge>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Card>

    <Dialog :open="isDialogOpen" @update:open="isDialogOpen = $event">
      <DialogContent class="sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>Ingresar Orden de Compra</DialogTitle>
          <DialogDescription>
            Busca el RUC, asigna un centro de costo y añade los detalles de la factura.
          </DialogDescription>
        </DialogHeader>

        <div v-if="formError" class="text-red-500 text-sm p-2 bg-red-50 rounded-md">
          {{ formError }}
        </div>

        <div class="grid grid-cols-2 gap-6 py-4">
          <div class="space-y-4">
            <div class="grid grid-cols-4 items-center gap-4">
              <Label for="ruc" class="text-right">RUC</Label>
              <Input id="ruc" v-model="formData.ruc" class="col-span-2" @keyup.enter="handleRucLookup" />
              <Button @click="handleRucLookup" :disabled="isLookingUpRuc" class="col-span-1">
                <Loader2 v-if="isLookingUpRuc" class="h-4 w-4 animate-spin" />
                <span v-else>Buscar</span>
              </Button>
            </div>
            <div v-if="formData.provider_name" class="grid grid-cols-4 items-center gap-4">
              <span class="text-right text-sm">Proveedor:</span>
              <span class="col-span-3 font-semibold text-green-600">{{ formData.provider_name }}</span>
            </div>
            <div class="grid grid-cols-4 items-center gap-4">
              <Label for="doc-type" class="text-right">Tipo Doc.</Label>
              <Select v-model="formData.document_type_id">
                <SelectTrigger class="col-span-3">
                  <SelectValue placeholder="Selecciona un tipo..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem v-for="docType in catalogs.document_types" :key="docType.id" :value="docType.id">
                      {{ docType.name }}
                    </SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div class="space-y-4">
            <div class="grid grid-cols-4 items-center gap-4">
              <Label for="doc-num" class="text-right">Nro. Documento</Label>
              <Input id="doc-num" v-model="formData.document_number" class="col-span-3" />
            </div>
            <div class="grid grid-cols-4 items-center gap-4">
              <Label for="status" class="text-right">Estado</Label>
              <Select v-model="formData.status_id">
                <SelectTrigger class="col-span-3">
                  <SelectValue placeholder="Selecciona un estado..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem v-for="status in catalogs.statuses" :key="status.id" :value="status.id">
                      {{ status.name }}
                    </SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            <div class="grid grid-cols-4 items-center gap-4">
              <Label for="cost-center" class="text-right">Centro de Costo</Label>
              <Select v-model="formData.cost_center_id">
                <SelectTrigger class="col-span-3">
                  <SelectValue placeholder="Asigna un centro de costo..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem v-for="cc in catalogs.cost_centers" :key="cc.id" :value="cc.id">
                      {{ cc.name }} ({{ cc.code }})
                    </SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        <div class="space-y-4">
          <h4 class="font-semibold">Detalles de la Compra (Factura)</h4>
          <div class="max-h-[300px] overflow-y-auto pr-2 space-y-3">
            <div class="flex items-center gap-2 text-sm font-medium text-gray-600 px-1">
              <span class="flex-1">Detalle (Factura)</span>
              <span class="w-16">UM</span>
              <span class="w-20">Cant.</span>
              <span class="w-24">P. Unit.</span>
              <span class="w-10"></span>
            </div>
            <div v-for="(item, index) in lineItems" :key="item.temp_id" class="flex items-center gap-2">
              <Input v-model="item.invoice_detail_text" placeholder="Ej. Cable THW Marca X" class="flex-1" />
              <Input v-model="item.um" placeholder="UM" class="w-16" />
              <Input v-model="item.quantity" type="number" placeholder="Cant." class="w-20"/>
              <Input v-model="item.unit_price" type="number" placeholder="P. Unit." class="w-24" />
              <Button variant="outline" size="icon" @click="removeLineItem(index)">
                <Trash2 class="h-4 w-4" />
              </Button>
            </div>
          </div>
          <Button variant="outline" @click="addNewLineItem" class="mt-2">
            <Plus class="h-4 w-4 mr-2" />
            Añadir Fila
          </Button>
        </div>

        <DialogFooter class="pt-4">
          <Button variant="secondary" @click="isDialogOpen = false">Cancelar</Button>
          <Button @click="handleFormSubmit" :disabled="isSubmitting">
            <Loader2 v-if="isSubmitting" class="h-4 w-4 animate-spin mr-2" />
            Guardar Orden
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

  </div>
</template>
