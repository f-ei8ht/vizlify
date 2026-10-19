/**
 * The single HTTP entry point for the Vizlify API.
 *
 * The backend wraps every response in `{ data, error }`; HTTP status is the
 * source of truth. This client unwraps `data`, turns `error` into a typed
 * `ApiError`, and attaches the Clerk session token when one is available.
 */

export interface ApiValidationDetail {
  field?: string
  message?: string
  type?: string
}

export interface ApiErrorBody {
  code: string
  message: string
  details?: ApiValidationDetail[] | null
}

export interface ApiEnvelope<T> {
  data: T | null
  error: ApiErrorBody | null
}

const FALLBACK_BASE_URL = "http://localhost:8000"

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: ApiValidationDetail[]

  constructor({
    status,
    code,
    message,
    details,
  }: {
    status: number
    code: string
    message: string
    details?: ApiValidationDetail[] | null
  }) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.code = code
    this.details = details ?? []
  }

  /** The request never reached the API (backend down, DNS, offline). */
  get isNetwork(): boolean {
    return this.status === 0
  }

  get isUnauthorized(): boolean {
    return this.status === 401 || this.status === 403
  }

  get isValidation(): boolean {
    return this.status === 422
  }

  /** Pydantic validation details flattened to `field -> message`. */
  get fieldErrors(): Record<string, string> {
    return this.details.reduce<Record<string, string>>((errors, detail) => {
      if (detail.field && detail.message) {
        errors[detail.field] = detail.message
      }
      return errors
    }, {})
  }
}

export type TokenGetter = () => Promise<string | null>

export interface ApiClientOptions {
  baseUrl?: string
  getToken?: TokenGetter
}

export type ApiClient = ReturnType<typeof createApiClient>

function resolveBaseUrl(baseUrl?: string): string {
  const configured = baseUrl ?? process.env.NEXT_PUBLIC_API_URL ?? FALLBACK_BASE_URL
  return configured.replace(/\/+$/, "")
}

async function readEnvelope(response: Response): Promise<ApiEnvelope<unknown> | null> {
  if (response.status === 204) return null

  const text = await response.text()
  if (!text) return null

  try {
    return JSON.parse(text) as ApiEnvelope<unknown>
  } catch {
    return null
  }
}

export function createApiClient({ baseUrl, getToken }: ApiClientOptions = {}) {
  const root = resolveBaseUrl(baseUrl)

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers)
    headers.set("Accept", "application/json")
    if (init.body !== undefined) {
      headers.set("Content-Type", "application/json")
    }

    if (getToken) {
      const token = await getToken().catch(() => null)
      if (token) headers.set("Authorization", `Bearer ${token}`)
    }

    let response: Response
    try {
      response = await fetch(`${root}${path}`, { ...init, headers })
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === "AbortError") throw cause
      throw new ApiError({
        status: 0,
        code: "network_error",
        message: "Could not reach the Vizlify API. Check that the backend is running.",
      })
    }

    const payload = await readEnvelope(response)

    if (!response.ok) {
      throw new ApiError({
        status: response.status,
        code: payload?.error?.code ?? `http_${response.status}`,
        message:
          payload?.error?.message ?? `Request failed with status ${response.status}.`,
        details: payload?.error?.details,
      })
    }

    return (payload?.data ?? null) as T
  }

  return {
    get: <T>(path: string, signal?: AbortSignal) => request<T>(path, { signal }),
    post: <T>(path: string, body: unknown) =>
      request<T>(path, { method: "POST", body: JSON.stringify(body) }),
    patch: <T>(path: string, body: unknown) =>
      request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
    delete: <T = null>(path: string) => request<T>(path, { method: "DELETE" }),
  }
}
