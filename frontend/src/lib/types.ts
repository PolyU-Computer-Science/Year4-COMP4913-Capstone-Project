export interface EmailItem {
  id: string
  sender: string
  subject: string
  body: string
  timestamp: string
  html: string
  status: string
}

export interface Classification {
  category: string
  topic: string
  priority: string
  urgency_score: number
  summary: string
  custom: Record<string, unknown>
}

export interface Case {
  id: string
  email: EmailItem
  classification: Classification
  draft: string
  created_at: string
  sent_at: string | null
}

export interface CategoryDatum {
  name: string
  value: number
}

export interface RecentActivity {
  email: string
  topic: string
  category: string
  priority: string
  status: string
  time: string
}

export interface Stats {
  total_emails: number
  processed: number
  pending: number
  success_rate: number
  category_distribution: CategoryDatum[]
  recent_activity: RecentActivity[]
}

export interface AIConfig {
  id: number
  name: string
  provider: string
  model: string
  base_url: string
  api_key: string
  has_api_key: boolean
  timeout: number
  max_tokens: number
  temperature: number
  enabled: boolean
}

export interface AIConfigIn {
  name: string
  provider: string
  model: string
  base_url: string
  api_key: string
  timeout: number
  max_tokens: number
  temperature: number
  enabled: boolean
}

export interface StageConfig {
  role: string
  goal: string
  backstory: string
  prompt: string
  max_tokens: number | null
  temperature: number | null
}

export interface StagesSettings {
  classification: StageConfig
  draft: StageConfig
}

export interface TestResult {
  ok: boolean
  message: string
}

export interface MailAccount {
  id: number
  address: string
  imap_host: string
  imap_port: number
  smtp_host: string
  smtp_port: number
  password: string
  has_password: boolean
  folder: string
  max_emails: number
  enabled: boolean
}

export interface MailAccountIn {
  address: string
  imap_host: string
  imap_port: number
  smtp_host: string
  smtp_port: number
  password: string
  folder: string
  max_emails: number
  enabled: boolean
}
