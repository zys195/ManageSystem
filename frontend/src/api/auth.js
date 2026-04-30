import http from './http'

export function loginApi(data) {
  return http.post('/auth/login', data)
}

export function meApi() {
  return http.get('/auth/me')
}

export function changePasswordApi(data) {
  return http.post('/auth/change-password', data)
}
