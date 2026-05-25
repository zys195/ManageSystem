import http from './http'

export function getDashboardSummary() {
  return http.get('/dashboard/summary')
}

export function getContracts(params) {
  return http.get('/contracts', { params })
}

export function getContract(id) {
  return http.get(`/contracts/${id}`)
}

export function createContract(data) {
  return http.post('/contracts', data)
}

export function updateContract(id, data) {
  return http.put(`/contracts/${id}`, data)
}

export function deleteContract(id) {
  return http.delete(`/contracts/${id}`)
}

export function addInvoice(contractId, data) {
  return http.post(`/contracts/${contractId}/invoices`, data)
}

export function addReceipt(contractId, data) {
  return http.post(`/contracts/${contractId}/receipts`, data)
}

export function addPayment(contractId, data) {
  return http.post(`/contracts/${contractId}/payments`, data)
}

export function addAcceptance(contractId, data) {
  return http.post(`/contracts/${contractId}/acceptances`, data)
}

export function uploadFile(contractId, formData) {
  return http.post(`/contracts/${contractId}/files`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function downloadContractFile(fileId) {
  return http.get(`/files/${fileId}/download`, { responseType: 'blob' })
}

export function deleteContractFile(fileId) {
  return http.delete(`/files/${fileId}`)
}

export function importContractsFromExcel(formData) {
  return http.post('/contracts/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function downloadImportTemplate() {
  return http.get('/contracts/import/template', { responseType: 'blob' })
}

export function exportContracts(params) {
  return http.get('/contracts/export', { params, responseType: 'blob' })
}

export function getInvoices(params) {
  return http.get('/invoices', { params })
}

export function createInvoice(data) {
  return http.post('/invoices', data)
}

export function uploadInvoiceImages(formData) {
  return http.post('/invoices/ocr-upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function deleteInvoice(id) {
  return http.delete(`/invoices/${id}`)
}

export function exportInvoices(params) {
  return http.get('/invoices/export', { params, responseType: 'blob' })
}

// ========== 审批流程 API ==========

export function submitApproval(contractId, data) {
  return http.post(`/contracts/${contractId}/approval/submit`, data)
}

export function approveContract(contractId, data) {
  return http.post(`/contracts/${contractId}/approval/approve`, data)
}

export function rejectContract(contractId, data) {
  return http.post(`/contracts/${contractId}/approval/reject`, data)
}

export function resubmitApproval(contractId, data) {
  return http.post(`/contracts/${contractId}/approval/resubmit`, data)
}

export function getApprovalHistory(contractId) {
  return http.get(`/contracts/${contractId}/approval/history`)
}
