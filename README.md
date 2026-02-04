# Ecliptic - Planetary Alignment Finder

惑星の直列（アライメント）を検出する Python ツールです。NASA JPL の Horizons API を使用して、指定期間内で複数の惑星が黄道面上で近接する期間を探します。

## 概要

このプロジェクトは、地球から見た複数の惑星が黄道面上で一定の角度範囲内に収まる期間を検出します。2 つの実装が含まれています：

- **eclipse.py**: 日付を順次スキャンしてアライメントを検出する実装
- **eclipse2.py**: 軌道要素と平均運動を用いて候補日を事前計算し、効率的に検証する実装

## 機能

- 複数の惑星（水星、金星、火星、木星、土星、天王星、海王星）の黄道経度を取得
- 指定期間内で惑星が一定角度範囲内に収まる期間を検出
- 連続する日付を自動的に期間として統合
- NASA JPL Horizons API を使用した高精度な天文データ取得

## 必要な環境

- Python 3.7 以上
- `requests` ライブラリ

## インストール

```bash
pip install requests
```

## 使用方法

### eclipse.py

日付を順次スキャンしてアライメントを検出します：

```bash
python eclipse.py
```

デフォルトでは 2026 年 1 月 1 日から 2028 年 12 月 31 日の期間で、7 つの惑星（地球を除く）が 10 度以内に収まる期間を検索します。

コード内で以下のパラメータを変更できます：

```python
start_day = date(2026, 1, 1)      # 開始日
end_day = date(2028, 12, 31)      # 終了日
planets = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"]
span_threshold_deg = 10.0          # アライメント判定の角度閾値（度）
```

### eclipse2.py

軌道要素を用いた最適化版：

```bash
python eclipse2.py
```

この実装は、平均運動の計算により候補日を事前に生成し、その候補日のみを検証することで効率的にアライメントを検出します。

## 出力例

```
Found 3 alignment interval(s) where span <= 10.0°
2026-05-15 〜 2026-05-17  span<= 8.45°
2027-03-22  span<= 9.12°
2028-11-10 〜 2028-11-12  span<= 7.89°
```

## 主要な関数

### eclipse.py

- `fetch_geocentric_ecliptic_longitude(body_id, day, session)`: 指定日の惑星の黄道経度を取得
- `list_planetary_alignments(start_day, end_day, planets, span_threshold_deg)`: 指定期間内のアライメント期間をリスト化
- `_circular_span_deg(angles_deg)`: 円周上の角度の最小スパンを計算

### eclipse2.py

- `fetch_elements(body_id, epoch_dt, sess)`: 軌道要素を取得
- `mean_motion(a_km)`: 平均運動を計算
- `mean_longitude(el)`: 平均黄経を計算
- `fetch_lon(body_id, jd, sess)`: ユリウス日での黄道経度を取得

## 注意事項

- NASA Horizons API へのアクセスにはインターネット接続が必要です
- API の利用制限に注意してください（過度なリクエストは避けてください）
- `eclipse.py`は期間が長い場合、処理に時間がかかる可能性があります
- `eclipse2.py`はより効率的ですが、実装がやや複雑です

## ライセンス

このプロジェクトのライセンス情報は含まれていません。使用する際は適切なライセンスを追加してください。

## 参考

- [NASA JPL Horizons API](https://ssd.jpl.nasa.gov/api/horizons.api)
- [Horizons Documentation](https://ssd.jpl.nasa.gov/horizons/manual.html)
