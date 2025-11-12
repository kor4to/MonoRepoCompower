<script setup>
import { ref, onMounted } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Loader2, Upload, FileSpreadsheet } from 'lucide-vue-next'

const { getAccessTokenSilently } = useAuth0()
const warehouses = ref([])
const selectedWarehouse = ref(null)
const fileInput = ref(null)
const isSubmitting = ref(false)

// Cargar Almacenes
onMounted(async () => {
  const token = await getAccessTokenSilently()
  const res = await fetch('https://192.168.1.59:5000/api/warehouses', {
    headers: { 'Authorization': `Bearer ${token}` }
  })
  warehouses.value = await res.json()
})

async function handleFileUpload(event) {
  const file = event.target.files[0]
  if (!file || !selectedWarehouse.value) {
    alert("Selecciona un almacén y un archivo.")
    return
  }

  isSubmitting.value = true
  const formData = new FormData()
  formData.append('file', file)
  formData.append('warehouse_id', selectedWarehouse.value)

  try {
    const token = await getAccessTokenSilently()
    const response = await fetch('https://192.168.1.59:5000/api/inventory/adjust-mass', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    })

    const result = await response.json()
    if (!response.ok) throw new Error(result.error || 'Error')

    alert(`¡Éxito!\nProductos ajustados: ${result.updated_products}\nErrores: ${result.errors.length}`)

  } catch (e) {
    alert(e.message)
  } finally {
    isSubmitting.value = false
    event.target.value = '' // Limpiar input
  }
}
</script>

<template>
  <div>
    <h1 class="text-3xl font-bold mb-6">Carga Masiva de Inventario (Inicial)</h1>

    <Card class="max-w-xl">
      <CardHeader>
        <CardTitle>Subir Saldos Iniciales</CardTitle>
      </CardHeader>
      <CardContent class="space-y-6">

        <div class="space-y-2">
          <Label>1. Selecciona el Almacén donde se contó</Label>
          <Select v-model="selectedWarehouse">
            <SelectTrigger>
              <SelectValue placeholder="Selecciona un almacén..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="wh in warehouses" :key="wh.id" :value="wh.id.toString()">
                {{ wh.name }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="space-y-2">
          <Label>2. Sube el Excel (Columnas: SKU, Cantidad)</Label>
          <div class="border-2 border-dashed rounded-lg p-10 flex flex-col items-center justify-center text-center hover:bg-gray-50 transition cursor-pointer" @click="fileInput.click()">
            <FileSpreadsheet class="h-10 w-10 text-green-600 mb-2" />
            <p class="text-sm text-gray-600" v-if="!isSubmitting">
              Clic para seleccionar archivo .xlsx
            </p>
            <div v-else class="flex items-center text-blue-600">
              <Loader2 class="h-4 w-4 animate-spin mr-2" /> Procesando...
            </div>
          </div>
          <input type="file" ref="fileInput" class="hidden" accept=".xlsx" @change="handleFileUpload" :disabled="!selectedWarehouse || isSubmitting" />
        </div>

        <div class="bg-blue-50 p-4 rounded text-sm text-blue-800">
          <strong>Nota:</strong> Este proceso actualizará el stock actual a la cantidad que indiques en el Excel. Se creará un registro en el Kardex como "Carga Inicial / Ajuste".
        </div>

      </CardContent>
    </Card>
  </div>
</template>
