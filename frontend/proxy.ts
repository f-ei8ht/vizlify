import { clerkMiddleware } from "@clerk/nextjs/server"
import { NextResponse } from "next/server"

const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY)

// Without a Clerk key the app runs in AUTH_MODE=dev, so there is nothing to do
// before the request reaches the app.
export default clerkEnabled
  ? clerkMiddleware()
  : function proxy() {
      return NextResponse.next()
    }

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/__clerk/:path*",
    "/(api|trpc)(.*)",
  ],
}
