
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
      path: '/chats/:uri',
      name: 'ChatSession',
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
  const authToken = window.sessionStorage.getItem('authToken')

  if (!authToken && to.path !== '/auth') {
    next({
      path: '/auth',
      query: { redirect: to.fullPath }
    })
    return
  }

  next()
})

export default router
