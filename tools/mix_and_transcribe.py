"""
複数デバイス録音の最適活用スクリプト
================================
[手順]
1. 2音声ファイルをロード
2. クロス相関で時間オフセットを自動検出・位置合わせ
3. ミックス（平均化）して単一の高品質音声を生成
4. Whisperで1回だけ文字起こし（精度向上）

[なぜこの方法が優れているか]
- テキストマージより音声ミックスの方が情報が多い
- 片方が無音でも片方が声を拾っていれば補完される
- SNR改善でハルシネーション（幻覚繰り返し）が減る
- 文字起こしは1回で済む
"""

import os
import sys
import json
import re
import numpy as np
import wave
import struct
import subprocess

# ffmpegのパスを明示的に設定
FFMPEG_PATH = r"C:\Users\shuhe\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin"
FFMPEG_EXE = os.path.join(FFMPEG_PATH, "ffmpeg.exe")
os.environ["PATH"] = FFMPEG_PATH + os.pathsep + os.environ.get("PATH", "")

BASE_DIR = r"c:\Users\shuhe\Documents\01_personal"
AUDIO_DIR = os.path.join(BASE_DIR, "docs", "meetings", "audio")
OUTPUT_DIR = os.path.join(BASE_DIR, "docs", "meetings")

AUDIO_A = os.path.join(AUDIO_DIR, "20230907-092414.WAV")
AUDIO_B = os.path.join(AUDIO_DIR, "標準録音 2.mp3")
MIXED_WAV = os.path.join(AUDIO_DIR, "mixed_aligned.wav")
TRANSCRIPT_OUT = os.path.join(BASE_DIR, "docs", "meetings", "transcripts", "transcript_mixed.txt")
TRANSCRIPT_JSON = os.path.join(BASE_DIR, "docs", "meetings", "transcripts", "transcript_mixed.json")

TARGET_SR = 16000  # Whisperの推奨サンプリングレート

# ============================================================
# ドメイン固有語彙プロンプト
# ============================================================
INITIAL_PROMPT = """
これはFIRE（経済的自立・早期退職）シミュレーターのUIレビュー会議です。

【プロダクト固有用語】
FIRE（ファイヤー）、セミFIRE、NISA（ニーサ）、iDeCo（イデコ）、
SWR（Safe Withdrawal Rate、安全引き出し率）、
モンテカルロシミュレーション、ガードレール戦略、
取り崩し戦略、ブートストラップ法、正規分布、平均回帰、
パーセンタイル、インフレ率、生活費上昇率、

【UI関連用語】
ライフステージ、シニア、後期高齢者、前期高齢者、
配偶者、育休（育児休業）、産休（産前産後休業）、産休育休、
時短勤務、フリーランス、自営業、専業主婦、
年収上昇率、退職年齢、年金受給額、
住宅ローン、固定金利、変動金利、固定資産税、
教育費、保育料、児童手当、
KPI、ツールチップ、スライダー、タブ、アコーディオン、トグル、

【計算・金融用語】
期待リターン、リスク（標準偏差）、
取り崩し、資産配分、株式、現金預金、
社会保険料、確定申告、所得控除、
必要資産額、FIRE達成年齢、FIRE成功確率、
生活費モード、固定費、ライフステージ連動、

参加者：修平（開発者）、レビュアー
"""

# ============================================================
# 事後補正辞書
# ============================================================
CORRECTION_RULES = [
    (r"本手カル[ロら]", "モンテカルロ"),
    (r"モンテカルラ", "モンテカルロ"),
    (r"[Ss][Vv][Rr]", "SWR"),
    (r"非定[率理]", "非定率"),
    (r"年金持久額", "年金受給額"),
    (r"一節三角", "年間定額"),
    (r"ファイヤーゴ[のな]", "FIRE後の"),
    (r"ファイヤーした", "FIREした"),
    (r"ファイヤー", "FIRE"),
    (r"KPA", "KPI"),
    (r"決算結果", "計算結果"),
    (r"生活非常省率", "生活費上昇率"),
    (r"セミファイヤー", "セミFIRE"),
    (r"ブーストラ[ップ]?", "ブートストラップ"),
    (r"反感を変われない", "反感を買われない"),
    (r"戦回|線回|試乗試乗試乗", "シナリオ"),
    (r"ニーサ", "NISA"),
    (r"イデコ", "iDeCo"),
]


