"""
탈개미 시그널 승률 백테스트
- 바이비트 BTC/USDT 1H 데이터 기준
- RSI + 거래량 폭발 역추세 시그널 검증

실행: python signal_winrate.py
필요: pip install ccxt pandas
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime

# ── 설정 ──────────────────────────────────────────────────
SYMBOL = "BTC/USDT"
TIMEFRAME = "1h"
START_DATE = "2022-01-01T00:00:00Z"

# 청산 조건
TAKE_PROFIT_PCT = 0.02   # +2% 목표
STOP_LOSS_PCT   = 0.05   # -5% 손절
MAX_HOLD_CANDLES = 72    # 최대 보유 72시간 (3일)


# ── 데이터 수집 ────────────────────────────────────────────
def fetch_ohlcv(symbol, timeframe, start_date):
    exchange = ccxt.bybit()
    since = exchange.parse8601(start_date)
    all_data = []

    print("📥 데이터 수집 중...")
    while True:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
        if not ohlcv:
            break
        all_data.extend(ohlcv)
        since = ohlcv[-1][0] + 1
        if len(ohlcv) < 1000:
            break

    df = pd.DataFrame(all_data, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
    df = df.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    print(f"✅ {len(df)}개 캔들 수집 ({df['ts'].iloc[0].date()} ~ {df['ts'].iloc[-1].date()})")
    return df


# ── 지표 계산 ──────────────────────────────────────────────
def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def add_signals(df):
    df = df.copy()
    df["rsi"] = calc_rsi(df["close"], 14)
    df["vol_ma"] = df["volume"].rolling(20).mean()
    df["vol_mult"] = df["volume"] / df["vol_ma"]

    # 롱 시그널 (Pine Script 동일)
    df["long_1"] = (df["rsi"] <= 30) & (df["vol_mult"] >= 1.5) & (df["vol_mult"] < 2.5)
    df["long_2"] = (df["rsi"] <= 25) & (df["vol_mult"] >= 2.5) & (df["vol_mult"] < 4)
    df["long_3"] = (df["rsi"] <= 25) & (df["vol_mult"] >= 4)
    df["long_4"] = (df["rsi"] <= 20) & (df["vol_mult"] >= 5)

    # 숏 시그널
    df["short_1"] = (df["rsi"] >= 70) & (df["vol_mult"] >= 1.5) & (df["vol_mult"] < 2)
    df["short_2"] = (df["rsi"] >= 75) & (df["vol_mult"] >= 2.5) & (df["vol_mult"] < 3)
    df["short_3"] = (df["rsi"] >= 75) & (df["vol_mult"] >= 4)
    df["short_4"] = (df["rsi"] >= 80) & (df["vol_mult"] >= 5)

    # 강도 분류
    df["long_strength1"]  = df["long_1"] | df["long_2"]
    df["long_strength2"]  = df["long_3"] | df["long_4"]
    df["short_strength1"] = df["short_1"] | df["short_2"]
    df["short_strength2"] = df["short_3"] | df["short_4"]

    return df


# ── 백테스트 ───────────────────────────────────────────────
def backtest_signal(df, signal_col, direction="long"):
    """
    신호 발생 후 MAX_HOLD_CANDLES 이내에:
      - TP 도달 → WIN
      - SL 도달 → LOSS
      - 시간 초과 → 종가 기준 손익
    """
    results = []
    signal_rows = df[df[signal_col]].index.tolist()

    for idx in signal_rows:
        entry_price = df.loc[idx, "close"]
        tp = entry_price * (1 + TAKE_PROFIT_PCT) if direction == "long" else entry_price * (1 - TAKE_PROFIT_PCT)
        sl = entry_price * (1 - STOP_LOSS_PCT)   if direction == "long" else entry_price * (1 + STOP_LOSS_PCT)

        outcome = None
        exit_price = None
        hold_candles = 0

        for future_idx in range(idx + 1, min(idx + MAX_HOLD_CANDLES + 1, len(df))):
            row = df.loc[future_idx]
            hold_candles = future_idx - idx

            if direction == "long":
                if row["high"] >= tp:
                    outcome, exit_price = "WIN", tp
                    break
                if row["low"] <= sl:
                    outcome, exit_price = "LOSS", sl
                    break
            else:
                if row["low"] <= tp:
                    outcome, exit_price = "WIN", tp
                    break
                if row["high"] >= sl:
                    outcome, exit_price = "LOSS", sl
                    break

        if outcome is None:
            exit_price = df.loc[min(idx + MAX_HOLD_CANDLES, len(df) - 1), "close"]
            pnl_pct = (exit_price - entry_price) / entry_price if direction == "long" else (entry_price - exit_price) / entry_price
            outcome = "WIN" if pnl_pct > 0 else "LOSS"
            hold_candles = MAX_HOLD_CANDLES

        pnl_pct = (exit_price - entry_price) / entry_price * 100 if direction == "long" \
                  else (entry_price - exit_price) / entry_price * 100

        results.append({
            "entry_time":   df.loc[idx, "ts"],
            "entry_price":  entry_price,
            "exit_price":   exit_price,
            "pnl_pct":      round(pnl_pct, 3),
            "outcome":      outcome,
            "hold_candles": hold_candles,
            "rsi":          round(df.loc[idx, "rsi"], 1),
            "vol_mult":     round(df.loc[idx, "vol_mult"], 2),
        })

    return pd.DataFrame(results)


# ── 결과 출력 ──────────────────────────────────────────────
def print_result(label, res_df):
    if res_df.empty:
        print(f"\n[{label}] 시그널 없음")
        return

    total   = len(res_df)
    wins    = (res_df["outcome"] == "WIN").sum()
    losses  = total - wins
    win_rate = wins / total * 100
    avg_pnl  = res_df["pnl_pct"].mean()
    avg_win  = res_df[res_df["outcome"] == "WIN"]["pnl_pct"].mean()
    avg_loss = res_df[res_df["outcome"] == "LOSS"]["pnl_pct"].mean()
    total_pnl = res_df["pnl_pct"].sum()

    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"{'='*50}")
    print(f"  총 시그널 수  : {total}회")
    print(f"  승률          : {win_rate:.1f}%  ({wins}승 {losses}패)")
    print(f"  평균 손익     : {avg_pnl:+.2f}%")
    print(f"  평균 수익 (승): {avg_win:+.2f}%")
    print(f"  평균 손실 (패): {avg_loss:+.2f}%")
    print(f"  누적 손익합   : {total_pnl:+.2f}%")

    # 연도별 분포
    res_df["year"] = res_df["entry_time"].dt.year
    print(f"\n  [연도별 발생 횟수]")
    for year, grp in res_df.groupby("year"):
        wr = (grp["outcome"] == "WIN").mean() * 100
        print(f"    {year}년: {len(grp)}회, 승률 {wr:.1f}%")


# ── 메인 ──────────────────────────────────────────────────
if __name__ == "__main__":
    df = fetch_ohlcv(SYMBOL, TIMEFRAME, START_DATE)
    df = add_signals(df)

    print(f"\n⚙️  설정: TP {TAKE_PROFIT_PCT*100:.0f}% / SL {STOP_LOSS_PCT*100:.0f}% / 최대보유 {MAX_HOLD_CANDLES}H")

    # 각 시그널별 백테스트
    signals = [
        ("롱 강도1 (RSI≤30, vol 1.5~2.5x)", "long_strength1",  "long"),
        ("롱 강도2 (RSI≤25, vol 4x+)",       "long_strength2",  "long"),
        ("숏 강도1 (RSI≥70, vol 1.5~2x)",    "short_strength1", "short"),
        ("숏 강도2 (RSI≥75, vol 4x+)",       "short_strength2", "short"),
    ]

    all_results = {}
    for label, col, direction in signals:
        res = backtest_signal(df, col, direction)
        all_results[label] = res
        print_result(label, res)

    print(f"\n{'='*50}")
    print("  전체 요약")
    print(f"{'='*50}")
    long_all  = pd.concat([all_results[s[0]] for s in signals if s[2] == "long"],  ignore_index=True)
    short_all = pd.concat([all_results[s[0]] for s in signals if s[2] == "short"], ignore_index=True)

    for label, combined in [("롱 전체", long_all), ("숏 전체", short_all)]:
        if not combined.empty:
            wr = (combined["outcome"] == "WIN").mean() * 100
            avg = combined["pnl_pct"].mean()
            print(f"  {label}: {len(combined)}회, 승률 {wr:.1f}%, 평균손익 {avg:+.2f}%")

    print("\n✅ 완료")
