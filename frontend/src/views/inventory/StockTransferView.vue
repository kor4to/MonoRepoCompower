<script setup>
import { ref, onMounted } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Card } from '@/components/ui/card/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Button } from '@/components/ui/button/index.js'
import { Badge } from '@/components/ui/badge/index.js'
import { RouterLink } from 'vue-router'
import { Eye } from 'lucide-vue-next'
// --- CAMBIO: Importar el nuevo componente Kardex y la lógica de pestañas ---
import KardexView from './KardexView.vue'

const activeTab = ref('transferencias')
// --------------------------------------------------------------------

const { getAccessTokenSilently } = useAuth0()
const transfers = ref([])
const isLoading = ref(true)
const error = ref(null)

async function fetchTransfers() {
  // No se recarga el loading en cada fetch, solo la primera vez
  error.value = null
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
}

onMounted(fetchTransfers)

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  const options = { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }
  return new Date(dateString).toLocaleString('es-ES', options)
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex justify-between items-center mb-4">
      <h1 class="text-3xl font-bold">
        Transferencias y Kardex
      </h1>
      <!-- El botón de crear solo aparece en la pestaña de transferencias -->
      <Button as-child v-if="activeTab === 'transferencias'">
        <RouterLink to="/inventory/transfers/create">
          Crear Transferencia
        </RouterLink>
      </Button>
    </div>

    <!-- CAMBIO: Menú de Pestañas -->
    <div class="flex space-x-2 border-b">
      <Button :variant="activeTab === 'transferencias' ? 'secondary' : 'ghost'" @click="activeTab = 'transferencias'">
        Transferencias
      </Button>
      <Button :variant="activeTab === 'kardex' ? 'secondary' : 'ghost'" @click="activeTab = 'kardex'">
        Kardex
      </Button>
    </div>

    <!-- CAMBIO: Contenido de las Pestañas -->
    <div>
      <!-- Pestaña 1: Transferencias (Contenido Original) -->
      <div v-if="activeTab === 'transferencias'">
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
                <TableHead>Documento</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead class="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-if="transfers.length === 0">
                <TableCell colspan="7" class="text-center">No se han realizado transferencias.</TableCell>
              </TableRow>
              <TableRow v-for="transfer in transfers" :key="transfer.id">
                <TableCell class="font-medium">{{ transfer.id }}</TableCell>
                <TableCell>{{ formatDate(transfer.transfer_date) }}</TableCell>
                <TableCell>{{ transfer.origin_warehouse }}</TableCell>
                <TableCell>
                  {{ transfer.destination_warehouse !== 'N/A' ? transfer.destination_warehouse : transfer.destination_external }}
                </TableCell>
                <TableCell>
                  <span v-if="transfer.gre_series">{{ transfer.gre_series }}-{{ transfer.gre_number }}</span>
                  <span v-else>-</span>
                </TableCell>
                <TableCell>
                  <Badge :variant="transfer.status === 'Completada (GRE)' ? 'default' : 'secondary'">
                    {{ transfer.status }}
                  </Badge>
                </TableCell>
                <TableCell class="text-right">
                  <Button as-child variant="outline" size="icon">
                    <RouterLink :to="`/inventory/transfers/${transfer.id}`">
                      <Eye class="h-4 w-4" />
                    </RouterLink>
                  </Button>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </Card>
      </div>

      <!-- Pestaña 2: Kardex -->
      <div v-if="activeTab === 'kardex'">
        <KardexView />
      </div>
    </div>
  </div>
</template>
