import http from './http'

export function getBackupInfo() {
  return http.get('/system/backup/info')
}

export function downloadBackup() {
  return http.get('/system/backup/export', {
    responseType: 'blob',
    timeout: 120000,
  })
}

export function restoreBackup(formData) {
  return http.post('/system/backup/restore', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}
