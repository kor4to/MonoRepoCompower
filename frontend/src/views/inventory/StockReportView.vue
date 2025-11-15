<script setup>
import { ref, onMounted, computed, h } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import {
  useVueTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  FlexRender,
} from '@tanstack/vue-table'

// Importar componentes de UI
import { Card } from '@/components/ui/card/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Input } from '@/components/ui/input/index.js'
import { Button } from '@/components/ui/button/index.js'
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger, DropdownMenuItem, DropdownMenuCheckboxItem } from '@/components/ui/dropdown-menu/index.js'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select/index.js'
import { ArrowUpDown, ChevronDown, Printer, Tags } from 'lucide-vue-next'

const { getAccessTokenSilently } = useAuth0()

// --- State ---
const data = ref([])
const warehouses = ref([])
const isLoading = ref(true)
const error = ref(null)
const isGeneratingLabels = ref(false)

// --- Table State ---
const sorting = ref([])
const columnFilters = ref([])
const columnVisibility = ref({})

// --- Column Definitions ---
const columns = [
  {
    accessorKey: 'product_sku',
    header: ({ column }) => h(Button, {
      variant: 'ghost',
      onClick: () => column.toggleSorting(column.getIsSorted() === 'asc'),
    }, () => ['SKU', h(ArrowUpDown, { class: 'ml-2 h-4 w-4' })]),
    label: 'SKU',
  },
  {
    accessorKey: 'product_name',
    header: 'Producto',
    label: 'Producto',
  },
  {
    accessorKey: 'warehouse_name',
    header: 'Almacén',
    label: 'Almacén',
  },
  {
    accessorKey: 'product_location',
    header: 'Ubicación',
    label: 'Ubicación',
  },
  {
    accessorKey: 'category_name',
    header: 'Categoría',
    label: 'Categoría',
    filterFn: (row, columnId, filterValue) => {
      if (!filterValue || filterValue.length === 0) {
        return true
      }
      return filterValue.includes(row.getValue(columnId))
    },
    enableMultiSort: true,
  },
  {
    accessorKey: 'quantity',
    header: ({ column }) => h(Button, {
      variant: 'ghost',
      onClick: () => column.toggleSorting(column.getIsSorted() === 'asc'),
    }, () => ['Cantidad', h(ArrowUpDown, { class: 'ml-2 h-4 w-4' })]),
    cell: ({ row }) => h('div', { class: 'text-center' }, new Intl.NumberFormat('es-ES').format(row.getValue('quantity'))),
    label: 'Cantidad',
  },
  {
    accessorKey: 'unit_price',
    header: ({ column }) => h(Button, {
      variant: 'ghost',
      onClick: () => column.toggleSorting(column.getIsSorted() === 'asc'),
    }, () => ['Costo Unit.', h(ArrowUpDown, { class: 'ml-2 h-4 w-4' })]),
    cell: ({ row }) => h('div', { class: 'text-center font-medium' }, new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(row.getValue('unit_price'))),
    label: 'Costo Unit.',
  },
  {
    accessorKey: 'total_value',
    header: ({ column }) => h(Button, {
      variant: 'ghost',
      onClick: () => column.toggleSorting(column.getIsSorted() === 'asc'),
    }, () => ['Valor Total', h(ArrowUpDown, { class: 'ml-2 h-4 w-4' })]),
    cell: ({ row }) => h('div', { class: 'text-center font-medium' }, new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(row.getValue('total_value'))),
    label: 'Valor Total',
  },
]

