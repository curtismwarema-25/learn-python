<template>
  <div class="container">
    <div class="row">
      <div class="col-sm-6 offset-3">

        <div v-if="sessionStarted || $route.params.uri" id="chat-container" class="card">
          <div class="card-header text-white text-center font-weight-bold subtle-blue-gradient">
            Share the page URL to invite new friends
          </div>

          <div class="card-body">
            <div class="container chat-body">
              <p v-if="errorMessage" class="alert alert-danger">{{ errorMessage }}</p>
              <p v-if="websocketError" class="alert alert-warning">{{ websocketError }}</p>
              <p v-if="loading && messages.length === 0" class="text-center">Loading messages...</p>

              <div
                v-for="(message, index) in messages"
                :key="message.id || index"
                class="row chat-section"
              >
                <template v-if="message.user.username === username">
                  <div class="col-sm-7 offset-3">
                    <p class="card-text speech-bubble speech-bubble-user float-right text-white subtle-blue-gradient">
                      {{ message.message }}
                    </p>
                  </div>
                  <div class="col-sm-2">
                    <img class="rounded-circle" src="http://placehold.it/40/333333/fff&text=A" />
                  </div>
                </template>
                <template v-else>
                  <div class="col-sm-2">
                    <img class="rounded-circle" src="http://placehold.it/40/f16000/fff&text=D" />
                  </div>
                  <div class="col-sm-7">
                    <p class="card-text speech-bubble speech-bubble-peer">
                      {{ message.message }}
                    </p>
                  </div>
                </template>
              </div>
            </div>
          </div>

          <div class="card-footer text-muted">
            <form @submit.prevent="sendMessage">
              <div class="row">
                <div class="col-sm-10">
                  <input
                    v-model="messageDraft"
                    type="text"
                    placeholder="Type a message"
                    required
                  />
                </div>
                <div class="col-sm-2">
                  <button class="btn btn-primary" type="submit" :disabled="sendingMessage">
                    Send
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>

        <div v-else>
          <h3 class="text-center">Welcome !</h3>

          <br />

          <p class="text-center">
            To start chatting with friends click on the button below, it'll start a new chat session
            and then you can invite your friends over to chat!
          </p>

          <br />

          <button @click="startChatSession" class="btn btn-primary btn-lg btn-block">Start Chatting</button>
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
      sessionStarted: false,
      username: window.sessionStorage.getItem('username'),
      messages: [],
      messageDraft: '',
      loading: false,
      sendingMessage: false,
      errorMessage: '',
      websocketError: '',
      websocket: null
    }
  },

  created () {
    if (this.$route.params.uri) {
      this.loadMessages()
    }
  },

  beforeDestroy () {
    this.disconnectWebSocket()
  },

  watch: {
    '$route.params.uri' (uri) {
      if (uri) {
        this.loadMessages()
      } else {
        this.disconnectWebSocket()
        this.sessionStarted = false
        this.messages = []
        this.errorMessage = ''
        this.websocketError = ''
      }
    }
  },

  methods: {
    async startChatSession () {
      const token = window.sessionStorage.getItem('authToken')

      if (!token) {
        this.$router.push('/auth')
        return
      }

      try {
        const response = await fetch(`${API_BASE_URL}/api/chats/`, {
          method: 'POST',
          headers: {
            Authorization: `Token ${token}`,
            'Content-Type': 'application/json'
          }
        })

        const result = await response.json()

        if (!response.ok) {
          throw new Error(JSON.stringify(result))
        }

        this.$router.push({
          name: 'ChatSession',
          params: { uri: result.uri }
        })
      } catch (error) {
        console.error('Could not start chat session:', error)
        alert('Unable to start a chat session: ' + error.message)
      }
    },

    async loadMessages () {
      const token = window.sessionStorage.getItem('authToken')
      const uri = this.$route.params.uri

      if (!token || !uri) {
        return
      }

      this.disconnectWebSocket()
      this.loading = true
      this.errorMessage = ''
      this.websocketError = ''

      try {
        const response = await fetch(
          `${API_BASE_URL}/api/chats/${encodeURIComponent(uri)}/join/`,
          {
            method: 'POST',
            headers: { Authorization: `Token ${token}` }
          }
        )
        const joinResult = await response.json()

        if (!response.ok) {
          throw new Error(JSON.stringify(joinResult))
        }

        const messagesResponse = await fetch(
          `${API_BASE_URL}/api/chats/${encodeURIComponent(uri)}/messages/`,
          { headers: { Authorization: `Token ${token}` } }
        )
        const result = await messagesResponse.json()

        if (!messagesResponse.ok) {
          throw new Error(JSON.stringify(result))
        }

        this.messages = result.messages
        this.sessionStarted = true
        this.connectWebSocket(uri, token)
      } catch (error) {
        this.errorMessage = error.message
      } finally {
        this.loading = false
      }
    },

    async sendMessage () {
      const token = window.sessionStorage.getItem('authToken')
      const uri = this.$route.params.uri
      const message = this.messageDraft.trim()

      if (!token || !uri || !message || this.sendingMessage) {
        return
      }

      this.sendingMessage = true
      this.errorMessage = ''

      try {
        const response = await fetch(
          `${API_BASE_URL}/api/chats/${encodeURIComponent(uri)}/messages/`,
          {
            method: 'POST',
            headers: {
              Authorization: `Token ${token}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message })
          }
        )
        const result = await response.json()

        if (!response.ok) {
          throw new Error(JSON.stringify(result))
        }

        this.addMessage({
          user: result.user,
          id: result.id,
          message: result.message
        })
        this.messageDraft = ''
      } catch (error) {
        this.errorMessage = error.message
      } finally {
        this.sendingMessage = false
      }
    },

    connectWebSocket (uri, token) {
      const apiUrl = new URL(API_BASE_URL)
      const protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'
      const socketUrl = `${protocol}//${apiUrl.host}/ws/chats/${encodeURIComponent(uri)}/?token=${encodeURIComponent(token)}`
      const websocket = new WebSocket(socketUrl)

      this.websocket = websocket
      websocket.onopen = () => {
        this.websocketError = ''
      }
      websocket.onmessage = (event) => {
        let message

        try {
          message = JSON.parse(event.data)
        } catch (error) {
          console.error('Could not parse chat WebSocket message:', error)
          this.websocketError = 'Received an invalid real-time message.'
          return
        }

        this.addMessage(message)
      }
      websocket.onerror = () => {
        this.websocketError = 'Real-time updates are unavailable.'
      }
      websocket.onclose = () => {
        if (this.websocket === websocket) {
          this.websocket = null
        }
      }
    },

    disconnectWebSocket () {
      if (this.websocket) {
        this.websocket.close()
        this.websocket = null
      }
    },

    addMessage (message) {
      if (!this.messages.some(existing => existing.id === message.id)) {
        this.messages.push(message)
      }
    }
  }
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
h1,
h2 {
  font-weight: normal;
}
ul {
  list-style-type: none;
  padding: 0;
}
li {
  display: inline-block;
  margin: 0 10px;
}

.btn {
  border-radius: 0 !important;
}

.card-footer input[type="text"] {
  background-color: #ffffff;
  color: #444444;
  padding: 7px;
  font-size: 13px;
  border: 2px solid #cccccc;
  width: 100%;
  height: 38px;
}

.card-header a {
  text-decoration: underline;
}

.card-body {
  background-color: #ddd;
}

.chat-body {
  margin-top: -15px;
  margin-bottom: -5px;
  height: 380px;
  overflow-y: auto;
}

.speech-bubble {
  display: inline-block;
  position: relative;
  border-radius: 0.4em;
  padding: 10px;
  background-color: #fff;
  font-size: 14px;
}

.subtle-blue-gradient {
  background: linear-gradient(45deg,#004bff, #007bff);
}

.speech-bubble-user:after {
  content: "";
  position: absolute;
  right: 4px;
  top: 10px;
  width: 0;
  height: 0;
  border: 20px solid transparent;
  border-left-color: #007bff;
  border-right: 0;
  border-top: 0;
  margin-top: -10px;
  margin-right: -20px;
}

.speech-bubble-peer:after {
  content: "";
  position: absolute;
  left: 3px;
  top: 10px;
  width: 0;
  height: 0;
  border: 20px solid transparent;
  border-right-color: #ffffff;
  border-top: 0;
  border-left: 0;
  margin-top: -10px;
  margin-left: -20px;
}

.chat-section:first-child {
  margin-top: 10px;
}

.chat-section {
  margin-top: 15px;
}

.send-section {
  margin-bottom: -20px;
  padding-bottom: 10px;
}
</style>
