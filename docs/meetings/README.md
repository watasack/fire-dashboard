# 会議録音 文字起こし 手順書

## フォルダ構成

```
docs/meetings/
  audio/
    20230907-092414.WAV     元録音（デバイスA）
    標準録音 2.mp3           元録音（デバイスB）
    mixed_aligned.wav       アライメント済みミックス音声（Step 2 の出力）
  transcripts/
    transcript_mixed.txt    文字起こし結果（タイムスタンプ付き）
    transcript_mixed.json   文字起こし結果（構造化データ）
  meeting_transcript.md     会議サマリー（セクション別整理）
  task_list.md              タスクリスト
  implementation_plan.md    実装計画
  README.md                 本ファイル

tools/
  transcribe.py             文字起こしスクリプト（メイン）
  mix_and_transcribe.py     2デバイス音声のミックススクリプト
```

---

## 事前準備（初回のみ）

### 必要ライブラリのインストール

```bash
pip install faster-whisper torch silero-vad numpy scipy
```

### ffmpeg

WinGet でインストール済みであること。パスが通っていない場合は
`tools/transcribe.py` と `tools/mix_and_transcribe.py` の `FFMPEG_PATH` を環境に合わせて更新する。

---

## 手順

### Step 1: 音声ファイルの配置

録音ファイルを `docs/meetings/audio/` に置く。

ファイル名を変更した場合は `tools/mix_and_transcribe.py` の `AUDIO_A` / `AUDIO_B` と
`tools/transcribe.py` の `AUDIO_FILES` を合わせて更新する。

### Step 2: 2音声のミックス

2台のデバイスで録音した音声をクロス相関でアライメントし、混合する。
SNR が改善されハルシネーション（繰り返し出力）が減少する。

```bash
python -X utf8 tools/mix_and_transcribe.py
```

出力: `docs/meetings/audio/mixed_aligned.wav`

> 1デバイスのみの場合はこの手順を飛ばし、Step 3 で `device_A` を指定する。

### Step 3: 文字起こし

Silero VAD で音声区間のみ抽出したうえで faster-whisper large-v3 で文字起こしする。

```bash
# ミックス音声（2デバイスの場合・推奨）
python -X utf8 tools/transcribe.py mixed

# 単独デバイスの場合
python -X utf8 tools/transcribe.py device_A
```

出力:
- `docs/meetings/transcripts/transcript_mixed.txt`
- `docs/meetings/transcripts/transcript_mixed.json`

所要時間の目安: 52分音声で 20〜30分（CPU環境）

### Step 4: 品質確認

ハルシネーション（同一文の連続繰り返し）が残っていないか確認する。

```bash
python -X utf8 -c "
lines = open('docs/meetings/transcripts/transcript_mixed.txt', encoding='utf-8').readlines()
dups = [(i, lines[i].strip()[:60]) for i in range(1, len(lines))
        if lines[i].strip() and lines[i] == lines[i-1]]
if dups:
    for i, t in dups: print(f'重複 line {i}: {t}')
else:
    print('問題なし')
"
```

誤認識が多い単語は `tools/transcribe.py` の `CORRECTION_RULES` に正規表現パターンを追加する。

### Step 5: 会議サマリー・タスクリストの生成

`transcripts/transcript_mixed.txt` を読み込み、以下を生成・更新する。

| ファイル | 内容 |
|---|---|
| `meeting_transcript.md` | セクション別の議論サマリー |
| `task_list.md` | バグ修正・UX改善・優先度別タスク一覧 |
| `implementation_plan.md` | フェーズ別実装計画 |

Claude Code でこのフォルダを開いている場合は `/meeting-transcribe` スラッシュコマンドで
Step 1〜5 の手順を参照できる。

---

## トラブルシューティング

### ハルシネーションループが発生する（同一文が100回以上繰り返される）

`tools/transcribe.py` の以下パラメータを確認する。

```python
condition_on_previous_text=False   # ← これが True になっていると高確率で発生
compression_ratio_threshold=1.35   # ← デフォルト(2.4)では検出が遅すぎる
```

### 2デバイスの同期ずれが大きい（60秒以上）

`mix_and_transcribe.py` はクロス相関で自動補正するが、オフセットが極端に大きい場合は
ffmpeg で片方を手動トリミングしてから実行する。

```bash
# 例: デバイスBの先頭30秒をカット
ffmpeg -i "docs/meetings/audio/標準録音 2.mp3" -ss 30 -c copy "docs/meetings/audio/標準録音 2_trimmed.mp3"
```

### 重複セグメントが残る（ミックス音声）

`tools/transcribe.py` の `dedup_segments()` の閾値を調整する。

```python
dedup_segments(segs, sim_threshold=0.7, time_window=5.0)  # デフォルト: 0.8
```

### 処理速度を上げたい

`tools/transcribe.py` のモデルを変更する（精度は低下する）。

```python
MODEL_SIZE = "medium"   # デフォルト: "large-v3"
```