// --- Table Instance ---
const table = useVueTable({
  get data() { return data.value },
  columns,
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
  getFilteredRowModel: getFilteredRowModel(),
  state: {
    get sorting() { return sorting.value },
    get columnFilters() { return columnFilters.value },
    get columnVisibility() { return columnVisibility.value },
  },
  onSortingChange: (updaterOrValue) => sorting.value = typeof updaterOrValue === 'function' ? updaterOrValue(sorting.value) : updaterOrValue,
  onColumnFiltersChange: (updaterOrValue) => {
    console.log('onColumnFiltersChange triggered!')
    const newValue = typeof updaterOrValue === 'function' ? updaterOrValue(columnFilters.value) : updaterOrValue
    console.log('New columnFilters value:', newValue)
    columnFilters.value = newValue
  },
  onColumnVisibilityChange: (updaterOrValue) => columnVisibility.value = typeof updaterOrValue === 'function' ? updaterOrValue(columnVisibility.value) : updaterOrValue,
})

// --- Data Fetching ---
onMounted(async () => {
  try {
    const token = await getAccessTokenSilently()
    const [reportRes, whRes] = await Promise.all([
      fetch('https://192.168.1.59:5000/api/inventory/stock-report', { headers: { 'Authorization': `Bearer ${token}` } }),
      fetch('https://192.168.1.59:5000/api/warehouses', { headers: { 'Authorization': `Bearer ${token}` } })
    ])
    if (!reportRes.ok) throw new Error('No se pudo cargar el reporte.')
    if (!whRes.ok) throw new Error('No se pudieron cargar los almacenes.')
    data.value = await reportRes.json()
    warehouses.value = await whRes.json()
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
})

// --- Computed Properties & Handlers ---
const uniqueCategories = computed(() => {
  const categories = table.getCoreRowModel().rows.map(row => row.original.category_name)
  return [...new Set(categories)].filter(Boolean)
})

const categoryFilter = computed(() => {
  return table.getColumn('category_name')?.getFilterValue() || []
})

const totalValue = computed(() => {
  const total = table.getRowModel().rows.reduce((sum, row) => sum + row.original.total_value, 0)
  return new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(total)
})
function handleWarehouseFilterChange(value) {
  const filterValue = value === 'all' ? null : value
  table.getColumn('warehouse_name')?.setFilterValue(filterValue)
}

function handleCategoryFilterChange(category) {
  console.log(`--- Handling Category Click ---`)
  console.log(`Category clicked: ${category}`)

  const column = table.getColumn('category_name')
  if (!column) {
    console.error('Category column not found!')
    return
  }

  const currentFilter = (column.getFilterValue() || [])
  console.log('Current filter array:', currentFilter)
  
  let newFilter

  // If the category is already in the filter, this click should remove it.
  if (currentFilter.includes(category)) {
    newFilter = currentFilter.filter(c => c !== category)
  } 
  // Otherwise, this click should add it.
  else {
    newFilter = [...currentFilter, category]
  }
  console.log('New filter array:', newFilter)

  const filterValueToSet = newFilter.length > 0 ? newFilter : undefined
  console.log('Value being set to filter:', filterValueToSet)

  column.setFilterValue(filterValueToSet)
}

function printReport() {
  window.print()
}

async function generateLabels() {
  isGeneratingLabels.value = true
  try {
    const token = await getAccessTokenSilently()
    const filteredProducts = table.getFilteredRowModel().rows.map(row => row.original)

    if (filteredProducts.length === 0) {
      alert('No hay productos en la tabla para generar etiquetas.')
      return
    }

    const response = await fetch('https://192.168.1.59:5000/api/inventory/generate-labels', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ products: filteredProducts })
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || 'Error al generar el PDF de etiquetas.')
    }

    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    window.open(url, '_blank')
    window.URL.revokeObjectURL(url)

  } catch (e) {
    alert(e.message)
  } finally {
    isGeneratingLabels.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <h1 class="text-3xl font-bold print:hidden">Reportes y Maestro de Stock</h1>

    <!-- Filter & Controls Bar -->
    <div class="flex items-center justify-between print:hidden no-print">
      <div class="flex items-center gap-2">
        <Input
          class="max-w-sm"
          placeholder="Filtrar por nombre de producto..."
          :model-value="table.getColumn('product_name')?.getFilterValue()"
          @update:model-value="table.getColumn('product_name')?.setFilterValue($event)"
        />
        <Input
          class="max-w-sm"
          placeholder="Filtrar por ubicación..."
          :model-value="table.getColumn('product_location')?.getFilterValue()"
          @update:model-value="table.getColumn('product_location')?.setFilterValue($event)"
        />
        
        <Select @update:model-value="handleWarehouseFilterChange">
          <SelectTrigger class="w-[180px]">
            <SelectValue placeholder="Todos los Almacenes" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos los Almacenes</SelectItem>
            <SelectItem v-for="wh in warehouses" :key="wh.id" :value="wh.name">
              {{ wh.name }}
            </SelectItem>
          </SelectContent>
        </Select>

        <DropdownMenu>
          <DropdownMenuTrigger as-child>
            <Button variant="outline" class="ml-auto">
              Categorías <ChevronDown class="ml-2 h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuCheckboxItem
              v-for="category in uniqueCategories"
              :key="category"
              class="capitalize"
              :checked="categoryFilter.includes(category)"
              @click.prevent="handleCategoryFilterChange(category)"
            >
              {{ category }}
            </DropdownMenuCheckboxItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <div class="flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger as-child>
            <Button variant="outline" class="ml-auto">
              Columnas <ChevronDown class="ml-2 h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              v-for="column in table.getAllColumns().filter((column) => column.getCanHide())"
              :key="column.id"
              class="flex items-center space-x-2"
            >
              <input
                type="checkbox"
                :id="`column-toggle-${column.id}`"
                :checked="column.getIsVisible()"
                @change="(e) => column.toggleVisibility(e.target.checked)"
                @click.stop
                class="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
              />
              <label :for="`column-toggle-${column.id}`" class="text-sm cursor-pointer" @click.stop>
                {{ column.columnDef.label }}
              </label>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <Button variant="outline" @click="printReport">
          <Printer class="mr-2 h-4 w-4" />
          Imprimir
        </Button>
        <Button variant="outline" @click="generateLabels" :disabled="isGeneratingLabels">
          <Tags class="mr-2 h-4 w-4" />
          <span v-if="isGeneratingLabels">Generando...</span>
          <span v-else>Generar Etiquetas</span>
        </Button>
      </div>
    </div>

    <!-- Table -->
    <div v-if="isLoading">Cargando reporte...</div>
    <div v-else-if="error" class="text-red-500">{{ error }}</div>
    <Card v-else class="print:text-xs">
      <Table>
        <TableHeader>
          <TableRow v-for="headerGroup in table.getHeaderGroups()" :key="headerGroup.id">
            <TableHead v-for="header in headerGroup.headers" :key="header.id" class="print:p-1">
              <FlexRender
                v-if="!header.isPlaceholder"
                :render="header.column.columnDef.header"
                :props="header.getContext()"
              />
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <template v-if="table.getRowModel().rows?.length">
            <TableRow
              v-for="row in table.getRowModel().rows"
              :key="row.id"
              :data-state="row.getIsSelected() && 'selected'"
            >
              <TableCell v-for="cell in row.getVisibleCells()" :key="cell.id" class="print:p-1">
                <FlexRender :render="cell.column.columnDef.cell" :props="cell.getContext()" />
              </TableCell>
            </TableRow>
          </template>
          <template v-else>
            <TableRow>
              <TableCell :colspan="columns.length" class="h-24 text-center print:p-1">
                No hay resultados.
              </TableCell>
            </TableRow>
          </template>
        </TableBody>
      </Table>
    </Card>

    <!-- Footer Summary -->
    <div class="flex items-center justify-end space-x-2 py-4 print:hidden no-print">
      <div class="flex-1 text-sm text-muted-foreground">
        {{ table.getFilteredRowModel().rows.length }} de {{ data.length }} fila(s) mostradas.
      </div>
      <div class="font-bold text-lg">
        Valor Total Filtrado: {{ totalValue }}
      </div>
    </div>
  </div>
</template>