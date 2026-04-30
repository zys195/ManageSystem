import http from './http'

export function getUsers() {
  return http.get('/meta/users')
}

export function getDepartments() {
  return http.get('/meta/departments')
}

export function getCompanies() {
  return http.get('/meta/companies')
}

export function createCompany(data) {
  return http.post('/meta/companies', data)
}
