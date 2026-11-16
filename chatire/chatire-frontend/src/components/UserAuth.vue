
<template>
  <div class="container">
    <h1 class="text-center">Welcome to Chatire!</h1>

    <div id="auth-container" class="row">
      <div class="col-sm-4 offset-sm-4">
        <ul class="nav nav-tabs nav-justified" id="myTab" role="tablist">
          <li class="nav-item">
            <a
              class="nav-link"
              :class="{ active: activeTab === 'signup' }"
              id="signup-tab"
              href="#signup"
              role="tab"
              aria-controls="signup"
              :aria-selected="activeTab === 'signup'"
              @click.prevent="activeTab = 'signup'"
            >
              Sign Up
            </a>
          </li>
          <li class="nav-item">
            <a
              class="nav-link"
              :class="{ active: activeTab === 'signin' }"
              id="signin-tab"
              href="#signin"
              role="tab"
              aria-controls="signin"
              :aria-selected="activeTab === 'signin'"
              @click.prevent="activeTab = 'signin'"
            >
              Sign In
            </a>
          </li>
        </ul>

        <div class="tab-content" id="myTabContent">
          <div
            class="tab-pane"
            :class="{ active: activeTab === 'signup' }"
            id="signup"
            role="tabpanel"
            aria-labelledby="signup-tab"
            v-show="activeTab === 'signup'"
          >
            <form @submit.prevent="signUp">
              <div class="form-group">
                <input
                  v-model="email"
                  type="email"
                  class="form-control"
                  id="signup-email"
                  placeholder="Email Address"
                  required
                >
              </div>

              <div class="form-row">
                <div class="form-group col-md-6">
                  <input
                    v-model="username"
                    type="text"
                    class="form-control"
                    id="signup-username"
                    placeholder="Username"
                    required
                  >
                </div>

                <div class="form-group col-md-6">
                  <input
                    v-model="password"
                    type="password"
                    class="form-control"
                    id="signup-password"
                    placeholder="Password"
                    required
                  >
                </div>
              </div>

              <div class="form-group">
                <div class="form-check">
                  <input
                    class="form-check-input"
                    type="checkbox"
                    id="toc"
                    required
                  >
                  <label class="form-check-label" for="toc">
                    Accept terms and Conditions
                  </label>
                </div>
              </div>

              <button type="submit" class="btn btn-block btn-primary">
                Sign up
              </button>
            </form>
          </div>

          <div
            class="tab-pane"
            :class="{ active: activeTab === 'signin' }"
            id="signin"
            role="tabpanel"
            aria-labelledby="signin-tab"
            v-show="activeTab === 'signin'"
          >
            <form @submit.prevent="signIn">
              <div class="form-group">
                <input
                  v-model="username"
                  type="text"
                  class="form-control"
                  id="signin-username"
                  placeholder="Username"
                  required
                >
              </div>

              <div class="form-group">
                <input
                  v-model="password"
                  type="password"
                  class="form-control"
                  id="signin-password"
                  placeholder="Password"
                  required
                >
              </div>

              <button type="submit" class="btn btn-block btn-primary">
                Sign in
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import API_BASE_URL from '@/api'

export default {
  data () {
    return {
      activeTab: 'signup',
      email: '',
      username: '',
      password: ''
    }
  },

  methods: {
    async signUp () {
      try {
        const response = await fetch(`${API_BASE_URL}/auth/users/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            email: this.email,
            username: this.username,
            password: this.password
          })
        })

        const result = await response.json()

        if (!response.ok) {
          throw new Error(JSON.stringify(result))
        }

        alert('Your account has been created. You will now be signed in.')
        await this.signIn()
      } catch (error) {
        alert('Registration failed: ' + error.message)
      }
    },

    async signIn () {
      try {
        const credentials = {
          username: this.username,
          password: this.password
        }

        const response = await fetch(`${API_BASE_URL}/auth/token/login/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(credentials)
        })

        const result = await response.json()

        if (!response.ok) {
          throw new Error(JSON.stringify(result))
        }

        window.sessionStorage.setItem('authToken', result.auth_token)
        window.sessionStorage.setItem('username', this.username)

        const redirect = this.$route && this.$route.query
          ? this.$route.query.redirect
          : null
        this.$router.push(
          typeof redirect === 'string' &&
            redirect.startsWith('/') &&
            redirect !== '/auth'
            ? redirect
            : '/'
        )
      } catch (error) {
        alert('Sign in failed: ' + error.message)
      }
    }
  }
}
</script>

<style scoped>
#auth-container {
  margin-top: 50px;
}

.tab-content {
  padding-top: 20px;
}
</style>
