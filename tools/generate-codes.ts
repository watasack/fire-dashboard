import { randomBytes } from "crypto"
import { writeFileSync } from "fs"
import { join, dirname } from "path"
import { fileURLToPath } from "url"

const COUNT = 100
const PREFIX = "fire"
const __dirname = dirname(fileURLToPath(import.meta.url))
const outDir = join(__dirname, "..", "secrets")

function generateCode(): string {
  return `${PREFIX}-${randomBytes(4).toString("hex")}`
}

const codes = Array.from({ length: COUNT }, generateCode)

// コンソール出力
console.log("=== 個別リスト（スプレッドシート用）===")
codes.forEach((code, i) => console.log(`${i + 1}\t${code}`))

console.log("\n=== VALID_CODES（Vercel環境変数用）===")
console.log(codes.join(","))

// ファイル保存
import { mkdirSync } from "fs"
mkdirSync(outDir, { recursive: true })

const tsvLines = codes.map((code, i) => `${i + 1}\t${code}\t\t未送付`).join("\n")
writeFileSync(join(outDir, "codes.tsv"), `#\tコード\t送付日\tステータス\n${tsvLines}\n`)

writeFileSync(join(outDir, "valid_codes.txt"), codes.join(",") + "\n")

console.log(`\n✅ 保存完了:`)
console.log(`   secrets/codes.tsv        — スプレッドシート用`)
console.log(`   secrets/valid_codes.txt   — Vercel環境変数用`)