def apply_corrections(text: str) -> str:
    for pattern, replacement in CORRECTION_RULES:
        text = re.sub(pattern, replacement, text)
    return text


# ============================================================
# Step 1: MP3/WAVをffmpegで16kHz mono WAVに変換
# ============================================================
def convert_to_wav(input_path: str, output_path: str, sr: int = TARGET_SR) -> str:
    print(f"  変換中: {os.path.basename(input_path)} → {os.path.basename(output_path)}")
    cmd = [
        FFMPEG_EXE, "-y",
        "-i", input_path,
        "-ar", str(sr),
        "-ac", "1",           # モノラル
        "-sample_fmt", "s16", # 16bit PCM
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  エラー: {result.stderr[-500:]}")
        raise RuntimeError(f"ffmpeg変換失敗: {input_path}")
    return output_path


def read_wav_as_float(path: str) -> tuple[np.ndarray, int]:
    """WAVファイルをfloat32配列として読み込む"""
    with wave.open(path, 'r') as wf:
        sr = wf.getframerate()
        n_frames = wf.getnframes()
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        raw = wf.readframes(n_frames)

    if sample_width == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_width == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"非対応サンプル幅: {sample_width}")

    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1)

    return samples, sr


def write_wav(path: str, samples: np.ndarray, sr: int):
    """float32配列をWAVファイルに書き込む"""
    pcm = (samples * 32767).clip(-32768, 32767).astype(np.int16)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


# ============================================================
# Step 2: クロス相関による時間オフセット検出
# ============================================================
def find_offset(audio_a: np.ndarray, audio_b: np.ndarray, sr: int,
                search_window_sec: float = 30.0) -> int:
    """
    クロス相関でaudioBがaudioAに対して何サンプル遅れているか検出。
    search_window_sec: 最大探索範囲（秒）。録音開始タイミングのズレを想定。
    """
    print(f"  クロス相関でオフセット検出中 (探索範囲 ±{search_window_sec}秒)...")
    window = int(search_window_sec * sr)

    # 先頭部分だけで相関を計算（全体だと重い）
    len_for_corr = min(len(audio_a), len(audio_b), sr * 120)  # 最大2分
    a_chunk = audio_a[:len_for_corr]
    b_chunk = audio_b[:len_for_corr]

    # FFTベースの高速クロス相関
    n = len(a_chunk) + len(b_chunk) - 1
    n_fft = 1 << (n - 1).bit_length()  # 2の累乗に切り上げ

    A = np.fft.rfft(a_chunk, n=n_fft)
    B = np.fft.rfft(b_chunk, n=n_fft)
    corr = np.fft.irfft(A * np.conj(B), n=n_fft)

    # 探索範囲を制限
    search_corr = np.concatenate([corr[-window:], corr[:window+1]])
    peak_idx = np.argmax(np.abs(search_corr))
    offset = peak_idx - window  # 正: B が遅い、負: B が早い

    offset_sec = offset / sr
    print(f"  検出オフセット: {offset_sec:+.2f}秒 ({offset:+d}サンプル)")
    print(f"  → {'device_B が device_A より' if offset > 0 else 'device_A が device_B より'} "
          f"{abs(offset_sec):.2f}秒遅い")
    return offset


# ============================================================
# Step 3: 位置合わせしてミックス
# ============================================================
def align_and_mix(audio_a: np.ndarray, audio_b: np.ndarray,
                  offset: int, sr: int) -> np.ndarray:
    """
    オフセットを考慮して2音声を位置合わせし、平均ミックスする。
    片方が終わった後も、もう片方が残っていれば保持。
    """
    if offset >= 0:
        # B が遅い: Aの先頭にゼロパディングせず、Bをずらす
        b_shifted = np.concatenate([np.zeros(offset, dtype=np.float32), audio_b])
    else:
        # B が早い: Aをずらす
        audio_a = np.concatenate([np.zeros(-offset, dtype=np.float32), audio_a])
        b_shifted = audio_b

    # 長い方に合わせる
    max_len = max(len(audio_a), len(b_shifted))
    a_padded = np.pad(audio_a, (0, max_len - len(audio_a)))
    b_padded = np.pad(b_shifted, (0, max_len - len(b_shifted)))

    # 両方に音声がある区間は平均、片方だけの区間はそのまま
    # 単純平均でSNRが改善される（無相関ノイズは1/√2に）
    mixed = (a_padded + b_padded) / 2.0

    # 正規化（クリッピング防止）
    max_val = np.abs(mixed).max()
    if max_val > 0.95:
        mixed = mixed * (0.95 / max_val)

    duration = len(mixed) / sr
    print(f"  ミックス完了: {duration/60:.1f}分 ({len(mixed):,}サンプル)")
    return mixed


