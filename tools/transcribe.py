"""
会議録音 文字起こし - Silero VAD + faster-whisper 版
=====================================================
特徴:
1. Silero VAD で音声区間のみ抽出 → ハルシネーション根本解決
2. faster-whisper (CTranslate2) で CPU でも 3-4x 高速化
3. initial_prompt でドメイン語彙注入
4. 事後補正辞書

使い方:
  python -X utf8 tools/transcribe.py device_A
  python -X utf8 tools/transcribe.py device_B
  python -X utf8 tools/transcribe.py both
  python -X utf8 tools/transcribe.py mixed   # mix_and_transcribe.pyで作成済みのミックス音声
"""

import os, sys, json, re, subprocess
import numpy as np

FFMPEG_PATH = r"C:\Users\shuhe\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin"
os.environ["PATH"] = FFMPEG_PATH + os.pathsep + os.environ.get("PATH", "")

BASE_DIR        = r"c:\Users\shuhe\Documents\01_personal"
AUDIO_DIR       = os.path.join(BASE_DIR, "docs", "meetings", "audio")
TRANSCRIPT_DIR  = os.path.join(BASE_DIR, "docs", "meetings", "transcripts")
OUTPUT_DIR      = os.path.join(BASE_DIR, "docs", "meetings")

AUDIO_FILES = {
    "device_A": os.path.join(AUDIO_DIR, "20230907-092414.WAV"),
    "device_B": os.path.join(AUDIO_DIR, "標準録音 2.mp3"),
    "mixed":    os.path.join(AUDIO_DIR, "mixed_aligned.wav"),
}

MODEL_SIZE = "large-v3"   # CPU でも faster-whisper なら turbo より速い

INITIAL_PROMPT = (
    "これはFIREシミュレーターのUIレビュー会議です。"
    "FIRE、セミFIRE、NISA、iDeCo、SWR、モンテカルロシミュレーション、"
    "ガードレール戦略、取り崩し戦略、ブートストラップ法、正規分布、平均回帰、"
    "パーセンタイル、インフレ率、生活費上昇率、ライフステージ、シニア、"
    "後期高齢者、前期高齢者、育休、産休、時短勤務、フリーランス、専業主婦、"
    "年収上昇率、退職年齢、年金受給額、住宅ローン、固定金利、変動金利、"
    "固定資産税、教育費、保育料、児童手当、KPI、ツールチップ、"
    "期待リターン、標準偏差、資産配分、社会保険料、必要資産額、FIRE達成年齢。"
)

CORRECTION_RULES = [
    # モンテカルロ
    (r"本手カル[ロらル]|モンテカルラ|モンテカルル", "モンテカルロ"),
    # 金融・投資用語
    (r"[Ss][Vv][Rr]",                         "SWR"),
    (r"非定[率理]",                            "非定率"),
    (r"年金[持自][久給]額",                   "年金受給額"),
    (r"ファイヤーゴ[のな]",                   "FIRE後の"),
    (r"ファイヤーした|ファイヤー",            "FIRE"),
    (r"セミファイヤー",                        "セミFIRE"),
    (r"ニーサ",                               "NISA"),
    (r"NISA[ーー]",                           "NISA"),
    (r"イデコ",                               "iDeCo"),
    (r"KPA",                                  "KPI"),
    # 生活費・UI用語
    (r"決算結果",                             "計算結果"),
    (r"生活非常[省症]率",                     "生活費上昇率"),
    (r"生活非常省率",                          "生活費上昇率"),
    # 人物・雇用形態
    (r"成長主婦|専業主義|専業収[支費]",       "専業主婦"),
    (r"応用携帯|雇用携帯",                    "雇用形態"),
    (r"デフコ|デフォー|デフォる",             "デフォルト"),
    # ブートストラップ
    (r"ブーストラ[ップ]?|ブートラップ|ブートストラ(?!ップ)", "ブートストラップ"),
    (r"平均回帰分布とストラップ",               "平均回帰、ブートストラップ"),
    # その他
    (r"反感を[変変]われない|反感変われない|半顔変われない", "反感を買われない"),
    (r"戦回|線回|試乗試乗試乗",              "シナリオ"),
    (r"一節三角",                             "年間定額"),
    (r"ブートストラ(?!ップ)\w*",             "ブートストラップ"),
    # ミックス音声で発生する誤認識
    (r"空切り",                              "区切り"),
    (r"固定印刷時",                          "固定費にした時"),
    (r"文庫外で聞きます|文庫外",             "オンオフできます"),
    (r"2万ショック",                         "リーマンショック"),
    (r"自動手当て",                          "児童手当"),
    (r"スミFIRE",                            "セミFIRE"),
]

def fix(text: str) -> str:
    for pat, rep in CORRECTION_RULES:
        text = re.sub(pat, rep, text)
    return text

