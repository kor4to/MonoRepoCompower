<script setup>
import { ref, onMounted } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Button } from '@/components/ui/button/index.js'
import { Card } from '@/components/ui/card/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog/index.js'
import { Input } from '@/components/ui/input/index.js'
import { Label } from '@/components/ui/label/index.js'
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select/index.js'
import { Loader2, Pencil, Upload } from 'lucide-vue-next' // <-- AÑADE Upload

const { getAccessTokenSilently } = useAuth0()
const products = ref([])
const categories = ref([]) // ¡Necesitamos las categorías para el modal!
const isLoading = ref(true)
const error = ref(null)

const isDialogOpen = ref(false)
const modalMode = ref('create')
const isSubmitting = ref(false) // <-- ¡AÑADE ESTA LÍNEA!
const formData = ref({ id: null, sku: '', name: '', description: '', unit_of_measure: 'UND', standard_price: 0.00, category_id: null })
// Ref para el input de archivo oculto
const fileInput = ref(null)
const isImporting = ref(false)



// --- Cargar AMBOS, productos y categorías ---
async function fetchData() {
  isLoading.value = true
  error.value = null
  try {
    const token = await getAccessTokenSilently()
    // Cargar Productos
    const prodRes = await fetch('https://192.168.1.59:5000/api/products', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!prodRes.ok) throw new Error('No se pudieron cargar los productos.')
    products.value = await prodRes.json()

    // Cargar Categorías
    const catRes = await fetch('https://192.168.1.59:5000/api/categories', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!catRes.ok) throw new Error('No se pudieron cargar las categorías.')
    categories.value = await catRes.json()

  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
}
onMounted(fetchData)

// --- Lógica de Modales ---
function openCreateModal() {
  modalMode.value = 'create'
  formData.value = { id: null, sku: '', name: '', description: '', um: 'UND', category_id: null }
  isDialogOpen.value = true
}

function openEditModal(product) {
  modalMode.value = 'edit'
  // El 'um' no está en el to_dict(), así que lo asignamos por separado
  const productData = products.value.find(p => p.id === product.id)
  formData.value = { ...productData }
  isDialogOpen.value = true
}

async function handleFormSubmit() {
  isSubmitting.value = true
  let url = 'https://192.168.1.59:5000/api/products'
  let method = 'POST'

  if (modalMode.value === 'edit') {
    url = `https://192.168.1.59:5000/api/products/${formData.value.id}`
    method = 'PUT'
  }

  // --- ¡AQUÍ ESTÁ LA CORRECCIÓN! ---
  // Creamos un payload explícito para asegurarnos de enviar todos los campos,
  // incluyendo el nuevo 'standard_price'.
  const payload = {
    sku: formData.value.sku,
    name: formData.value.name,
    description: formData.value.description,
    um: formData.value.unit_of_measure, // Asegúrate que el backend espera 'um' o 'unit_of_measure'
    standard_price: formData.value.standard_price, // <-- ¡IMPORTANTE!
    category_id: formData.value.category_id
  }
  // --------------------------------

  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(url, {
      method: method,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload) // Enviamos el payload
    })
    if (!response.ok) throw new Error('Error al guardar.')

    isDialogOpen.value = false
    await fetchData()
  } catch (e) {
    alert(e.message)
  } finally {
    isSubmitting.value = false
  }
}

// --- Función para disparar el click en el input oculto ---
function triggerImport() {
  fileInput.value.click()
}

// --- Función para manejar la subida del archivo ---
async function handleFileUpload(event) {
  const file = event.target.files[0]
  if (!file) return

  isImporting.value = true

  const formData = new FormData()
  formData.append('file', file)

  try {
    const token = await getAccessTokenSilently()
    const response = await fetch('https://192.168.1.59:5000/api/products/import', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
        // NOTA: No pongas 'Content-Type': 'application/json' aquí.
        // El navegador lo pondrá automáticamente como 'multipart/form-data'
      },
      body: formData
    })

    const result = await response.json()

    if (!response.ok) throw new Error(result.error || 'Error en la importación')

    alert(`Importación Exitosa:\nCreados: ${result.created}\nActualizados: ${result.updated}`)
    await fetchData() // Recargar la tabla

  } catch (e) {
    alert(e.message)
  } finally {
    isImporting.value = false
    event.target.value = '' // Limpiar el input para poder subir el mismo archivo de nuevo si se quiere
  }
}



</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h1 class="text-3xl font-bold">Gestión de Productos</h1>

      <div class="flex gap-2">
        <input
          type="file"
          ref="fileInput"
          class="hidden"
          accept=".xlsx, .xls"
          @change="handleFileUpload"
        />

        <Button variant="outline" @click="triggerImport" :disabled="isImporting">
          <Loader2 v-if="isImporting" class="h-4 w-4 animate-spin mr-2" />
          <Upload v-else class="h-4 w-4 mr-2" />
          Importar Excel
        </Button>

        <Button @click="openCreateModal">Crear Producto</Button>
      </div>
    </div>

    <div v-if="isLoading">Cargando...</div>
    <div v-else-if="error" class="text-red-500">{{ error }}</div>

    <Card v-else>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>SKU</TableHead>
            <TableHead>Nombre</TableHead>
            <TableHead>Categoría</TableHead>
            <TableHead>UM</TableHead>
            <TableHead class="text-right">Precio Ref.</TableHead>
            <TableHead>Acciones</TableHead>

          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="prod in products" :key="prod.id">
            <TableCell class="font-medium">{{ prod.sku }}</TableCell>
            <TableCell>{{ prod.name }}</TableCell>
            <TableCell>{{ prod.category_name }}</TableCell>
            <TableCell>{{ prod.unit_of_measure }}</TableCell>
            <TableCell class="text-right">
                S/ {{ parseFloat(prod.standard_price).toFixed(2) }}
            </TableCell>
            <TableCell>
              <Button variant="outline" size="icon" @click="openEditModal(prod)">
                <Pencil class="h-4 w-4" />
              </Button>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Card>

    <Dialog :open="isDialogOpen" @update:open="isDialogOpen = $event">
      <DialogContent class="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{{ modalMode === 'create' ? 'Crear' : 'Editar' }} Producto</DialogTitle>
        </DialogHeader>
        <div class="grid gap-4 py-4">
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="sku" class="text-right">SKU</Label>
            <Input id="sku" v-model="formData.sku" class="col-span-3" />
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="name" class="text-right">Nombre</Label>
            <Input id="name" v-model="formData.name" class="col-span-3" />
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="um" class="text-right">UM (Ej. UND, M, KG)</Label>
            <Input id="um" v-model="formData.unit_of_measure" class="col-span-3" />
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="category" class="text-right">Categoría</Label>
            <Select v-model="formData.category_id">
              <SelectTrigger class="col-span-3">
                <SelectValue placeholder="Selecciona una categoría..." />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem v-for="cat in categories" :key="cat.id" :value="cat.id">
                    {{ cat.name }}
                  </SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="price" class="text-right">Precio Ref. (S/)</Label>
            <Input id="price" type="number" step="0.01" v-model="formData.standard_price" class="col-span-3" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="secondary" @click="isDialogOpen = false">Cancelar</Button>
          <Button @click="handleFormSubmit">Guardar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
