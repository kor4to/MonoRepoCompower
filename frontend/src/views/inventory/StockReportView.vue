<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Search, FilterX, Printer } from 'lucide-vue-next'

const { getAccessTokenSilently } = useAuth0()

// --- Datos ---
const stockReport = ref([])
const warehouses = ref([])
const categories = ref([]) // Lista de categorías para el filtro
const isLoading = ref(true)
const error = ref(null)

// --- Filtros ---
const searchQuery = ref('')
const selectedWarehouse = ref('all') // ID del almacén o 'all'
const selectedCategory = ref('all')  // Nombre de la categoría o 'all'

const currencyFormatter = new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' })

// --- 1. Cargar Almacenes y Categorías (Solo una vez) ---
async function fetchFilters() {
  try {
    const token = await getAccessTokenSilently()
    const headers = { 'Authorization': `Bearer ${token}` }

    const whRes = await fetch('https://192.168.1.59:5000/api/warehouses', { headers })
    if (whRes.ok) warehouses.value = await whRes.json()

    const catRes = await fetch('https://192.168.1.59:5000/api/categories', { headers })
    if (catRes.ok) categories.value = await catRes.json()
  } catch (e) {
    console.error("Error cargando filtros:", e)
  }
}

// --- 2. Cargar Reporte (Se llama al iniciar y al cambiar almacén) ---
async function fetchReport() {
  isLoading.value = true
  error.value = null
  try {
    const token = await getAccessTokenSilently()

    // Construimos la URL con el parámetro de almacén si es necesario
    let url = 'https://192.168.1.59:5000/api/inventory/stock-report'
    if (selectedWarehouse.value !== 'all') {
      url += `?warehouse_id=${selectedWarehouse.value}`
    }

    const response = await fetch(url, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (!response.ok) throw new Error('Error cargando reporte de stock')
    stockReport.value = await response.json()

  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
}

// --- HELPER: Encontrar todos los IDs de una familia (Padre + Hijos) ---
function getCategoryFamilyIds(parentId, allCategories) {
  // 1. Empezamos con el ID del padre seleccionado
  const familyIds = new Set([parentId])

  // 2. Función recursiva para buscar hijos
  function findChildren(currentId) {
    const children = allCategories.filter(c => c.parent_id === currentId)
    children.forEach(child => {
      familyIds.add(child.id)
      findChildren(child.id) // Buscar nietos...
    })
  }

  findChildren(parentId)
  return familyIds
}

// --- 3. Filtrado Local (ACTUALIZADO) ---
const filteredStock = computed(() => {
  return stockReport.value.filter(item => {
    // Filtro de Texto
    const searchLower = searchQuery.value.toLowerCase()
    const matchesSearch =
      item.product_name.toLowerCase().includes(searchLower) ||
      item.product_sku.toLowerCase().includes(searchLower)

    // Filtro de Categoría (¡Lógica Inteligente!)
    let matchesCategory = true
    if (selectedCategory.value !== 'all') {
      // Buscamos el objeto de la categoría seleccionada
      const selectedCatObj = categories.value.find(c => c.name === selectedCategory.value)

      if (selectedCatObj) {
        // Obtenemos todos los IDs de la familia (padre e hijos)
        const familyIds = getCategoryFamilyIds(selectedCatObj.id, categories.value)
        // Verificamos si el producto pertenece a alguno de esos IDs
        matchesCategory = familyIds.has(item.category_id)
      }
    }

    return matchesSearch && matchesCategory
  })
})

// --- Watchers ---
// Cuando cambia el almacén, recargamos los datos del servidor
watch(selectedWarehouse, () => {
  fetchReport()
})

function clearFilters() {
  searchQuery.value = ''
  selectedWarehouse.value = 'all'
  selectedCategory.value = 'all'
}

function printReport() { window.print() }

function getStockStatus(quantity) {
  if (quantity <= 0) return { label: 'Sin Stock', variant: 'destructive' }
  if (quantity < 10) return { label: 'Bajo', variant: 'warning' }
  return { label: 'Normal', variant: 'secondary' }
}

onMounted(() => {
  fetchFilters()
  fetchReport()
})
</script>

<template>
  <div class="space-y-6">

    <div class="flex flex-col md:flex-row justify-between items-center gap-4 no-print">
      <div>
        <h1 class="text-3xl font-bold tracking-tight">Inventario Actual</h1>
        <p class="text-muted-foreground">Vista consolidada y valorizada del stock.</p>
      </div>
      <Button variant="outline" @click="printReport">
        <Printer class="mr-2 h-4 w-4" /> Imprimir Reporte
      </Button>
    </div>

    <Card class="no-print">
      <CardContent class="p-4 flex flex-col md:flex-row items-center justify-center gap-4">

        <div class="w-full md:w-[200px]">
          <Select v-model="selectedCategory">
            <SelectTrigger>
              <SelectValue placeholder="Todas las Categorías" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas las Categorías</SelectItem>

              <SelectItem v-for="cat in categories" :key="cat.id" :value="cat.name">
                <span v-if="cat.parent_id" class="pl-2 text-gray-500">↳ </span>
                {{ cat.name }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="relative w-full md:w-[400px]">
          <Search class="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Buscar por nombre o SKU..."
            v-model="searchQuery"
            class="pl-8"
          />
        </div>

        <div class="w-full md:w-[200px]">
          <Select v-model="selectedWarehouse">
            <SelectTrigger>
              <SelectValue placeholder="Todos los Almacenes" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los Almacenes</SelectItem>
              <SelectItem v-for="wh in warehouses" :key="wh.id" :value="wh.id.toString()">
                {{ wh.name }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Button variant="ghost" size="icon" @click="clearFilters" title="Limpiar Filtros">
          <FilterX class="h-4 w-4" />
        </Button>

      </CardContent>
    </Card>

    <div v-if="isLoading" class="text-center py-10">Cargando inventario...</div>
    <div v-else-if="error" class="text-red-500 p-4 bg-red-50 rounded">{{ error }}</div>

    <Card v-else>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>SKU</TableHead>
            <TableHead>Producto</TableHead>
            <TableHead>Categoría</TableHead> <TableHead class="text-right">Precio Unit.</TableHead>
            <TableHead class="text-right">Cantidad</TableHead>
            <TableHead class="text-right">Valor Total</TableHead>
            <TableHead class="text-center">Estado</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-if="filteredStock.length === 0">
            <TableCell colspan="7" class="text-center h-24 text-muted-foreground">
              No se encontraron productos.
            </TableCell>
          </TableRow>

          <TableRow v-for="(item, index) in filteredStock" :key="index">
            <TableCell class="font-mono text-sm">{{ item.product_sku }}</TableCell>
            <TableCell class="font-medium">{{ item.product_name }}</TableCell>
            <TableCell>
              <Badge variant="outline">{{ item.category_name }}</Badge> </TableCell>

            <TableCell class="text-right text-gray-500">
              {{ currencyFormatter.format(item.unit_price) }}
            </TableCell>

            <TableCell class="text-right font-bold" :class="{'text-red-600': item.quantity <= 0}">
              {{ item.quantity }}
            </TableCell>

            <TableCell class="text-right font-bold text-green-700">
              {{ currencyFormatter.format(item.total_value) }}
            </TableCell>

            <TableCell class="text-center">
              <Badge :variant="getStockStatus(item.quantity).variant">
                {{ getStockStatus(item.quantity).label }}
              </Badge>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Card>
  </div>
</template>

<style>
@media print {
  .no-print { display: none !important; }
  body { background: white; }
  .card { border: none; box-shadow: none; }
}
</style>
