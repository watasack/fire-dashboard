import { createHmac } from "crypto"
import { NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null)
  const code: string = body?.code ?? ""

  // ログ出力
  console.log(JSON.stringify({
    event: "validate",
    code: code.length >= 6 ? code.slice(0, 6) + "***" : "***",
    ip: request.headers.get("x-forwarded-for"),
    ua: request.headers.get("user-agent"),
    ts: new Date().toISOString(),
  }))

  if (!code) {
    return NextResponse.json({ error: "code required" }, { status: 400 })
  }

  const secret = process.env.AUTH_SECRET ?? ""
  const validCodes = (process.env.VALID_CODES ?? "")
    .split(",")
    .map((c) => c.trim())
    .filter(Boolean)

  if (!validCodes.includes(code)) {
    return NextResponse.json({ error: "invalid code" }, { status: 401 })
  }

  const sig = createHmac("sha256", secret).update(code).digest("hex")
  const token = `${code}.${sig}`

  return NextResponse.json({ token })
}
