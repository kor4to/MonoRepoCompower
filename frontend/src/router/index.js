import { createRouter, createWebHistory } from 'vue-router'

// --- ¡RUTAS DE IMPORTACIÓN ACTUALIZADAS! ---
import HomeView from '@/views/HomeView.vue'
import Modulo1 from '@/views/modules/Modulo1.vue'
import Modulo2 from '@/views/modules/Modulo2.vue'
import Modulo3 from '@/views/modules/Modulo3.vue'

import AdminPanel from '@/views/admin/AdminPanel.vue'

import CostCentersView from '@/views/cost_centers/CostCentersView.vue'

import PurchasesView from '@/views/purchasing/PurchasesView.vue'
import PurchaseDetailView from '@/views/purchasing/PurchaseDetailView.vue'

import CatalogCategoriesView from '@/views/catalog/CatalogCategoriesView.vue'
import CatalogProductsView from '@/views/catalog/CatalogProductsView.vue'

import InventoryView from '@/views/inventory/InventoryView.vue'
import InventoryReceiveView from '@/views/inventory/InventoryReceiveView.vue'
import StockReportView from '@/views/inventory/StockReportView.vue'
import StockTransferView from '@/views/inventory/StockTransferView.vue'
import CreateTransferView from '@/views/inventory/CreateTransferView.vue'
import WarehouseView from '@/views/inventory/WarehouseView.vue'


const routes = [
  {
    path: '/',
    name: 'Home',
    component: HomeView,
    meta: { title: 'Novedades' }
  },
  // Módulos
  {
    path: '/modulo1',
    name: 'Modulo1',
    component: Modulo1,
    meta: { title: 'Módulo 1' }
  },
  {
    path: '/modulo2',
    name: 'Modulo2',
    component: Modulo2,
    meta: { title: 'Módulo 2' }
  },
  {
    path: '/modulo3',
    name: 'Modulo3',
    component: Modulo3,
    meta: { title: 'Módulo 3' }
  },
  // Admin
  {
    path: '/admin',
    name: 'Admin',
    component: AdminPanel,
    meta: { title: 'Admin Panel' }
  },
  // Centros de Costos
  {
    path: '/cost-centers',
    name: 'CostCenters',
    component: CostCentersView,
    meta: { title: 'Centros de Costos' }
  },
  // Compras
  {
    path: '/purchases',
    name: 'Purchases',
    component: PurchasesView,
    meta: { title: 'Módulo de Compras' }
  },
  {
    path: '/purchases/:id',
    name: 'PurchaseDetail',
    component: PurchaseDetailView,
    meta: { title: 'Detalle de Compra' }
  },
  // Catálogo
  {
    path: '/catalog/categories',
    name: 'Categories',
    component: CatalogCategoriesView,
    meta: { title: 'Gestión de Categorías' }
  },
  {
    path: '/catalog/products',
    name: 'Products',
    component: CatalogProductsView,
    meta: { title: 'Gestión de Productos' }
  },
  // Inventario
  {
    path: '/inventory/warehouses',
    name: 'Warehouses',
    component: WarehouseView,
    meta: { title: 'Gestión de Almacenes' }
  },
  {
    path: '/inventory',
    name: 'Inventory',
    component: InventoryView,
    meta: { title: 'Recepción de Inventario' }
  },
  {
    path: '/inventory/receive/:id',
    name: 'InventoryReceive',
    component: InventoryReceiveView,
    meta: { title: 'Recepcionar Orden' }
  },
  {
    path: '/inventory/stock-report',
    name: 'StockReport',
    component: StockReportView,
    meta: { title: 'Reporte de Stock' }
  },
  {
    path: '/inventory/transfers',
    name: 'StockTransfers',
    component: StockTransferView,
    meta: { title: 'Movimientos de Stock' }
  },
  {
    path: '/inventory/transfers/create',
    name: 'CreateStockTransfer',
    component: CreateTransferView,
    meta: { title: 'Crear Transferencia' }
  }
]

// ... (el resto de tu archivo router, createRouter, etc. no cambia)
const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
