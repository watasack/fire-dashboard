# FIRE Dashboard

Financial Independence, Retire Early（FIRE）達成・維持のための可視化ダッシュボードシステム

## 概要

このプロジェクトは、MoneyForwardから取得した資産・収支データを分析し、FIRE目標額を精緻に計算、将来の資産推移をシミュレーションして、インタラクティブなダッシュボードとして可視化します。

### 主な機能

1. **資産推移グラフ** - 時系列での総資産・純資産・債務の推移を表示
2. **FIRE達成進捗** - 目標額に対する現在の達成率と到達予測を可視化
3. **カテゴリー別支出分析** - 食費・交通費などカテゴリー別の支出内訳
4. **将来資産シミュレーション** - 楽観・標準・悲観の3シナリオで将来を予測

### FIRE目標額の計算方法

単純な「4%ルール」ではなく、**将来の収入・支出を精緻にシミュレーションし、二分探索アルゴリズムで「資産が枯渇しない最低額」を逆算**します。さらに、3つのシナリオ（楽観・標準・悲観）で検証し、最も悲観的なケースでも破綻しない額に安全バッファ（20%）を加えた値を推奨目標額とします。

## セットアップ

### 前提条件

- Python 3.8以上
- pip

### インストール

1. リポジトリをクローン（または既に存在する場合はスキップ）

```bash
cd c:\Users\shuhe\Documents\01_personal
```

2. 依存関係をインストール

```bash
pip install -r requirements.txt
```

### データファイルの配置

MoneyForwardからエクスポートしたCSVファイルを `data/` ディレクトリに配置します。

```
data/
├── 資産推移月次.csv
└── 収入・支出詳細_YYYY-MM-DD_YYYY-MM-DD.csv
```

## 使用方法

### ダッシュボードの生成

```bash
python scripts/generate_dashboard.py
```

実行すると、以下の8ステップが自動的に実行されます：

1. 設定読み込み（`config.yaml`）
2. データファイル読み込み
3. データ処理・クリーニング
4. 現状分析
5. FIRE目標額計算（二分探索）
6. 将来シミュレーション（3シナリオ）
7. グラフ生成（Plotly）
8. HTML出力

生成されたダッシュボードは `docs/index.html` に保存されます。

### ローカルでの確認

ブラウザで `docs/index.html` を開きます。

```bash
# Windowsの場合
start docs/index.html

# macOS/Linuxの場合
open docs/index.html
```

## 設定のカスタマイズ

`config.yaml` ファイルを編集することで、シミュレーションパラメータをカスタマイズできます。

### 主な設定項目

```yaml
simulation:
  years: 50                      # シミュレーション期間（年）
  life_expectancy: 90            # 想定寿命

  standard:
    annual_return_rate: 0.05     # 年率リターン（5%）
    inflation_rate: 0.02         # インフレ率（2%）
    income_growth_rate: 0.02     # 収入成長率（2%）
    expense_growth_rate: 0.02    # 支出成長率（2%）

fire:
  safety_buffer: 1.2             # 安全バッファ（20%）
  withdrawal_rate: 0.04          # 4%ルール（参考値）
```

設定変更後は、再度 `python scripts/generate_dashboard.py` を実行してください。

## GitHub Pagesでの公開

### 初回セットアップ

1. GitHubにプッシュ

```bash
git add .
git commit -m "Initial FIRE dashboard"
git push origin main
```

2. GitHub Pagesを有効化

- GitHubリポジトリページにアクセス
- `Settings` → `Pages`
- Source: `main` ブランチ、`/docs` フォルダを選択
- `Save` をクリック

数分後、ダッシュボードがGitHub Pagesで公開されます。

### 更新フロー

データファイルを更新した後：

```bash
# 1. ダッシュボード再生成
python scripts/generate_dashboard.py

# 2. Git commit & push
git add docs/
git commit -m "Update dashboard $(date +%Y-%m-%d)"
git push origin main
```

プッシュ後、数分でGitHub Pages上のダッシュボードが自動更新されます。

## プロジェクト構造

```
.
├── config.yaml              # シミュレーション設定
├── requirements.txt         # Python依存関係
├── README.md               # このファイル
├── data/                   # データファイル（.gitignoreで除外）
│   ├── 資産推移月次.csv
│   └── 収入・支出詳細_*.csv
├── src/                    # ソースコード
│   ├── config.py           # 設定管理
│   ├── data_loader.py      # データ読み込み
│   ├── data_processor.py   # データ処理
│   ├── analyzer.py         # 現状分析
│   ├── simulator.py        # 将来シミュレーション
│   ├── fire_calculator.py  # FIRE目標額計算
│   ├── visualizer.py       # グラフ生成
│   └── html_generator.py   # HTML生成
├── docs/                   # GitHub Pages用（生成物）
│   ├── index.html          # ダッシュボード
│   ├── assets/
│   │   └── styles.css      # スタイル
│   └── .nojekyll
└── scripts/
    └── generate_dashboard.py  # メインスクリプト
```

## セキュリティとプライバシー

### データ保護

- `data/` ディレクトリは `.gitignore` で除外されており、GitHubにアップロードされません
- 生成されるHTMLには**集計値のみ**が含まれ、元のトランザクションデータは含まれません
- プライベートリポジトリの使用を推奨します

### GitHub Pagesの公開範囲

- パブリックリポジトリの場合、GitHub Pagesは誰でもアクセス可能です
- プライベートリポジトリ + GitHub Pro/Teamプランの場合、Pages公開範囲を制限できます
- 家族のみに共有する場合は、プライベートリポジトリを使用してください

## トラブルシューティング

### エンコーディングエラー

CSVファイルの文字化けが発生する場合：

1. `config.yaml` の `data.encoding` を変更
   ```yaml
   data:
     encoding: 'shift_jis'  # または 'utf-8'
   ```

2. CSVファイルをUTF-8で保存し直す（Excel → 名前を付けて保存 → CSV UTF-8）

### グラフが表示されない

- ブラウザのJavaScriptが有効か確認
- ブラウザのコンソールでエラーを確認
- Plotly CDNにアクセスできるか確認（インターネット接続必要）

### 依存関係のエラー

```bash
pip install --upgrade -r requirements.txt
```

## ライセンス

Private use only - 個人利用のみ

## サポート

質問や問題がある場合は、GitHubのIssuesに投稿してください。