# ============================================================
# Step 4: Whisperで文字起こし
# ============================================================
def transcribe(audio_path: str, model) -> dict:
    import whisper as _whisper
    print(f"\n  文字起こし開始: {os.path.basename(audio_path)}")
    result = model.transcribe(
        audio_path,
        language="ja",
        task="transcribe",
        verbose=True,
        initial_prompt=INITIAL_PROMPT,
        no_speech_threshold=0.6,
        condition_on_previous_text=True,
        temperature=0.0,
        compression_ratio_threshold=2.4,
        logprob_threshold=-1.0,
    )
    return result


def save_transcript(result: dict, txt_path: str, json_path: str):
    def fmt_time(sec):
        m = int(sec // 60)
        s = int(sec % 60)
        return f"{m:02d}:{s:02d}"

    # 事後補正
    for seg in result["segments"]:
        seg["text"] = apply_corrections(seg["text"])
    result["text"] = apply_corrections(result["text"])

    # テキスト保存
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("# 会議文字起こし（2デバイスミックス版）\n\n")
        f.write("**日付**: 2023-09-07\n")
        f.write("**内容**: FIREシミュレーターUIレビュー会議\n")
        f.write("**手法**: 2デバイス音声をクロス相関でアライメント後にミックスして文字起こし\n\n")
        f.write("---\n\n")

        prev_end = 0
        for seg in result["segments"]:
            text = seg["text"].strip()
            if not text:
                continue
            start = seg["start"]
            # 30秒以上の空白は区切りを入れる
            if start - prev_end > 30:
                f.write("\n---\n\n")
            f.write(f"[{fmt_time(start)}] {text}\n")
            prev_end = seg["end"]

    # JSON保存
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  テキスト保存: {txt_path}")
    print(f"  JSON保存:     {json_path}")


# ============================================================
# メイン処理
# ============================================================
def main():
    skip_mix = "--skip-mix" in sys.argv  # 既にミックス済みなら文字起こしだけ

    if not skip_mix:
        print("=" * 60)
        print("Step 1: 音声ファイルをWAV変換中...")
        print("=" * 60)
        tmp_a = os.path.join(OUTPUT_DIR, "_tmp_a.wav")
        tmp_b = os.path.join(OUTPUT_DIR, "_tmp_b.wav")

        convert_to_wav(AUDIO_A, tmp_a)
        convert_to_wav(AUDIO_B, tmp_b)

        print("\n" + "=" * 60)
        print("Step 2: 音声読み込み...")
        print("=" * 60)
        audio_a, sr = read_wav_as_float(tmp_a)
        audio_b, _  = read_wav_as_float(tmp_b)
        print(f"  device_A: {len(audio_a)/sr/60:.1f}分")
        print(f"  device_B: {len(audio_b)/sr/60:.1f}分")

        print("\n" + "=" * 60)
        print("Step 3: クロス相関でアライメント...")
        print("=" * 60)
        offset = find_offset(audio_a, audio_b, sr)

        print("\n" + "=" * 60)
        print("Step 4: ミックス...")
        print("=" * 60)
        mixed = align_and_mix(audio_a, audio_b, offset, sr)
        write_wav(MIXED_WAV, mixed, sr)
        print(f"  ミックス音声保存: {MIXED_WAV}")

        # 一時ファイル削除
        os.remove(tmp_a)
        os.remove(tmp_b)
    else:
        print("--skip-mix: ミックス済みファイルを使用します")
        if not os.path.exists(MIXED_WAV):
            print(f"エラー: {MIXED_WAV} が見つかりません")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("Step 5: Whisperで文字起こし...")
    print("=" * 60)
    import whisper
    print(f"モデル (turbo) ロード中...")
    model = whisper.load_model("turbo")
    print("ロード完了")

    result = transcribe(MIXED_WAV, model)
    save_transcript(result, TRANSCRIPT_OUT, TRANSCRIPT_JSON)

    print("\n" + "=" * 60)
    print("完了!")
    print("=" * 60)
    print(f"  文字起こし: {TRANSCRIPT_OUT}")


if __name__ == "__main__":
    main()
