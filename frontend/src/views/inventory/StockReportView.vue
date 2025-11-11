<script setup>
import { ref, onMounted } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Card } from '@/components/ui/card/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'

const { getAccessTokenSilently } = useAuth0()
const stockReport = ref([])
const isLoading = ref(true)
const error = ref(null)

onMounted(async () => {
  try {
    const token = await getAccessTokenSilently()
    // Asegúrate de que esta URL apunte a tu IP de backend
    const response = await fetch('https://192.168.1.59:5000/api/inventory/stock-report', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error('No se pudo cargar el reporte de stock.')
    stockReport.value = await response.json()
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <div>
    <h1 class="text-3xl font-bold mb-4">
      Reporte de Stock Actual
    </h1>
    <p class="text-gray-600 mb-4">Esta es la cantidad actual de items en cada almacén.</p>

    <div v-if="isLoading">Cargando reporte...</div>
    <div v-else-if="error" class="text-red-500">{{ error }}</div>

    <Card v-else>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Almacén</TableHead>
            <TableHead>SKU</TableHead>
            <TableHead>Producto</TableHead>
            <TableHead class="text-right">Cantidad en Stock</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-if="stockReport.length === 0">
            <TableCell colspan="4" class="text-center">No hay stock de ningún producto.</TableCell>
          </TableRow>
          <TableRow v-for="(item, index) in stockReport" :key="index">
            <TableCell class="font-medium">{{ item.warehouse_name }}</TableCell>
            <TableCell>{{ item.product_sku }}</TableCell>
            <TableCell>{{ item.product_name }}</TableCell>
            <TableCell class="text-right font-bold">{{ item.quantity }}</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Card>
  </div>
</template>
