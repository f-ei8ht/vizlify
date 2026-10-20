"use client"

import {
  CheckIcon,
  PlayIcon,
  RefreshCwIcon,
  SendIcon,
  XIcon,
} from "lucide-react"
import { useState } from "react"

import { DataState } from "@/components/query/data-state"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import {
  useActions,
  useApproveAction,
  useRejectAction,
} from "@/lib/api/actions"
import {
  useCancelInvoice,
  useInvoices,
  useProposeInvoicePayout,
  useRefreshInvoice,
  useRemindInvoice,
} from "@/lib/api/invoices"
import { usePayouts, useProposePayoutExecution } from "@/lib/api/payouts"
import type { ActionKind } from "@/lib/api/types"
import { formatDate, formatMoney } from "@/lib/format"

const KIND_LABELS: Record<ActionKind, string> = {
  create_invoice: "Create invoice",
  send_invoice: "Send invoice",
  send_reminder: "Send reminder",
  cancel_invoice: "Cancel invoice",
  prepare_payout: "Prepare payout",
  execute_payout: "Execute payout",
  draft_dispute_response: "Draft dispute response",
}

type BadgeVariant = "default" | "secondary" | "destructive" | "outline"

function statusVariant(status: string): BadgeVariant {
  if (["paid", "success", "executed"].includes(status)) return "default"
  if (["failed", "denied", "cancelled"].includes(status)) return "destructive"
  if (["sent", "pending", "unclaimed"].includes(status)) return "secondary"
  return "outline"
}

function report(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong."
}

