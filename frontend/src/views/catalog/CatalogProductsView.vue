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
import { Pencil } from 'lucide-vue-next'

const { getAccessTokenSilently } = useAuth0()
const products = ref([])
const categories = ref([]) // ¡Necesitamos las categorías para el modal!
const isLoading = ref(true)
const error = ref(null)

const isDialogOpen = ref(false)
const modalMode = ref('create')
const formData = ref({ id: null, sku: '', name: '', description: '', um: 'UND', category_id: null })

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
  let url = 'https://192.168.1.59:5000/api/products'
  let method = 'POST'

  if (modalMode.value === 'edit') {
    url = `https://192.168.1.59:5000/api/products/${formData.value.id}`
    method = 'PUT'
  }

  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(url, {
      method: method,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(formData.value)
    })
    if (!response.ok) throw new Error('Error al guardar.')

    isDialogOpen.value = false
    await fetchData() // Recargar productos
  } catch (e) {
    alert(e.message)
  }
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h1 class="text-3xl font-bold">Gestión de Productos</h1>
      <Button @click="openCreateModal">Crear Producto</Button>
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
            <TableHead>Acciones</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="prod in products" :key="prod.id">
            <TableCell class="font-medium">{{ prod.sku }}</TableCell>
            <TableCell>{{ prod.name }}</TableCell>
            <TableCell>{{ prod.category_name }}</TableCell>
            <TableCell>{{ prod.unit_of_measure }}</TableCell>
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
        </div>
        <DialogFooter>
          <Button variant="secondary" @click="isDialogOpen = false">Cancelar</Button>
          <Button @click="handleFormSubmit">Guardar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
