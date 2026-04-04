"use client"

import { useEffect, useState } from "react"
import { FireDashboard } from "./dashboard"
import { getToken, setToken } from "@/lib/auth"

type AuthState = "loading" | "authed" | "demo"

function DashboardSkeleton() {
  return (
    <div className="min-h-screen bg-background animate-pulse">
      <div className="h-16 border-b bg-card" />
      <div className="container mx-auto px-4 py-6">
        <div className="h-8 bg-muted rounded w-64 mb-4" />
        <div className="h-64 bg-muted rounded" />
      </div>
    </div>
  )
}

export function AccessGate() {
  const [authState, setAuthState] = useState<AuthState>("loading")

  useEffect(() => {
    const token = getToken()

    fetch("/api/ping", {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((res) => res.json())
      .then(({ valid }) => {
        setAuthState(valid ? "authed" : "demo")
      })
      .catch(() => {
        // フェールオープン: トークンがあればauthed、なければdemo
        setAuthState(token ? "authed" : "demo")
      })
  }, [])

  const handleUnlock = (token: string) => {
    setToken(token)
    setAuthState("authed")
  }

  if (authState === "loading") return <DashboardSkeleton />

  return (
    <FireDashboard
      isDemoMode={authState === "demo"}
      onUnlock={handleUnlock}
    />
  )
}
