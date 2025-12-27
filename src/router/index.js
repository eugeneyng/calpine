import * as VueRouter from 'vue-router'
import { useUserStore } from '@/stores/UserStore'

const router = VueRouter.createRouter({
  history: VueRouter.createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue')
    },
    {
      path: '/units/:id',
      name: 'unit',
      component: () => import('@/views/UnitView.vue')
    },
    {
      path: '/about',
      name: 'about',
      component: () => import('@/views/AboutView.vue')
    },
    {
      path: '/inventory',
      name: 'inventory',
      component: () => import('@/views/InventoryView.vue')
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/AuthView.vue')
    },
    {
      path: '/people',
      name: 'people',
      component: () => import('@/views/PeopleView.vue')
    },
    {
      path: '/users/:uid',
      name: 'user',
      component: () => import('@/views/UserView.vue')
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue')
    },
    {
      path: '/tasks',
      name: 'tasks',
      component: () => import('@/views/TasksView.vue')
    }
  ]
})

router.beforeEach(async (to) => {
  // Redirect to login page if not logged in and trying to access a restricted page
  const publicPages = ['/about','/login'];
  const authRequired = !publicPages.includes(to.path);
  const userStore = useUserStore()

  if (authRequired && !userStore.isLoggedIn) {
    return '/login';
  }
})

export default router
