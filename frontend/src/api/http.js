import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 20000,
})

const pendingGetRequests = new Map()

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (location.pathname !== '/login') {
        location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

function stableStringify(value) {
  if (!value || typeof value !== 'object') return ''
  return JSON.stringify(Object.keys(value).sort().reduce((result, key) => {
    result[key] = value[key]
    return result
  }, {}))
}

const originalGet = http.get.bind(http)
http.get = (url, config = {}) => {
  if (config.responseType === 'blob') {
    return originalGet(url, config)
  }

  const key = `${url}?${stableStringify(config.params)}`
  if (pendingGetRequests.has(key)) {
    return pendingGetRequests.get(key)
  }

  const request = originalGet(url, config).finally(() => {
    pendingGetRequests.delete(key)
  })
  pendingGetRequests.set(key, request)
  return request
}

export default http
