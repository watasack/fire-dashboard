"""
データローダーモジュール
CSVファイルの読み込みとエンコーディング処理を担当
"""

import pandas as pd
import chardet
from pathlib import Path
from glob import glob
from typing import Dict, Any


def detect_encoding(file_path: str) -> str:
    """
    ファイルのエンコーディングを自動検出

    Args:
        file_path: ファイルパス

    Returns:
        検出されたエンコーディング名
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)  # 最初の10KBで判定
            result = chardet.detect(raw_data)
            encoding = result['encoding']

            # よくあるエンコーディングにマッピング
            if encoding and encoding.lower() in ['shift_jis', 'shift-jis']:
                return 'shift_jis'
            elif encoding and 'cp932' in encoding.lower():
                return 'cp932'

            return encoding if encoding else 'cp932'

    except Exception:
        return 'cp932'


def load_asset_data(config: Dict[str, Any]) -> pd.DataFrame:
    """
    資産推移月次データの読み込み

    Args:
        config: 設定辞書

    Returns:
        資産推移データフレーム
    """
    file_path = config['data']['asset_file']

    # エンコーディング検出
    encoding = config['data'].get('encoding', 'cp932')

    # CSVファイル読み込み（フォールバック付き）
    encodings_to_try = [encoding, 'cp932', 'shift_jis', 'utf-8']

    for enc in encodings_to_try:
        try:
            df = pd.read_csv(
                file_path,
                encoding=enc,
                parse_dates=[0],  # 1列目（日付）を日付型に変換
                on_bad_lines='skip'
            )

            # カラム名を標準化（最初の行がヘッダー）
            # MoneyForward CSV形式: 日付, 総計(円), 現金・預金・債券等(円), 投資信託(円)
            if len(df.columns) >= 4:
                df.columns = ['date', 'total_assets', 'cash_deposits', 'investment_trusts']

                # データ型変換
                for col in ['total_assets', 'cash_deposits', 'investment_trusts']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

                # 日付でソート
                df = df.sort_values('date')
                df = df.reset_index(drop=True)

                return df
            else:
                return df

        except Exception:
            continue

    raise ValueError(f"Failed to load {file_path} with any encoding")


def load_transaction_data(config: Dict[str, Any]) -> pd.DataFrame:
    """
    収入・支出詳細データの読み込み（複数ファイル対応）

    Args:
        config: 設定辞書

    Returns:
        収支詳細データフレーム
    """
    pattern = config['data']['transaction_pattern']

    # globパターンでファイル検索
    file_paths = glob(pattern)

    if not file_paths:
        raise FileNotFoundError(f"No files found matching pattern: {pattern}")

    # すべてのファイルを読み込んで結合
    dfs = []
    encoding = config['data'].get('encoding', 'cp932')
    encodings_to_try = [encoding, 'cp932', 'shift_jis', 'utf-8']

    for file_path in file_paths:
        for enc in encodings_to_try:
            try:
                df = pd.read_csv(
                    file_path,
                    encoding=enc,
                    parse_dates=[1],  # 2列目（日付）を日付型に変換
                    on_bad_lines='skip'
                )

                # カラム名を標準化
                if len(df.columns) >= 10:
                    df.columns = [
                        'is_expense',      # 0: 収入, 1: 支出
                        'date',
                        'description',
                        'amount',
                        'account',
                        'category_major',
                        'category_minor',
                        'memo',
                        'is_transfer',     # 振替フラグ
                        'id'
                    ]

                    # データ型変換
                    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                    df['is_expense'] = pd.to_numeric(df['is_expense'], errors='coerce').fillna(1).astype(int)
                    df['is_transfer'] = pd.to_numeric(df['is_transfer'], errors='coerce').fillna(0).astype(int)

                    dfs.append(df)
                    break
                else:
                    dfs.append(df)
                    break

            except Exception:
                if enc == encodings_to_try[-1]:  # 最後のエンコーディングでも失敗
                    pass
                continue

    if not dfs:
        raise ValueError("Failed to load any transaction files")

    # すべてのデータフレームを結合
    combined_df = pd.concat(dfs, ignore_index=True)

    # 日付でソート
    combined_df = combined_df.sort_values('date')
    combined_df = combined_df.reset_index(drop=True)

    return combined_df