def dedup_segments(segs: list[dict], sim_threshold=0.8, time_window=5.0) -> list[dict]:
    """
    ミックス音声で発生する連続重複セグメントを除去する。
    直前のセグメントと文字列類似度が sim_threshold 以上かつ
    時間差が time_window 秒以内なら重複とみなしてスキップ。
    """
    if not segs:
        return segs

    def similarity(a: str, b: str) -> float:
        a, b = a.strip(), b.strip()
        if not a or not b:
            return 0.0
        # 文字レベルの一致率（短い方を基準）
        shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
        matches = sum(1 for c in shorter if c in longer)
        return matches / max(len(shorter), 1)

    result = [segs[0]]
    for seg in segs[1:]:
        prev = result[-1]
        time_diff = seg["start"] - prev["start"]
        sim = similarity(fix(seg["text"]), fix(prev["text"]))
        if sim >= sim_threshold and time_diff <= time_window:
            continue  # 重複とみなしてスキップ
        result.append(seg)

    removed = len(segs) - len(result)
    if removed > 0:
        print(f"  重複除去: {removed} セグメント削除 ({len(result)} 残)")
    return result

def fmt(sec):
    return f"{int(sec//60):02d}:{int(sec%60):02d}"

# ──────────────────────────────────────────────
# Step 1: ffmpeg で 16kHz mono float32 WAV に変換
# ──────────────────────────────────────────────
def to_wav16k(src: str, dst: str):
    print(f"  変換: {os.path.basename(src)}")
    subprocess.run([
        os.path.join(FFMPEG_PATH, "ffmpeg.exe"), "-y",
        "-i", src, "-ar", "16000", "-ac", "1", "-sample_fmt", "s16", dst
    ], capture_output=True, check=True)

def load_wav(path: str) -> tuple[np.ndarray, int]:
    import wave
    with wave.open(path, 'r') as wf:
        sr = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    samples = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    return samples, sr

# ──────────────────────────────────────────────
# Step 2: Silero VAD で音声区間を検出
# ──────────────────────────────────────────────
def get_speech_chunks(audio: np.ndarray, sr: int,
                      min_speech_ms=300, min_silence_ms=500,
                      threshold=0.4) -> list[dict]:
    """
    Returns: [{"start": float秒, "end": float秒}, ...]
    threshold: 低いほど検出が敏感（小声も拾う）、高いほど厳格
    min_silence_ms: この長さ以上の無音を区切りとみなす
    """
    from silero_vad import load_silero_vad, get_speech_timestamps

    print("  Silero VAD モデルロード中...")
    vad_model = load_silero_vad()

    import torch
    audio_tensor = torch.from_numpy(audio)

    print(f"  音声区間検出中 (threshold={threshold})...")
    timestamps = get_speech_timestamps(
        audio_tensor,
        vad_model,
        sampling_rate=sr,
        threshold=threshold,
        min_speech_duration_ms=min_speech_ms,
        min_silence_duration_ms=min_silence_ms,
        return_seconds=True,
    )
    print(f"  → {len(timestamps)} 区間を検出")
    return timestamps

# ──────────────────────────────────────────────
# Step 3: 音声区間を結合して無音を除去
# ──────────────────────────────────────────────
def extract_speech_audio(audio: np.ndarray, sr: int,
                         chunks: list[dict],
                         padding_ms=200) -> tuple[np.ndarray, list[dict]]:
    """
    VAD区間のみ抽出して結合。
    各区間の開始・終了オフセットも記録（後で元の時刻に戻すため）。
    padding_ms: 区間の前後にパディングを追加
    """
    pad = int(padding_ms / 1000 * sr)
    segments = []
    parts = []

    cursor = 0
    for chunk in chunks:
        start_s = max(0, chunk["start"] - padding_ms / 1000)
        end_s   = min(len(audio) / sr, chunk["end"] + padding_ms / 1000)
        s = int(start_s * sr)
        e = int(end_s   * sr)

        parts.append(audio[s:e])
        segments.append({
            "original_start": chunk["start"],
            "original_end":   chunk["end"],
            "extracted_start": cursor / sr,
            "extracted_end":   (cursor + e - s) / sr,
        })
        cursor += e - s

    combined = np.concatenate(parts) if parts else np.array([], dtype=np.float32)

    total = len(audio) / sr
    speech = len(combined) / sr
    print(f"  音声区間: {speech/60:.1f}分 / 全体: {total/60:.1f}分 "
          f"({speech/total*100:.0f}%が音声)")

    return combined, segments

