"use client"

import { useState } from "react"
import { Lock } from "lucide-react"
import { Button } from "@/components/ui/button"

interface LockOverlayProps {
  onUnlock: (token: string) => void
}

export function LockOverlay({ onUnlock }: LockOverlayProps) {
  const [code, setCode] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const res = await fetch("/api/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: code.trim() }),
      })
      if (res.ok) {
        const { token } = await res.json()
        onUnlock(token)
      } else {
        setError("コードが正しくありません")
      }
    } catch {
      setError("通信エラーが発生しました。再度お試しください。")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="absolute inset-0 z-10 flex items-center justify-center rounded-lg">
      {/* ぼかし背景 */}
      <div className="absolute inset-0 bg-background/60 backdrop-blur-sm rounded-lg" />
      {/* カード */}
      <div className="relative z-10 w-full max-w-xs mx-4 bg-card border rounded-xl shadow-lg p-5 space-y-3">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Lock className="h-4 w-4 text-muted-foreground" />
          フル版で利用できます
        </div>
        <p className="text-xs text-muted-foreground">
          アクセスコードを入力するとすべての機能が解放されます。
        </p>
        <form onSubmit={handleSubmit} className="space-y-2">
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="アクセスコードを入力"
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            disabled={loading}
          />
          {error && <p className="text-xs text-destructive">{error}</p>}
          <Button type="submit" className="w-full" size="sm" disabled={loading || !code.trim()}>
            {loading ? "確認中..." : "解放する"}
          </Button>
        </form>
      </div>
    </div>
  )
}
