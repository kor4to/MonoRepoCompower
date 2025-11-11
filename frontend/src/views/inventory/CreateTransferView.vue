<script setup>
import { ref, onMounted, watch } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { useRouter } from 'vue-router'
import { Button } from '@/components/ui/button/index.js'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card/index.js'
import { Input } from '@/components/ui/input/index.js'
import { Label } from '@/components/ui/label/index.js'
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Loader2, Plus, Trash2, Check, ChevronsUpDown } from 'lucide-vue-next'
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command/index.js'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover/index.js'

const { getAccessTokenSilently } = useAuth0()
const router = useRouter()

const isLoading = ref(true)
const isSubmitting = ref(false)
const error = ref(null)

const warehouses = ref([])
const productCatalog = ref([])
const lineItems = ref([])

const transferData = ref({
  origin_warehouse_id: null,
  destination_warehouse_id: null,
  destination_external_address: '',
})

// Cargar Almacenes y Productos
onMounted(async () => {
  try {
    const token = await getAccessTokenSilently()
    const whRes = await fetch('https://192.168.1.59:5000/api/warehouses', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    warehouses.value = await whRes.json()

    const prodRes = await fetch('https://192.168.1.59:5000/api/products', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    productCatalog.value = await prodRes.json()

    addNewLineItem()
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
})

// Lógica para deshabilitar campos de destino
watch(() => transferData.value.destination_warehouse_id, (newVal) => {
  if (newVal) transferData.value.destination_external_address = ''
})
watch(() => transferData.value.destination_external_address, (newVal) => {
  if (newVal) transferData.value.destination_warehouse_id = null
})

// --- Lógica de Items ---
function addNewLineItem() {
  lineItems.value.push({
    temp_id: crypto.randomUUID(), product_id: null,
    product_name: 'Selecciona...', product_sku: '', um: 'UND', quantity: 1
  })
}
function removeLineItem(index) {
  lineItems.value.splice(index, 1)
}
function handleProductSelect(item, selectedProductId) {
  const p = productCatalog.value.find(p => p.id === selectedProductId)
  if (p) {
    item.product_id = p.id; item.product_name = p.name;
    item.product_sku = p.sku; item.um = p.unit_of_measure;
  }
}

// --- Guardar Formulario ---
async function handleFormSubmit() {
  isSubmitting.value = true
  error.value = null

  if (!transferData.value.origin_warehouse_id) {
    error.value = "Debes seleccionar un Almacén de Origen."; isSubmitting.value = false; return;
  }
  if (!transferData.value.destination_warehouse_id && !transferData.value.destination_external_address) {
    error.value = "Debes seleccionar un Almacén Destino O una Dirección Externa."; isSubmitting.value = false; return;
  }
  if (lineItems.value.some(item => !item.product_id || item.quantity <= 0)) {
    error.value = "Todos los items deben tener un producto válido y cantidad mayor a 0."; isSubmitting.value = false; return;
  }

  try {
    const token = await getAccessTokenSilently()

    const payload = {
      transfer_data: {
        ...transferData.value,
        items: lineItems.value.map(item => ({
          product_id: item.product_id,
          quantity: item.quantity,
          um: item.um
        }))
      }
      // ¡No hay gre_data!
    }

    const response = await fetch('https://192.168.1.59:5000/api/transfers', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    const resData = await response.json()
    if (!response.ok) throw new Error(resData.error || 'Error al crear la transferencia.')

    alert("¡Transferencia creada exitosamente!")
    router.push('/inventory/transfers')

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
    <div v-else-if="error" class="text-red-500 p-4 bg-red-50 rounded-md mb-4">{{ error }}</div>

    <div v-else class="space-y-6">
      <Card>
        <CardHeader><CardTitle>1. Origen y Destino</CardTitle></CardHeader>
        <CardContent class="grid grid-cols-2 gap-6">
          <div class="space-y-2">
            <Label for="wh-origin">Almacén Origen</Label>
            <Select v-model="transferData.origin_warehouse_id">
              <SelectTrigger id="wh-origin"><SelectValue placeholder="Selecciona..." /></SelectTrigger>
              <SelectContent><SelectGroup>
                <SelectItem v-for="wh in warehouses" :key="wh.id" :value="wh.id">
                  {{ wh.name }} ({{ wh.location }})
                </SelectItem>
              </SelectGroup></SelectContent>
            </Select>
          </div>
          <div class="space-y-2">
            <Label for="wh-dest">Almacén Destino (Interno)</Label>
            <Select v-model="transferData.destination_warehouse_id" :disabled="!!transferData.destination_external_address">
              <SelectTrigger id="wh-dest"><SelectValue placeholder="Selecciona..." /></SelectTrigger>
              <SelectContent><SelectGroup>
                <SelectItem v-for="wh in warehouses" :key="wh.id" :value="wh.id">
                  {{ wh.name }} ({{ wh.location }})
                </SelectItem>
              </SelectGroup></SelectContent>
            </Select>
          </div>
          <div class="space-y-2 col-span-2">
            <Label for="dest-ext">O Destino Externo (Dirección)</Label>
            <Input
              id="dest-ext"
              v-model="transferData.destination_external_address"
              :disabled="!!transferData.destination_warehouse_id"
              placeholder="Ej. Av. Principal 123, Miraflores"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>2. Items a Transferir</CardTitle></CardHeader>
        <CardContent class="space-y-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead class="w-[40%]">Producto (Catálogo)</TableHead>
                <TableHead>UM</TableHead>
                <TableHead>Cant. a Mover</TableHead>
                <TableHead>Acción</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-if="lineItems.length === 0">
                <TableCell colspan="4" class="text-center">Añade productos...</TableCell>
              </TableRow>
              <TableRow v-for="(item, index) in lineItems" :key="item.temp_id">
                <TableCell>
                  <Popover>
                    <PopoverTrigger as-child>
                      <Button variant="outline" role="combobox" class="w-full justify-between">
                        {{ item.product_name }}
                        <ChevronsUpDown class="ml-2 h-4 w-4 shrink-0 opacity-50" />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent class="p-0">
                      <Command>
                        <CommandInput placeholder="Buscar producto..." />
                        <CommandEmpty>No se encontró.</CommandEmpty>
                        <CommandGroup><CommandList>
                          <CommandItem
                            v-for="product in productCatalog"
                            :key="product.id" :value="product.name"
                            @select="() => handleProductSelect(item, product.id)"
                          >
                            <Check :class="['mr-2 h-4 w-4', item.product_id === product.id ? 'opacity-100' : 'opacity-0']" />
                            {{ product.name }} ({{ product.sku }})
                          </CommandItem>
                        </CommandList></CommandGroup>
                      </Command>
                    </PopoverContent>
                  </Popover>
                </TableCell>
                <TableCell><Input v-model="item.um" class="w-16" /></TableCell>
                <TableCell><Input v-model="item.quantity" type="number" class="w-20" /></TableCell>
                <TableCell>
                  <Button variant="outline" size="icon" @click="removeLineItem(index)">
                    <Trash2 class="h-4 w-4" />
                  </Button>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
          <Button variant="outline" @click="addNewLineItem" class="mt-2">
            <Plus class="h-4 w-4 mr-2" />
            Añadir Fila
          </Button>
        </CardContent>
      </Card>

      <div class="flex justify-end">
        <Button @click="handleFormSubmit" :disabled="isSubmitting" size="lg">
          <Loader2 v-if="isSubmitting" class="h-4 w-4 animate-spin mr-2" />
          Guardar Transferencia
        </Button>
      </div>
    </div>
  </div>
</template>
