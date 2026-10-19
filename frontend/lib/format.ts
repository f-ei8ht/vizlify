import type { TonePreference } from "@/lib/api/types"

export const TONE_OPTIONS: TonePreference[] = ["friendly", "formal", "firm"]

export const TONE_LABELS: Record<TonePreference, string> = {
  friendly: "Friendly",
  formal: "Formal",
  firm: "Firm",
}

export function formatMoney(amount: string | number, currency = "USD"): string {
  const value = typeof amount === "number" ? amount : Number(amount)
  if (Number.isNaN(value)) return String(amount)

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(value)
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "No date"

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(date)
}

export function formatTime(timestamp: number): string {
  if (!timestamp) return ""

  return new Intl.DateTimeFormat("en-US", { timeStyle: "medium" }).format(
    new Date(timestamp),
  )
}

export function formatRelativeTime(timestamp: number): string {
  if (!timestamp) return ""

  const seconds = Math.max(0, Math.round((Date.now() - timestamp) / 1000))
  if (seconds < 5) return "just now"
  if (seconds < 60) return `${seconds}s ago`

  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`

  const hours = Math.round(minutes / 60)
  return `${hours}h ago`
}
