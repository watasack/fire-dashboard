import type { Metadata } from "next"
import Link from "next/link"
import { TrendingUp, ArrowLeft } from "lucide-react"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { Card, CardContent } from "@/components/ui/card"

export const metadata: Metadata = {
  title: "よくある質問 | FIREシミュレーター",
  description: "FIREシミュレーターに関するよくある質問。生活費の範囲・シミュレーションの仕組み・各入力項目の説明など。",
}

type FAQ = {
  question: string
  answer: React.ReactNode
}

type FAQCategory = {
  title: string
  faqs: FAQ[]
}

const categories: FAQCategory[] = [
  {
    title: "シミュレーションの基本",
    faqs: [
      {
        question: "FIRE成功確率とは何ですか？",
        answer: (
          <>
            <p>
              1,000通りの異なる市場シナリオ（モンテカルロシミュレーション）を使い、「100歳まで資産が枯渇しないシナリオの割合」をFIRE成功確率として表示しています。
            </p>
            <p className="mt-2">
              たとえば成功確率80%なら、1,000通りのシナリオのうち800通りで老後まで資産が持つ計算になります。一般的に70〜80%以上が堅実とされますが、家庭の状況に応じて判断してください。
            </p>
          </>
        ),
      },
      {
        question: "モンテカルロシミュレーションとは何ですか？",
        answer: (
          <>
            <p>
              毎年の投資リターンをランダムに変動させながら、資産の推移を1,000回シミュレーションする手法です。「平均的な未来」だけでなく、リーマンショックのような暴落が重なる最悪シナリオや、好調が続く楽観シナリオも含めて確率的に評価できます。
            </p>
            <p className="mt-2">
              グラフの帯（中央50%の確率範囲）は、1,000通りのうち25〜75パーセンタイルの範囲を示しています。
            </p>
          </>
        ),
      },
      {
        question: "FIRE達成年齢はどのように計算されますか？",
        answer: (
          <p>
            退職しても収支シミュレーション上で資産が尽きない最も早い年齢をFIRE達成年齢としています。年金・セミFIRE収入・教育費・住宅ローンなど将来の収支変動をすべて織り込んで判定します。モンテカルロモードでは1,000通りの市場シナリオの中央値（50パーセンタイル）を表示します。
          </p>
        ),
      },
    ],
  },
  {
    title: "生活費・支出について",
    faqs: [
      {
        question: "生活費には何が含まれますか？何が含まれませんか？",
        answer: (
          <>
            <p className="font-medium">生活費に含まれるもの（基本タブで入力）：</p>
            <ul className="mt-1 ml-4 list-disc space-y-0.5">
              <li>食費・光熱費・通信費・日用品</li>
              <li>交際費・娯楽・被服費</li>
              <li>保険料（生命保険・医療保険など）</li>
              <li>交通費・車の維持費</li>
            </ul>
            <p className="mt-3 font-medium">生活費に含まれないもの（別途入力）：</p>
            <ul className="mt-1 ml-4 list-disc space-y-0.5">
              <li>住宅ローン返済額 → ライフタブで入力</li>
              <li>家賃 → ライフタブ（賃貸選択時）で入力</li>
              <li>固定資産税 → ライフタブで入力</li>
              <li>住宅の大規模修繕費 → ライフタブで入力</li>
              <li>子どもの教育費 → ライフタブで入力</li>
              <li>保育料 → ライフタブの子どもカードで入力</li>
              <li>NISA・iDeCoへの積立金 → 投資タブで入力（支出ではなく資産移動として扱う）</li>
            </ul>
            <p className="mt-3 text-sm text-muted-foreground">
              迷った場合は「生活費に含めて大きめに設定する」か、「別項目で個別に入力する」かのどちらかに統一してください。二重計上にならないよう注意してください。
            </p>
          </>
        ),
      },
      {
        question: "ライフステージ別に生活費を変えられますか？",
        answer: (
          <>
            <p>
              基本タブの「生活費の算出方法」で「ライフステージ別」を選ぶと、以下のステージごとに生活費を個別設定できます。
            </p>
            <ul className="mt-2 ml-4 list-disc space-y-0.5">
              <li>現役期（現在〜退職まで）</li>
              <li>リタイア期（退職〜65歳）</li>
              <li>シニア期（65〜75歳）</li>
              <li>後期高齢者期（75歳〜）</li>
              <li>子育て期（子どもがいる期間）</li>
              <li>独立後（末子が18歳以降）</li>
            </ul>
            <p className="mt-2 text-sm text-muted-foreground">
              退職後は外食・交通費が減る一方、医療費が増える傾向があります。ライフステージ別モードで細かく設定するとより現実的なシミュレーションになります。
            </p>
          </>
        ),
      },
      {
        question: "セミFIRE時の収入はどう扱われますか？",
        answer: (
          <p>
            ライフタブの「セミFIRE」をONにすると、FIRE後も一定の収入（パートや仕事など）が続く想定でシミュレーションできます。設定した収入は、指定した年齢まで毎年の支出から差し引かれます。完全リタイアより資産の取り崩しが緩やかになるため、FIRE達成年齢が早まります。
          </p>
        ),
      },
      {
        question: "インフレ率と生活費上昇率はどう違いますか？",
        answer: (
          <>
            <ul className="ml-4 list-disc space-y-2">
              <li>
                <span className="font-medium">生活費上昇率</span>：毎年の生活費の増加率。昇給・子どもの成長・生活水準の向上などで生活費が増える効果を表します。
              </li>
              <li>
                <span className="font-medium">インフレ率</span>：物価上昇率。同じ生活水準でも将来的にかかる費用が増える効果（購買力の低下）を表します。
              </li>
            </ul>
            <p className="mt-2 text-sm text-muted-foreground">
              両方を設定するとやや保守的なシミュレーションになります。「どちらか一方に合算して設定する」シンプルな使い方でも構いません。
            </p>
          </>
        ),
      },
    ],
  },
  {
    title: "収入・雇用について",
    faqs: [
      {
        question: "育休中の収入はどう計算されますか？",
        answer: (
          <>
            <p>
              ライフタブの子どもカードで産休・育休取得者を設定すると、育休期間中は就労収入の代わりに育児休業給付金が自動で計算されます。
            </p>
            <ul className="mt-2 ml-4 list-disc space-y-1 text-sm">
              <li>育休開始から180日間：手取り換算で約67%相当</li>
              <li>181日目以降：手取り換算で約50%相当</li>
            </ul>
            <p className="mt-2 text-sm text-muted-foreground">
              実際の給付額は標準報酬月額をもとに計算されるため、あくまで参考値です。
            </p>
          </>
        ),
      },
      {
        question: "自営業・フリーランスの場合、年収上昇率はどう設定すればよいですか？",
        answer: (
          <p>
            雇用形態を「自営業・フリーランス」に設定すると、年収上昇率のデフォルト値が0%になります。収入が不安定なため、保守的に0%から始め、売上の見通しに応じて調整してください。会社員と異なり定期昇給がないため、慎重な設定を推奨します。
          </p>
        ),
      },
      {
        question: "配偶者が専業主婦（主夫）の場合はどう設定しますか？",
        answer: (
          <p>
            収入タブで配偶者の雇用形態を「専業主婦・主夫」に設定してください。就労収入は0として計算され、退職年齢の設定は無効になります。将来的に再就職する予定がある場合は、雇用形態を「会社員」などに変更して年収を設定してください。
          </p>
        ),
      },
    ],
  },
  {
    title: "資産・投資について",
    faqs: [
      {
        question: "株式・NISA残高に含めてよいものは何ですか？",
        answer: (
          <>
            <p className="font-medium">株式（課税口座）に含めるもの：</p>
            <ul className="mt-1 ml-4 list-disc space-y-0.5">
              <li>証券口座の株式・投資信託・ETF（課税口座分）</li>
            </ul>
            <p className="mt-3 font-medium">NISAに含めるもの：</p>
            <ul className="mt-1 ml-4 list-disc space-y-0.5">
              <li>新NISA口座（成長投資枠・つみたて投資枠）の残高</li>
            </ul>
            <p className="mt-3 font-medium">現金・預金に含めるもの：</p>
            <ul className="mt-1 ml-4 list-disc space-y-0.5">
              <li>銀行預金・定期預金・外貨預金・保険積立金・金（きん）</li>
            </ul>
            <p className="mt-2 text-sm text-muted-foreground">
              保険積立や外貨預金は市場リスクがあるものの、シミュレーターでは現金・預金として一律に扱います。より細かく分けたい場合は「その他資産」カードをご利用ください。
            </p>
          </>
        ),
      },
      {
        question: "新NISAはどう設定すればよいですか？",
        answer: (
          <>
            <p>
              投資タブの「新NISA」をONにすると設定できます。
            </p>
            <ul className="mt-2 ml-4 list-disc space-y-1 text-sm">
              <li><span className="font-medium">現在の残高</span>：すでに新NISA口座に保有している評価額</li>
              <li><span className="font-medium">年間積立額</span>：毎年の積立予定額（つみたて投資枠 最大120万円 + 成長投資枠 最大240万円、合計最大360万円）</li>
            </ul>
            <p className="mt-2 text-sm text-muted-foreground">
              NISA口座内の資産は運用益に非課税のため、課税口座より有利です。シミュレーターは売却時の税金を考慮した計算を行います。
            </p>
          </>
        ),
      },
      {
        question: "期待リターンとリスク（標準偏差）はどう設定すればよいですか？",
        answer: (
          <>
            <p>
              過去実績を参考に設定してください。
            </p>
            <ul className="mt-2 ml-4 list-disc space-y-2 text-sm">
              <li>
                <span className="font-medium">オール株式（S&P500相当）</span>：期待リターン6〜7%、リスク15〜18%
              </li>
              <li>
                <span className="font-medium">バランス型（株式60%・債券40%）</span>：期待リターン4〜5%、リスク10〜12%
              </li>
              <li>
                <span className="font-medium">保守型（債券中心）</span>：期待リターン2〜3%、リスク5〜7%
              </li>
            </ul>
            <p className="mt-2 text-sm text-muted-foreground">
              これらは過去の実績であり、将来の運用成績を保証するものではありません。
            </p>
          </>
        ),
      },
    ],
  },
  {
    title: "住宅・ライフイベントについて",
    faqs: [
      {
        question: "住宅ローンと家賃はどこで設定しますか？",
        answer: (
          <>
            <p>ライフタブの「住居」カードで設定します。</p>
            <ul className="mt-2 ml-4 list-disc space-y-1 text-sm">
              <li><span className="font-medium">持ち家</span>：住宅ローンカードで月返済額または借入条件から計算</li>
              <li><span className="font-medium">賃貸</span>：月額家賃を入力（年間コストとして計上）</li>
              <li><span className="font-medium">将来購入</span>：現在は賃貸・将来購入予定の場合、購入予定年と頭金を設定可能</li>
            </ul>
            <p className="mt-2 text-sm text-muted-foreground">
              住宅ローン返済額と家賃は、生活費とは別に計上されます。基本タブの生活費に含めないよう注意してください。
            </p>
          </>
        ),
      },
      {
        question: "教育費はどのように計算されますか？",
        answer: (
          <>
            <p>
              ライフタブで子どもごとに「幼保・小・中・高・大学」それぞれの公立/私立を設定できます。全公立・混合・全私立のプリセットも用意しています。
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              教育費は文部科学省の「子供の学習費調査」をもとにしたデフォルト値を使用しています。実際の費用に合わせて調整してください。なお、習い事・塾代などの費用は生活費に含めるか、教育費として別途調整してください。
            </p>
          </>
        ),
      },
      {
        question: "児童手当はどのように計算されますか？",
        answer: (
          <>
            <p>2024年10月改正後の制度に基づいて計算しています。</p>
            <ul className="mt-2 ml-4 list-disc space-y-1 text-sm">
              <li>3歳未満：15,000円/月</li>
              <li>3歳〜18歳（高校卒業まで）：10,000円/月</li>
              <li>第3子以降：30,000円/月</li>
            </ul>
            <p className="mt-2 text-sm text-muted-foreground">
              所得制限は2024年10月以降撤廃されているため、シミュレーターでは所得に関わらず支給されるものとして計算しています。
            </p>
          </>
        ),
      },
      {
        question: "固定資産税はどこで入力しますか？",
        answer: (
          <p>
            ライフタブに「固定資産税」の年額入力欄があります。持ち家の場合、一般的には年10〜30万円程度です（物件価格や所在地によって異なります）。賃貸の場合は0円のままで問題ありません。
          </p>
        ),
      },
    ],
  },
]

