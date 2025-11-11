<script setup>
import { ref, onMounted } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Card } from '@/components/ui/card/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Button } from '@/components/ui/button/index.js'
import { Badge } from '@/components/ui/badge/index.js'
import { RouterLink } from 'vue-router'

const { getAccessTokenSilently } = useAuth0()
const transfers = ref([])
const isLoading = ref(true)
const error = ref(null)

onMounted(async () => {
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch('https://192.168.1.59:5000/api/transfers', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error('No se pudieron cargar las transferencias.')
    transfers.value = await response.json()
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h1 class="text-3xl font-bold">
        Movimientos de Stock (Transferencias)
      </h1>
      <Button as-child>
        <RouterLink to="/inventory/transfers/create">
          Crear Transferencia
        </RouterLink>
      </Button>
    </div>

    <div v-if="isLoading">Cargando transferencias...</div>
    <div v-else-if="error" class="text-red-500">{{ error }}</div>

    <Card v-else>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>ID</TableHead>
            <TableHead>Fecha</TableHead>
            <TableHead>Almacén Origen</TableHead>
            <TableHead>Destino</TableHead>
            <TableHead>Estado</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-if="transfers.length === 0">
            <TableCell colspan="5" class="text-center">No se han realizado transferencias.</TableCell>
          </TableRow>
          <TableRow v-for="transfer in transfers" :key="transfer.id">
            <TableCell class="font-medium">{{ transfer.id }}</TableCell>
            <TableCell>{{ new Date(transfer.transfer_date).toLocaleString() }}</TableCell>
            <TableCell>{{ transfer.origin_warehouse }}</TableCell>
            <TableCell>{{ transfer.destination_warehouse || transfer.destination_external }}</TableCell>
            <TableCell>
              <Badge>{{ transfer.status }}</Badge>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Card>
  </div>
</template>
