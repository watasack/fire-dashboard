import { createHmac, timingSafeEqual } from "crypto"
import { NextRequest, NextResponse } from "next/server"

export async function GET(request: NextRequest) {
  const authHeader = request.headers.get("authorization") ?? ""
  const token = authHeader.startsWith("Bearer ") ? authHeader.slice(7) : ""

  if (!token) {
    return NextResponse.json({ valid: false })
  }

  const parts = token.split(".")
  if (parts.length !== 2) {
    return NextResponse.json({ valid: false })
  }
  const [code, sig] = parts

  const secret = process.env.AUTH_SECRET ?? ""
  const expected = createHmac("sha256", secret).update(code).digest("hex")

  // 長さガード（timingSafeEqual はバッファ長が違うと TypeError）
  if (sig.length !== expected.length) {
    return NextResponse.json({ valid: false })
  }

  let sigMatch = false
  try {
    sigMatch = timingSafeEqual(Buffer.from(sig, "hex"), Buffer.from(expected, "hex"))
  } catch {
    return NextResponse.json({ valid: false })
  }

  if (!sigMatch) {
    return NextResponse.json({ valid: false })
  }

  const validCodes = (process.env.VALID_CODES ?? "")
    .split(",")
    .map((c) => c.trim())
    .filter(Boolean)

  return NextResponse.json({ valid: validCodes.includes(code) })
}
