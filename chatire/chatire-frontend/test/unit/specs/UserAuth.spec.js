import Vue from 'vue'
import UserAuth from '@/components/UserAuth.vue'

describe('UserAuth.vue', () => {
  const storedValues = {}

  beforeEach(() => {
    const storage = {
      getItem: key => storedValues[key] || null,
      setItem: (key, value) => {
        storedValues[key] = value
      },
      clear: () => {
        Object.keys(storedValues).forEach(key => delete storedValues[key])
      }
    }
    Object.defineProperty(window, 'sessionStorage', {
      value: storage,
      configurable: true
    })
  })

  afterEach(() => {
    window.sessionStorage.clear()
    delete global.fetch
    delete window.sessionStorage
  })

  it('switches between sign up and sign in tabs', async () => {
    const Constructor = Vue.extend(UserAuth)
    const vm = new Constructor().$mount()

    expect(vm.$el.querySelector('#signup').style.display).not.toBe('none')
    expect(vm.$el.querySelector('#signin').style.display).toBe('none')

    const click = document.createEvent('MouseEvents')
    click.initEvent('click', true, true)
    vm.$el.querySelector('#signin-tab').dispatchEvent(click)
    await Vue.nextTick()

    expect(vm.activeTab).toBe('signin')
    expect(vm.$el.querySelector('#signup').style.display).toBe('none')
    expect(vm.$el.querySelector('#signin').style.display).not.toBe('none')

    vm.$destroy()
  })

  it('registers with credentials and returns to the requested chat', async () => {
    const Constructor = Vue.extend(UserAuth)
    const vm = new Constructor().$mount()
    const push = jest.fn()
    const alert = jest.spyOn(window, 'alert').mockImplementation(() => {})

    vm.email = 'new-user@example.com'
    vm.username = 'new_chat_user'
    vm.password = 'StrongTestPassword123!'
    vm.$router = { push }
    vm.$route = { query: { redirect: '/chats/invite-uri' } }
    global.fetch = jest.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: 1 })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ auth_token: 'test-token' })
      })

    await vm.signUp()

    expect(JSON.parse(global.fetch.mock.calls[0][1].body)).toEqual({
      email: 'new-user@example.com',
      username: 'new_chat_user',
      password: 'StrongTestPassword123!'
    })
    expect(push).toHaveBeenCalledWith('/chats/invite-uri')
    expect(window.sessionStorage.getItem('authToken')).toBe('test-token')

    alert.mockRestore()
    vm.$destroy()
  })
})
