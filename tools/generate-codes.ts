import { randomBytes } from "crypto"

const COUNT = 100
const PREFIX = "fire"

function generateCode(): string {
  return `${PREFIX}-${randomBytes(4).toString("hex")}`
}

const codes = Array.from({ length: COUNT }, generateCode)

console.log("=== 個別リスト（スプレッドシート用）===")
codes.forEach((code, i) => console.log(`${i + 1}\t${code}`))

console.log("\n=== VALID_CODES（Vercel環境変数用）===")
console.log(codes.join(","))
