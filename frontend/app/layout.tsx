import { ClerkProvider, Show, SignInButton, SignUpButton, UserButton } from "@clerk/nextjs"
import { Geist_Mono, Inter } from "next/font/google"

import "./globals.css"
import { ThemeProvider } from "@/components/theme-provider"
import { cn } from "@/lib/utils"

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" })

const fontMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
})

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={cn("antialiased", fontMono.variable, "font-sans", inter.variable)}
    >
      <body>
        <ClerkProvider>
          <ThemeProvider>
            <header className="flex h-16 items-center justify-end gap-4 p-4">
              <Show when="signed-out">
                <SignInButton />
                <SignUpButton>
                  <button className="h-10 cursor-pointer rounded-full bg-purple-700 px-5 text-sm font-medium text-white sm:h-12 sm:text-base">
                    Sign up
                  </button>
                </SignUpButton>
              </Show>
              <Show when="signed-in">
                <UserButton />
              </Show>
            </header>
            {children}
          </ThemeProvider>
        </ClerkProvider>
      </body>
    </html>
  )
}
