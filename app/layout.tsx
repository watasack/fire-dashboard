import type { Metadata, Viewport } from "next"
import { Inter, JetBrains_Mono } from "next/font/google"
import "./globals.css"

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
})

export const metadata: Metadata = {
  title: "共働き・子育てFIREシミュレーター | 育休・時短を考慮した確率計算",
  description: "育休・時短・教育費など共働き世帯のリアルを反映したFIREシミュレーター。1000通りのシミュレーションでFIRE成功確率を計算。登録不要・無料デモあり。",
  keywords: ["FIRE", "共働きFIRE", "育休FIRE", "FIREシミュレーター", "早期退職", "経済的自立", "子育てFIRE", "育休影響", "セミFIRE"],
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#1a365d",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ja">
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased`}>
        {children}
      </body>
    </html>
  )
}
