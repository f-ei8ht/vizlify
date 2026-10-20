"use client"

import { Show, SignInButton, SignUpButton, UserButton } from "@clerk/nextjs"

import { Badge } from "@/components/ui/badge"

export function SiteHeader({ clerkEnabled }: { clerkEnabled: boolean }) {
  return (
    <header className="flex h-16 items-center justify-end gap-4 p-4">
      {clerkEnabled ? (
        <>
          <Show when="signed-out">
            <SignInButton />
            <SignUpButton>
              <button className="h-10 cursor-pointer rounded-full bg-primary px-5 text-sm font-medium text-primary-foreground sm:h-12 sm:text-base">
                Sign up
              </button>
            </SignUpButton>
          </Show>
          <Show when="signed-in">
            <UserButton />
          </Show>
        </>
      ) : (
        <Badge variant="outline">Demo mode · no sign-in</Badge>
      )}
    </header>
  )
}
