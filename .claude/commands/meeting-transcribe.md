# 会議録音 → 文字起こし → タスクリスト 一連ワークフロー

複数デバイスで録音した会議音声を文字起こしし、タスクリストと実装計画を生成する。

## 前提条件（事前確認）

以下がインストール済みであること:
- `faster-whisper` (`pip install faster-whisper`)
- `silero-vad` / `torch` (`pip install torch silero-vad`)
- `numpy`, `scipy` (`pip install numpy scipy`)
- ffmpeg（WinGetまたはchoco経由でインストール済み）

## Step 1: 音声ファイルの配置

録音ファイルを `docs/meetings/audio/` に配置する。
2デバイス分の場合はファイル名を `tools/mix_and_transcribe.py` と `tools/transcribe.py` 内の
`AUDIO_A`, `AUDIO_B`, `AUDIO_FILES` に合わせて更新（またはファイル名をスクリプトに合わせる）。

```
docs/meetings/audio/
  20230907-092414.WAV   ← デバイスA（高品質マイク等）
  標準録音 2.mp3        ← デバイスB（スマホ等）
```

## Step 2: 2音声のアライメント＆ミックス

クロス相関で時間オフセットを自動検出し、SNRを改善した混合音声を生成。

```bash
python -X utf8 tools/mix_and_transcribe.py
```

出力: `docs/meetings/audio/mixed_aligned.wav`

> **注意**: このスクリプトはWhperではなく音声ミックスのみを行う。
> v2用の文字起こしコードが残っているが無視してよい（transcribeスクリプトで文字起こしする）。

## Step 3: 文字起こし（Silero VAD + faster-whisper large-v3）

ミックス済み音声を高精度で文字起こし。

```bash
# ミックス音声（推奨）
python -X utf8 tools/transcribe.py mixed

# 各デバイス単独（デバッグ・比較用）
python -X utf8 tools/transcribe.py device_A
python -X utf8 tools/transcribe.py device_B
```

出力:
- `docs/meetings/transcripts/transcript_mixed.txt` — タイムスタンプ付き文字起こし
- `docs/meetings/transcripts/transcript_mixed.json` — 構造化データ（segments配列）

### 重要パラメータ（ハルシネーション対策）

| パラメータ | 値 | 理由 |
|---|---|---|
| `condition_on_previous_text` | `False` | 繰り返しループ防止（最重要） |
| `compression_ratio_threshold` | `1.35` | 繰り返し早期検出（デフォルト2.4は甘すぎ） |
| `no_speech_threshold` | `0.7` | 無音誤認識削減 |
| `temperature` | `[0.0, 0.2, 0.4]` | 低温優先で確定的出力 |
| VAD `threshold` | `0.5` | 音声区間のみ抽出（無音部分スキップ） |

## Step 4: 文字起こし品質確認

ハルシネーション（同一文の連続繰り返し）が残っていないか確認:

```bash
# 連続する同一行の確認
python -X utf8 -c "
lines = open('docs/meetings/transcript_mixed.txt', encoding='utf-8').readlines()
for i in range(1, len(lines)):
    if lines[i].strip() and lines[i] == lines[i-1]:
        print(f'重複 line {i}: {lines[i].strip()[:50]}')
print('確認完了')
"
```

問題があれば `tools/transcribe.py` の `CORRECTION_RULES` に正規表現パターンを追加。

## Step 5: 文字起こしから会議サマリー生成

文字起こし `docs/meetings/transcript_mixed.txt` を読み込み、
セクション別の議論内容をまとめた会議サマリー Markdown を生成。

出力先: `docs/meetings/meeting_transcript.md`

構成例:
```markdown
# 会議サマリー: UIレビュー（YYYY-MM-DD）

## 基本タブ
- 議論内容...

## 収入タブ
...
```

## Step 6: タスクリスト生成・更新

文字起こしと会議サマリーをベースに、以下の形式でタスクリストを生成・更新。

出力先: `docs/meetings/task_list.md`

タスクリストのフォーマット:
```markdown
## 🔴 バグ修正（Critical）
| # | 内容 | 場所 |
|---|---|---|
| BUG-01 | ... | タブ名 |

## 🟠 UX改善（High Priority）
### タブ名
- [ ] タスク内容

## 🟡 Medium Priority
- [ ] ...

## 🟢 Post-Launch
- [ ] ...
```

差分確認: 既存 `task_list.md` と比較し、新規タスク・完了済みタスクの変化を報告。

## Step 7: 実装計画生成

タスクリストを優先度・依存関係で整理し、実装計画 `docs/meetings/implementation_plan.md` を生成。

---

## トラブルシューティング

### ハルシネーションループが止まらない
→ `condition_on_previous_text=False` を確認。`compression_ratio_threshold` を 1.2 まで下げる。

### デバイスB（MP3）の同期ずれが大きい
→ `mix_and_transcribe.py` のクロス相関ウィンドウを確認。
  オフセットが 60 秒以上ずれる場合は手動でトリミングしてから実行。

### 重複セグメントが残る（ミックス音声）
→ `transcribe.py` の `dedup_segments()` の `sim_threshold` を 0.7 に下げる。

### `faster-whisper` が遅い
→ CPU環境では `large-v3` で 52分音声に 20〜30分かかる。
  速度優先なら `model_size = "medium"` に変更（精度は低下）。

### ffmpeg が見つからない
→ `tools/transcribe.py` の `FFMPEG_PATH` を環境に合わせて更新。
