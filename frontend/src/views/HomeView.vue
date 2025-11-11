<script setup>
import { ref, onMounted } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'

const { getAccessTokenSilently } = useAuth0()
const isLoading = ref(true)
const error = ref(null)
const data = ref(null)

onMounted(async () => {
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch('https://192.168.1.59:5000/api/home-data', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) {
      throw new Error('No se pudo cargar el contenido')
    }
    data.value = await response.json()
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
      Novedades
    </h1>

    <div v-if="isLoading">Cargando...</div>
    <div v-else-if="error" class="text-red-500">{{ error }}</div>

    <Card v-else>
      <CardHeader>
        <CardTitle>{{ data.title }}</CardTitle>
      </CardHeader>
      <CardContent>
        <p>{{ data.content }}</p>
      </CardContent>
    </Card>
  </div>
</template>