export default function FAQPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
              <TrendingUp className="h-5 w-5 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-tight hidden lg:block">FIRE シミュレーター</h1>
              <p className="text-xs text-muted-foreground">育休や時短の影響も含めて、あなたのFIRE時期を計算します</p>
            </div>
          </div>
          <Link
            href="/"
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            シミュレーターに戻る
          </Link>
        </div>
      </header>

      {/* Main */}
      <main className="container mx-auto px-4 py-10 max-w-3xl">
        <div className="mb-8">
          <h2 className="text-2xl font-bold tracking-tight">よくある質問</h2>
          <p className="mt-1 text-muted-foreground">
            シミュレーターの使い方や計算の仕組みについて、よくある質問をまとめました。
          </p>
        </div>

        <div className="space-y-6">
          {categories.map((category) => (
            <Card key={category.title}>
              <CardContent className="pt-5 pb-2">
                <h3 className="text-sm font-semibold text-primary mb-3">{category.title}</h3>
                <Accordion type="single" collapsible className="w-full">
                  {category.faqs.map((faq, i) => (
                    <AccordionItem key={i} value={`${category.title}-${i}`}>
                      <AccordionTrigger className="text-left text-sm font-medium">
                        {faq.question}
                      </AccordionTrigger>
                      <AccordionContent className="text-sm text-muted-foreground leading-relaxed">
                        {faq.answer}
                      </AccordionContent>
                    </AccordionItem>
                  ))}
                </Accordion>
              </CardContent>
            </Card>
          ))}
        </div>

        <p className="mt-8 text-center text-xs text-muted-foreground">
          他にご不明な点がある場合は、シミュレーター内の各項目の
          <span className="inline-flex items-center justify-center w-4 h-4 rounded-full border border-current text-[10px] mx-1">?</span>
          ボタンから詳細をご確認ください。
        </p>
      </main>
    </div>
  )
}
