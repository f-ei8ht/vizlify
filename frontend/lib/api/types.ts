/**
 * Domain types mirroring the FastAPI schemas in `backend/app/schemas`.
 *
 * Money values are serialized by Pydantic as strings (for example "2500.00")
 * so precision survives JSON. Convert with `formatMoney` before display.
 */

export type TonePreference = "friendly" | "formal" | "firm"

export type ProjectStatus = "active" | "completed" | "archived"

export type MilestoneStatus = "todo" | "done" | "billed"

export type Money = string

export interface Account {
  id: string
  email: string
  business_name: string | null
  paypal_email: string | null
}

export interface Client {
  id: string
  name: string
  email: string
  tone_preference: TonePreference
}

export interface ClientCreateInput {
  name: string
  email: string
  tone_preference?: TonePreference
}

export interface ClientUpdateInput {
  name?: string
  email?: string
  tone_preference?: TonePreference
}

export interface Project {
  id: string
  client_id: string
  name: string
  currency: string
  status: ProjectStatus
}

export interface ProjectCreateInput {
  client_id: string
  name: string
  currency: string
  status?: ProjectStatus
}

export interface ProjectUpdateInput {
  name?: string
  currency?: string
  status?: ProjectStatus
}

export interface Milestone {
  id: string
  project_id: string
  title: string
  amount: Money
  due_date: string | null
  status: MilestoneStatus
}

export interface MilestoneCreateInput {
  title: string
  amount: string
  due_date?: string | null
  status?: MilestoneStatus
}

export interface MilestoneUpdateInput {
  title?: string
  amount?: string
  due_date?: string | null
  status?: MilestoneStatus
}

export interface TeamMember {
  id: string
  project_id: string
  name: string
  paypal_email: string
  share_percent: Money
}

export interface TeamMemberCreateInput {
  name: string
  paypal_email: string
  share_percent: string
}

export interface TeamMemberUpdateInput {
  name?: string
  paypal_email?: string
  share_percent?: string
}
