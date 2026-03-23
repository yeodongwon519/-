"""
BTC/USDT 5분봉 차트 캡처
- RSI, EMA 지표 포함
- 1080p (1920x1080) 출력
- 사용법: python chart_capture.py --date "2024-01-15 09:00" --bars 200
"""

import argparse
import ccxt
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates
from datetime import datetime, timezone
import numpy as np

# ──────────────────────────────────────────────
# 지표 계산
# ──────────────────────────────────────────────

def calc_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


# ──────────────────────────────────────────────
# 데이터 수집
# ──────────────────────────────────────────────

def fetch_ohlcv(target_dt: datetime, bars: int = 200) -> pd.DataFrame:
    try:
        exchange = ccxt.binance({'enableRateLimit': True})
        since_ms = int(target_dt.timestamp() * 1000) - bars * 5 * 60 * 1000
        raw = exchange.fetch_ohlcv('BTC/USDT', '5m', since=since_ms, limit=bars)
        df = pd.DataFrame(raw, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
        df['dt'] = pd.to_datetime(df['ts'], unit='ms', utc=True).dt.tz_localize(None)
        df.set_index('dt', inplace=True)
        return df
    except Exception as e:
        print(f"[경고] 네트워크 오류: {e}\n→ 샘플 데이터로 렌더링합니다.")
        return _mock_ohlcv(target_dt, bars)


def _mock_ohlcv(target_dt: datetime, bars: int) -> pd.DataFrame:
    """네트워크 없이 테스트용 BTC 스타일 OHLCV 생성"""
    rng = np.random.default_rng(42)
    start = target_dt.replace(tzinfo=None) - pd.Timedelta(minutes=5 * bars)
    timestamps = pd.date_range(start, periods=bars, freq='5min')

    price = 42000.0
    rows = []
    for _ in timestamps:
        change = rng.normal(0, 80)
        open_  = price
        close  = price + change
        high   = max(open_, close) + abs(rng.normal(0, 40))
        low    = min(open_, close) - abs(rng.normal(0, 40))
        volume = rng.uniform(5, 50)
        rows.append([open_, high, low, close, volume])
        price = close

    df = pd.DataFrame(rows, index=timestamps,
                      columns=['open', 'high', 'low', 'close', 'volume'])
    return df


# ──────────────────────────────────────────────
# 차트 렌더링
# ──────────────────────────────────────────────

def draw_candles(ax, df: pd.DataFrame):
    """수동 캔들스틱 렌더링 (mplfinance 대신 직접 그려 레이아웃 자유도 확보)"""
    width_days = 5 * 60 / 86400 * 0.8  # 5분봉 너비(days 단위)

    for _, row in df.iterrows():
        color = '#26a69a' if row['close'] >= row['open'] else '#ef5350'
        # 몸통
        body_bottom = min(row['open'], row['close'])
        body_height = abs(row['close'] - row['open'])
        rect = Rectangle(
            (mdates.date2num(_.to_pydatetime()) - width_days / 2, body_bottom),
            width_days, body_height,
            facecolor=color, edgecolor=color, linewidth=0.5
        )
        ax.add_patch(rect)
        # 심지
        ax.plot(
            [mdates.date2num(_.to_pydatetime()), mdates.date2num(_.to_pydatetime())],
            [row['low'], row['high']],
            color=color, linewidth=0.8
        )


def render_chart(df: pd.DataFrame, target_dt: datetime, output_path: str):
    # 지표 계산
    df['ema9']  = calc_ema(df['close'], 9)
    df['ema21'] = calc_ema(df['close'], 21)
    df['ema50'] = calc_ema(df['close'], 50)
    df['rsi']   = calc_rsi(df['close'], 14)

    # ── 레이아웃: 차트 70% / RSI 30% ──
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100)   # 1920×1080
    fig.patch.set_facecolor('#131722')

    gs = gridspec.GridSpec(2, 1, figure=fig, height_ratios=[7, 3], hspace=0.04)
    ax_price = fig.add_subplot(gs[0])
    ax_rsi   = fig.add_subplot(gs[1], sharex=ax_price)

    for ax in (ax_price, ax_rsi):
        ax.set_facecolor('#131722')
        ax.tick_params(colors='#787b86', labelsize=9)
        ax.spines[:].set_color('#2a2e39')

    # ── 캔들 ──
    draw_candles(ax_price, df)

    # ── EMA ──
    x = [mdates.date2num(i.to_pydatetime()) for i in df.index]
    ax_price.plot(x, df['ema9'],  color='#f6c90e', linewidth=1.2, label='EMA 9')
    ax_price.plot(x, df['ema21'], color='#26a69a', linewidth=1.2, label='EMA 21')
    ax_price.plot(x, df['ema50'], color='#ff6b6b', linewidth=1.2, label='EMA 50')

    # ── 가격 범위 자동 조정 ──
    pad = (df['high'].max() - df['low'].min()) * 0.05
    ax_price.set_ylim(df['low'].min() - pad, df['high'].max() + pad)
    ax_price.yaxis.set_label_position('right')
    ax_price.yaxis.tick_right()
    ax_price.legend(loc='upper left', facecolor='#1e222d', edgecolor='#2a2e39',
                    labelcolor='#d1d4dc', fontsize=9)

    # 타이틀
    ax_price.set_title(
        f'BTC/USDT  ·  5m  ·  {target_dt.strftime("%Y-%m-%d %H:%M")} UTC',
        color='#d1d4dc', fontsize=13, loc='left', pad=10
    )

    # ── RSI ──
    ax_rsi.plot(x, df['rsi'], color='#9c27b0', linewidth=1.2, label='RSI 14')
    ax_rsi.axhline(70, color='#ef5350', linewidth=0.8, linestyle='--', alpha=0.7)
    ax_rsi.axhline(30, color='#26a69a', linewidth=0.8, linestyle='--', alpha=0.7)
    ax_rsi.fill_between(x, df['rsi'], 70,
                        where=(df['rsi'] >= 70), alpha=0.15, color='#ef5350')
    ax_rsi.fill_between(x, df['rsi'], 30,
                        where=(df['rsi'] <= 30), alpha=0.15, color='#26a69a')
    ax_rsi.set_ylim(0, 100)
    ax_rsi.yaxis.set_label_position('right')
    ax_rsi.yaxis.tick_right()
    ax_rsi.set_yticks([30, 70])
    ax_rsi.legend(loc='upper left', facecolor='#1e222d', edgecolor='#2a2e39',
                  labelcolor='#d1d4dc', fontsize=9)

    # ── X축 날짜 포맷 ──
    ax_rsi.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.setp(ax_rsi.xaxis.get_majorticklabels(), rotation=30, ha='right', color='#787b86')
    plt.setp(ax_price.xaxis.get_majorticklabels(), visible=False)

    fig.subplots_adjust(left=0.04, right=0.93, top=0.95, bottom=0.08)
    plt.savefig(output_path, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"저장 완료 → {output_path}")


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='BTC/USDT 5분봉 차트 캡처')
    parser.add_argument(
        '--date', type=str, default='2024-01-15 09:00',
        help='기준 날짜/시간 (UTC, 예: "2024-01-15 09:00")'
    )
    parser.add_argument(
        '--bars', type=int, default=200,
        help='표시할 봉 개수 (기본: 200)'
    )
    parser.add_argument(
        '--output', type=str, default='chart.png',
        help='출력 파일명 (기본: chart.png)'
    )
    args = parser.parse_args()

    target_dt = datetime.strptime(args.date, '%Y-%m-%d %H:%M')
    target_dt = target_dt.replace(tzinfo=timezone.utc)

    print(f"데이터 수집 중... ({args.date} UTC, {args.bars}봉)")
    df = fetch_ohlcv(target_dt, args.bars)
    print(f"수집 완료: {len(df)}개 봉")

    render_chart(df, target_dt, args.output)


if __name__ == '__main__':
    main()