# ──────────────────────────────────────────────
# Step 4: faster-whisper で文字起こし
# ──────────────────────────────────────────────
def transcribe_fw(audio_path: str) -> list[dict]:
    from faster_whisper import WhisperModel

    print(f"\n  faster-whisper ({MODEL_SIZE}) ロード中...")
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    print("  ロード完了")

    segments, info = model.transcribe(
        audio_path,
        language="ja",
        initial_prompt=INITIAL_PROMPT,
        vad_filter=True,          # faster-whisper 内蔵VAD（二重フィルタ）
        vad_parameters={
            "threshold": 0.5,           # 0.4→0.5: より厳格に音声判定
            "min_speech_duration_ms": 300,
            "min_silence_duration_ms": 600,
        },
        beam_size=5,
        best_of=5,
        temperature=[0.0, 0.2, 0.4],   # 失敗時に温度を上げて再試行
        # ▼ ハルシネーションループ対策（最重要）
        condition_on_previous_text=False,   # True→False: ループの連鎖を断つ
        compression_ratio_threshold=1.35,   # 繰り返し検出を敏感に（デフォルト2.4）
        log_prob_threshold=-1.0,
        no_speech_threshold=0.7,            # 0.6→0.7: 無音判定を厳格に
        word_timestamps=False,
    )

    results = []
    for seg in segments:
        text = fix(seg.text.strip())
        if text:
            results.append({
                "start": seg.start,
                "end":   seg.end,
                "text":  text,
            })
            # リアルタイム表示
            print(f"    [{fmt(seg.start)}] {text}")

    return results

# ──────────────────────────────────────────────
# Step 5: 時刻をVAD前の元タイムラインに戻す
# ──────────────────────────────────────────────
def restore_timestamps(segs: list[dict], seg_map: list[dict]) -> list[dict]:
    """
    faster-whisperのセグメント時刻（VAD後）を元の録音時刻に変換。
    """
    if not seg_map:
        return segs

    restored = []
    for seg in segs:
        s, e = seg["start"], seg["end"]
        # どのVAD区間に属するか探す
        for m in seg_map:
            if m["extracted_start"] <= s <= m["extracted_end"]:
                offset = m["original_start"] - m["extracted_start"]
                restored.append({
                    "start": s + offset,
                    "end":   e + offset,
                    "text":  seg["text"],
                })
                break
        else:
            restored.append(seg)  # マッチしなければそのまま

    return restored

# ──────────────────────────────────────────────
# メイン
# ──────────────────────────────────────────────
def process(label: str, audio_src: str):
    print(f"\n{'='*60}")
    print(f"処理開始: {label}  ({os.path.basename(audio_src)})")
    print(f"{'='*60}")

    tmp_wav = os.path.join(OUTPUT_DIR, f"_tmp_{label}.wav")
    out_txt = os.path.join(TRANSCRIPT_DIR, f"transcript_{label}.txt")
    out_json= os.path.join(TRANSCRIPT_DIR, f"transcript_{label}.json")

    # WAV変換
    to_wav16k(audio_src, tmp_wav)

    # 音声ロード
    audio, sr = load_wav(tmp_wav)

    # VAD で音声区間検出
    chunks = get_speech_chunks(audio, sr, threshold=0.5)  # 0.4→0.5

    # 音声区間のみ抽出
    speech_audio, seg_map = extract_speech_audio(audio, sr, chunks)

    # VAD処理後の音声をWAVで保存
    speech_wav = os.path.join(OUTPUT_DIR, f"_speech_{label}.wav")
    import wave
    pcm = (speech_audio * 32767).clip(-32768, 32767).astype(np.int16)
    with wave.open(speech_wav, 'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())

    # 文字起こし
    segs = transcribe_fw(speech_wav)

    # タイムスタンプを元の録音時刻に変換
    segs = restore_timestamps(segs, seg_map)

    # 重複除去（ミックス音声の場合に有効）
    segs = dedup_segments(segs)

    # 保存
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(f"# 文字起こし ({label})\n\n")
        f.write("手法: Silero VAD + faster-whisper large-v3\n\n---\n\n")
        prev_end = 0
        for seg in segs:
            if seg["start"] - prev_end > 30:
                f.write("\n---\n\n")
            f.write(f"[{fmt(seg['start'])}] {seg['text']}\n")
            prev_end = seg["end"]

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(segs, f, ensure_ascii=False, indent=2)

    # 一時ファイル削除
    for p in [tmp_wav, speech_wav]:
        if os.path.exists(p): os.remove(p)

    print(f"\n保存完了: {out_txt}")
    return segs


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "device_A"

    if target == "both":
        process("device_A", AUDIO_FILES["device_A"])
        process("device_B", AUDIO_FILES["device_B"])
    elif target in AUDIO_FILES:
        process(target, AUDIO_FILES[target])
    else:
        print(f"不明なターゲット: {target}")
        print(f"使用可能: {list(AUDIO_FILES.keys())} または both")

if __name__ == "__main__":
    main()
