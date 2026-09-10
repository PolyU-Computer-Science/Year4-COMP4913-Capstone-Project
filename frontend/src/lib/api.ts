import axios from 'axios'

import type {
  AIConfig,
  AIConfigIn,
  Case,
  EmailItem,
  MailAccount,
  MailAccountIn,
  StagesSettings,
  Stats,
  TestResult,
} from '@/lib/types'

const client = axios.create({ baseURL: '/api' })

interface EmailsResponse {
  emails: EmailItem[]
  count: number
}

interface SyncResponse {
  synced: number
  emails: EmailItem[]
  count: number
}

interface CasesResponse {
  cases: Case[]
  count: number
}

interface ProcessResponse {
  case: Case
}

export async function fetchEmails(): Promise<EmailItem[]> {
  const { data } = await client.get<EmailsResponse>('/emails')
  return data.emails
}

export async function syncEmails(): Promise<{
  synced: number
  emails: EmailItem[]
}> {
  const { data } = await client.post<SyncResponse>('/emails/sync')
  return { synced: data.synced, emails: data.emails }
}

export async function processEmail(id: string): Promise<Case> {
  const { data } = await client.post<ProcessResponse>(`/emails/${id}/process`)
  return data.case
}

export async function processAllEmails(): Promise<{
  queued: number
  processed: number
  failed: string[]
}> {
  const { data } = await client.post<{
    queued: number
    processed: number
    failed: string[]
  }>('/emails/process-all')
  return data
}

export async function fetchCases(): Promise<Case[]> {
  const { data } = await client.get<CasesResponse>('/cases')
  return data.cases
}

export async function updateCaseDraft(id: string, draft: string): Promise<Case> {
  const { data } = await client.patch<Case>(`/cases/${id}`, { draft })
  return data
}

export async function sendCase(id: string): Promise<Case> {
  const { data } = await client.post<Case>(`/cases/${id}/send`)
  return data
}

export async function fetchStats(): Promise<Stats> {
  const { data } = await client.get<Stats>('/stats')
  return data
}

export async function fetchAIConfigs(): Promise<AIConfig[]> {
  const { data } = await client.get<AIConfig[]>('/settings/ai')
  return data
}

export async function createAIConfig(payload: AIConfigIn): Promise<AIConfig> {
  const { data } = await client.post<AIConfig>('/settings/ai', payload)
  return data
}

export async function updateAIConfig(
  id: number,
  payload: AIConfigIn,
): Promise<AIConfig> {
  const { data } = await client.put<AIConfig>(`/settings/ai/${id}`, payload)
  return data
}

export async function deleteAIConfig(id: number): Promise<void> {
  await client.delete(`/settings/ai/${id}`)
}

export async function activateAIConfig(id: number): Promise<AIConfig> {
  const { data } = await client.post<AIConfig>(`/settings/ai/${id}/activate`)
  return data
}

export async function testAIConfig(payload: AIConfigIn): Promise<TestResult> {
  const { data } = await client.post<TestResult>('/settings/ai/test', payload)
  return data
}

export async function testSavedAIConfig(id: number): Promise<TestResult> {
  const { data } = await client.post<TestResult>(`/settings/ai/${id}/test`)
  return data
}

export async function fetchStages(): Promise<StagesSettings> {
  const { data } = await client.get<StagesSettings>('/settings/stages')
  return data
}

export async function saveStages(
  payload: StagesSettings,
): Promise<StagesSettings> {
  const { data } = await client.put<StagesSettings>('/settings/stages', payload)
  return data
}

export async function fetchMailAccounts(): Promise<MailAccount[]> {
  const { data } = await client.get<MailAccount[]>('/settings/mail')
  return data
}

export async function createMailAccount(
  payload: MailAccountIn,
): Promise<MailAccount> {
  const { data } = await client.post<MailAccount>('/settings/mail', payload)
  return data
}

export async function updateMailAccount(
  id: number,
  payload: MailAccountIn,
): Promise<MailAccount> {
  const { data } = await client.put<MailAccount>(`/settings/mail/${id}`, payload)
  return data
}

export async function deleteMailAccount(id: number): Promise<void> {
  await client.delete(`/settings/mail/${id}`)
}
