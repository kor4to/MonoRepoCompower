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
const categories = ref([])
const isLoading = ref(true)
const error = ref(null)

const isDialogOpen = ref(false)
const modalMode = ref('create')
const formData = ref({ id: null, name: '', description: '', parent_id: null })

async function fetchCategories() {
  isLoading.value = true
  error.value = null
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch('https://192.168.1.59:5000/api/categories', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error('No se pudieron cargar las categorías.')
    categories.value = await response.json()
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
}
onMounted(fetchCategories)

function openCreateModal() {
  modalMode.value = 'create'
  formData.value = { id: null, name: '', description: '', parent_id: null }
  isDialogOpen.value = true
}

function openEditModal(category) {
  modalMode.value = 'edit'
  formData.value = { ...category }
  isDialogOpen.value = true
}

async function handleFormSubmit() {
  let url = 'https://192.168.1.59:5000/api/categories'
  let method = 'POST'

  if (modalMode.value === 'edit') {
    url = `https://192.168.1.59:5000/api/categories/${formData.value.id}`
    method = 'PUT'
  }

  // Asegurarse de que parent_id sea null si está vacío, no 0 o ""
  const payload = { ...formData.value }
  if (!payload.parent_id) {
    payload.parent_id = null
  }

  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(url, {
      method: method,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })
    if (!response.ok) throw new Error('Error al guardar.')

    isDialogOpen.value = false
    await fetchCategories()
  } catch (e) {
    alert(e.message)
  }
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h1 class="text-3xl font-bold">Gestión de Categorías</h1>
      <Button @click="openCreateModal">Crear Categoría</Button>
    </div>

    <div v-if="isLoading">Cargando...</div>
    <div v-else-if="error" class="text-red-500">{{ error }}</div>

    <Card v-else>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Nombre</TableHead>
            <TableHead>Categoría Padre (Subcategoría de)</TableHead>
            <TableHead>Acciones</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="cat in categories" :key="cat.id">
            <TableCell class="font-medium">{{ cat.name }}</TableCell>
            <TableCell>{{ cat.parent_name || '---' }}</TableCell>
            <TableCell>
              <Button variant="outline" size="icon" @click="openEditModal(cat)">
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
          <DialogTitle>{{ modalMode === 'create' ? 'Crear' : 'Editar' }} Categoría</DialogTitle>
        </DialogHeader>
        <div class="grid gap-4 py-4">
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="name" class="text-right">Nombre</Label>
            <Input id="name" v-model="formData.name" class="col-span-3" />
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="description" class="text-right">Descripción</Label>
            <Input id="description" v-model="formData.description" class="col-span-3" />
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="parent" class="text-right">Categoría Padre</Label>
            <Select v-model="formData.parent_id">
              <SelectTrigger class="col-span-3">
                <SelectValue placeholder="Selecciona (si es subcategoría)..." />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem :value="null">Ninguna (Categoría Principal)</SelectItem>
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
