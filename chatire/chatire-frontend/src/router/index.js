
import Vue from 'vue'
import Router from 'vue-router'

import Chat from '@/components/chat.vue'
import UserAuth from '@/components/UserAuth.vue'

Vue.use(Router)

const router = new Router({
  routes: [
    {
      path: '/',
      name: 'Chat',
      component: Chat
    },
    {
      path: '/auth',
      name: 'UserAuth',
      component: UserAuth
    }
  ]
})

router.beforeEach((to, from, next) => {
  const authToken = sessionStorage.getItem('authToken')

  if (authToken !== null || to.path === '/auth') {
    next()
  } else {
    next('/auth')
  }
})

export default router