export default function DashboardPage() {
  const [error, setError] = useState<string | null>(null)
  const [rejecting, setRejecting] = useState<string | null>(null)
  const [reason, setReason] = useState("")

  const actions = useActions("pending")
  const invoices = useInvoices()
  const payouts = usePayouts()

  const approve = useApproveAction()
  const reject = useRejectAction()
  const remind = useRemindInvoice()
  const cancel = useCancelInvoice()
  const refresh = useRefreshInvoice()
  const proposePayout = useProposeInvoicePayout()
  const executePayout = useProposePayoutExecution()

  const onError = (cause: unknown) => setError(report(cause))

  function submitRejection(id: string) {
    if (!reason.trim()) return
    reject.mutate(
      { id, reason: reason.trim() },
      {
        onSuccess: () => {
          setRejecting(null)
          setReason("")
          setError(null)
        },
        onError,
      },
    )
  }

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-6 py-8">
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">Money Board</h1>
          <Badge variant="destructive">Sandbox only — no real money</Badge>
        </div>
        <p className="max-w-2xl text-sm text-muted-foreground">
          The agent proposes; you approve. Nothing reaches PayPal until a
          proposal is approved here.
        </p>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertTitle>That did not work</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <section className="flex flex-col gap-3">
        <header className="flex items-end justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold">Approval queue</h2>
            <p className="text-sm text-muted-foreground">
              Each proposal is executed once. A second approve returns 409.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void actions.refetch()}
            disabled={actions.isFetching}
          >
            <RefreshCwIcon data-icon="inline-start" />
            Refresh
          </Button>
        </header>

        <DataState
          query={actions}
          skeleton={<p className="text-sm text-muted-foreground">Loading proposals…</p>}
          isEmpty={(data) => data.length === 0}
          empty={
            <Empty>
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <CheckIcon />
                </EmptyMedia>
                <EmptyTitle>Nothing waiting</EmptyTitle>
                <EmptyDescription>
                  Mark a milestone done or send a reminder to create a proposal.
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          }
        >
          {(data) => (
            <ul className="flex flex-col gap-3">
              {data.map((action) => (
                <li
                  key={action.id}
                  className="flex flex-col gap-3 rounded-2xl border bg-card p-4"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{KIND_LABELS[action.kind]}</Badge>
                    <Badge variant={statusVariant(action.status)}>
                      {action.status}
                    </Badge>
                  </div>
                  <p className="text-sm">{action.rationale}</p>
                  <p className="font-mono text-xs text-muted-foreground">
                    {action.id}
                  </p>

                  {rejecting === action.id ? (
                    <div className="flex flex-col gap-2 sm:flex-row">
                      <input
                        value={reason}
                        onChange={(event) => setReason(event.target.value)}
                        placeholder="Why are you rejecting this?"
                        className="h-9 flex-1 rounded-lg border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        aria-label="Rejection reason"
                      />
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => submitRejection(action.id)}
                        disabled={reject.isPending || !reason.trim()}
                      >
                        Confirm rejection
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setRejecting(null)
                          setReason("")
                        }}
                      >
                        Cancel
                      </Button>
                    </div>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        onClick={() =>
                          approve.mutate(action.id, {
                            onSuccess: () => setError(null),
                            onError,
                          })
                        }
                        disabled={approve.isPending}
                      >
                        <CheckIcon data-icon="inline-start" />
                        Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setRejecting(action.id)
                          setReason("")
                        }}
                      >
                        <XIcon data-icon="inline-start" />
                        Reject
                      </Button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </DataState>
      </section>

      <section className="flex flex-col gap-3">
        <header className="flex items-end justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold">Invoices</h2>
            <p className="text-sm text-muted-foreground">
              Created and sent through PayPal after approval.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void invoices.refetch()}
            disabled={invoices.isFetching}
          >
            <RefreshCwIcon data-icon="inline-start" />
            Refresh
          </Button>
        </header>

        <DataState
          query={invoices}
          skeleton={<p className="text-sm text-muted-foreground">Loading invoices…</p>}
          isEmpty={(data) => data.length === 0}
          empty={
            <Empty>
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <SendIcon />
                </EmptyMedia>
                <EmptyTitle>No invoices yet</EmptyTitle>
                <EmptyDescription>
                  Mark a milestone done, then approve the invoice proposal.
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          }
        >
          {(data) => (
            <ul className="flex flex-col gap-3">
              {data.map((invoice) => (
                <li
                  key={invoice.id}
                  className="flex flex-col gap-3 rounded-2xl border bg-card p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">
                        {invoice.number ?? "Draft"}
                      </span>
                      <Badge variant={statusVariant(invoice.status)}>
                        {invoice.status}
                      </Badge>
                      <span className="text-sm text-muted-foreground">
                        {formatMoney(invoice.amount, invoice.currency)}
                      </span>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      Due {formatDate(invoice.due_date)}
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {invoice.status === "sent" ? (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            remind.mutate(invoice.id, { onError })
                          }
                          disabled={remind.isPending}
                        >
                          Remind
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            refresh.mutate(invoice.id, { onError })
                          }
                          disabled={refresh.isPending}
                        >
                          Sync PayPal
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() =>
                            cancel.mutate(invoice.id, { onError })
                          }
                          disabled={cancel.isPending}
                        >
                          Cancel
                        </Button>
                      </>
                    ) : null}
                    {invoice.status === "paid" ? (
                      <Button
                        size="sm"
                        onClick={() =>
                          proposePayout.mutate(invoice.id, { onError })
                        }
                        disabled={proposePayout.isPending}
                      >
                        Prepare payout
                      </Button>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </DataState>
      </section>

      <section className="flex flex-col gap-3">
        <header>
          <h2 className="text-lg font-semibold">Payouts</h2>
          <p className="text-sm text-muted-foreground">
            Splits are rounded to the cent and capped before PayPal is called.
          </p>
        </header>

        <DataState
          query={payouts}
          skeleton={<p className="text-sm text-muted-foreground">Loading payouts…</p>}
          isEmpty={(data) => data.length === 0}
          empty={
            <Empty>
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <PlayIcon />
                </EmptyMedia>
                <EmptyTitle>No payouts yet</EmptyTitle>
                <EmptyDescription>
                  A paid invoice can be split across the team.
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          }
        >
          {(data) => (
            <ul className="flex flex-col gap-3">
              {data.map((payout) => (
                <li
                  key={payout.id}
                  className="flex flex-col gap-3 rounded-2xl border bg-card p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">
                        {formatMoney(payout.total, payout.currency)}
                      </span>
                      <Badge variant={statusVariant(payout.status)}>
                        {payout.status}
                      </Badge>
                      {payout.paypal_batch_id ? (
                        <span className="font-mono text-xs text-muted-foreground">
                          {payout.paypal_batch_id}
                        </span>
                      ) : null}
                    </div>
                    {!payout.paypal_batch_id ? (
                      <Button
                        size="sm"
                        onClick={() =>
                          executePayout.mutate(payout.id, { onError })
                        }
                        disabled={executePayout.isPending}
                      >
                        Propose execution
                      </Button>
                    ) : null}
                  </div>

                  <ul className="grid gap-2 sm:grid-cols-3">
                    {payout.items.map((item) => (
                      <li
                        key={item.id}
                        className="flex items-center justify-between rounded-xl border px-3 py-2 text-sm"
                      >
                        <span>{formatMoney(item.amount, payout.currency)}</span>
                        <Badge variant={statusVariant(item.status)}>
                          {item.status}
                        </Badge>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          )}
        </DataState>
      </section>
    </main>
  )
}
