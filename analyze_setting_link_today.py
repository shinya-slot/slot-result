import pandas as pd

import sys

from collections import defaultdict

def calc_same_day_link_rate(
    df,
    machine_col="台番号",
    date_col="日付",
    setting_col="設定",
    target_settings=(3, 4, 5, 6),
    days=45
):

    df = df.copy()

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df[setting_col] = pd.to_numeric(df[setting_col], errors="coerce")
    df[machine_col] = pd.to_numeric(df[machine_col], errors="coerce")

    df = df.dropna(subset=[date_col, machine_col, setting_col])

    max_date = df[date_col].max()
    start_date = max_date - pd.Timedelta(days=days - 1)

    df = df[
        (df[date_col] >= start_date) &
        (df[date_col] <= max_date)
    ]

    high_df = df[df[setting_col].isin(target_settings)]

    daily_high = (
        high_df.groupby(date_col)[machine_col]
        .apply(lambda x: sorted(set(x.astype(int))))
        .to_dict()
    )

    machines = sorted(df[machine_col].dropna().astype(int).unique())

    result = []

    for base in machines:

        base_days = []

        for d, high_machines in daily_high.items():
            if base in high_machines:
                base_days.append(d)

        base_count = len(base_days)

        if base_count == 0:
            continue

        link_counter = defaultdict(int)

        for d in base_days:

            high_machines = daily_high[d]

            for other in high_machines:

                if other != base:
                    link_counter[other] += 1

        for other, link_count in link_counter.items():

            rate = link_count / base_count

            result.append({
                "基準台": base,
                "連動台": other,
                "基準台高設定回数": base_count,
                "連動回数": link_count,
                "連動率": rate,
                "連動率表示": f"{link_count}/{base_count}（{rate:.0%}）"
            })

    result_df = pd.DataFrame(result)

    if result_df.empty:
        return result_df

    result_df = result_df.sort_values(
        ["基準台", "連動率", "連動回数"],
        ascending=[True, False, False]
    )

    return result_df

# =========================
# 連動率重視版 pt係数
# =========================

DAY_COEFFICIENTS = {
    1: 1.00,   # 1日前
    2: 0.70,   # 2日前
    3: 0.45,   # 3日前
}

LINK_WEIGHT_COEF = 2.0

def get_valid_top_scores(settings, target_date, days_ago, machines):
    settings["日付"] = pd.to_datetime(settings["日付"]).dt.normalize()
    target_day = pd.to_datetime(target_date).normalize() - pd.Timedelta(days=days_ago)

    day_row = settings[settings["日付"] == target_day]

    if day_row.empty:
        return []

    day_row = day_row.iloc[0]

    day_scores = []

    for m in machines:
        col = f"{m}_設定"
        if col in day_row.index:
            v = day_row[col]
            if pd.notna(v):
                day_scores.append((m, v))

    high_scores = [
        (m, v)
        for m, v in day_scores
        if pd.notna(v) and v >= 4
    ]

    sub_scores = [
        (m, v)
        for m, v in day_scores
        if pd.notna(v) and v == 3
    ]

    return (
        sorted(high_scores, key=lambda x: x[1], reverse=True)
        + sorted(sub_scores, key=lambda x: x[1], reverse=True)
    )

MACHINE_CONFIGS = {

"GOD": {
    "name": "ミリオンゴッド",
    "file": "GOD.xlsx",
    "machines": list(range(1164, 1178)),
    "circle_order": list(range(1164, 1178)),
    "section_id": "god",
    "html": "god_link.html",
    "today_html": "god_today.html",
},

"VVV2": {
    "name": "ヴァルヴレイヴ2",
    "file": "VVV2.xlsx",
    "machines": [1178, 1179, 1180, 1181, 1182, 1183, 1189, 1190],
    "circle_order": [1178, 1179, 1180, 1181, 1182, 1183, 1189, 1190],
    "section_id": "vvv",
    "html": "vvv_link.html",
    "today_html": "vvv_today.html",
},

"OKIDOKI": {
    "name": "沖ドキ",
    "file": "OKIDOKI.xlsx",
    "machines": list(range(1144, 1164)),
    "circle_order": list(range(1144, 1164)),
    "section_id": "okidoki",
    "html": "okidoki_link.html",
    "today_html": "okidoki_today.html",
},

"TOKYO_GHOUL": {
    "name": "東京喰種",
    "file": "TOKYO_GHOUL.xlsx",
    "machines": list(range(1197, 1206)) + list(range(1216, 1227)),
    "circle_order": list(range(1197, 1206)) + list(range(1216, 1227)),
    "section_id": "tokyo",
    "html": "tokyo_link.html",
    "today_html": "tokyo_today.html",
},

"HOKUTO": {
    "name": "北斗の拳",
    "file": "HOKUTO.xlsx",
    "machines": list(range(1281, 1301)),
    "circle_order": list(range(1281, 1301)),
    "section_id": "hokuto",
    "html": "hokuto_link.html",
    "today_html": "hokuto_today.html",
},

}

FILE_LIST = [
    config["file"]
    for config in MACHINE_CONFIGS.values()
]

html_sections = {}

all_top15 = []

sheetname = "周期"

def get_island(machine):
    # 沖ドキ
    if 1144 <= machine <= 1153:
        return "島1"
    elif 1154 <= machine <= 1163:
        return "島2"

    # GOD
    elif 1164 <= machine <= 1170:
        return "島1"
    elif 1171 <= machine <= 1177:
        return "島2"

    # VVV2
    elif machine in [1178, 1179, 1180, 1181, 1182, 1183, 1189, 1190]:
        return "島1"

    # 東京喰種
    elif 1197 <= machine <= 1205:
        return "島1"
    elif 1216 <= machine <= 1226:
        return "島2"
    
    # 北斗の拳
    elif 1281 <= machine <= 1290:
        return "島1"
    elif 1291 <= machine <= 1300:
        return "島2"

    return "_"

def get_circle_diff(prev_machine, current_machine, machine_list):
    if prev_machine not in machine_list or current_machine not in machine_list:
        return None

    n = len(machine_list)

    prev_i = machine_list.index(prev_machine)
    curr_i = machine_list.index(current_machine)

    diff = curr_i - prev_i

    if diff > n // 2:
        diff -= n
    elif diff < -n // 2:
        diff += n

    return diff

def old_data_weight(days_ago):
    """
    古いデータ補正
    days_ago: 何日前のデータか
    直近ほど1.0に近く、古いほど弱くする
    """
    if days_ago <= 7:
        return 1.00
    elif days_ago <= 14:
        return 0.85
    elif days_ago <= 30:
        return 0.70
    elif days_ago <= 60:
        return 0.50
    else:
        return 0.30
        
def calc_recent_move_rate(history, from_machine, to_machine, days=30):
    recent = history.tail(days + 1)

    total = 0
    hit = 0

    from_col = f"{from_machine}_設定"
    to_col = f"{to_machine}_設定"

    if from_col not in recent.columns or to_col not in recent.columns:
        return 0, 0

    for i in range(1, len(recent)):
        prev_row = recent.iloc[i - 1]
        curr_row = recent.iloc[i]

        try:
            prev_setting = float(prev_row[from_col])
        except:
            prev_setting = 0

        try:
            curr_setting = float(curr_row[to_col])
        except:
            curr_setting = 0

        if prev_setting >= 4:
            total += 1

            if curr_setting >= 4:
                hit += 1

    if total == 0:
        return 0, 0

    return round(hit / total * 100, 1), total
        
def calc_prev_top_link_rate(history, base_machine, target_machine, days=30):
    recent = history.tail(days)

    hit = 0
    total = 0

    for _, row in recent.iterrows():
        prev_high = row.get("前日高設定")
        current_high = row.get("当日高設定")

        if str(prev_high) == str(base_machine):
            total += 1

            if str(current_high) == str(target_machine):
                hit += 1

    rate = round(hit / total * 100, 1) if total > 0 else 0
    return rate, hit, total
    
def build_two_step_bonus(settings, target_machines, circle_order=None, high_setting=4):
    """
    日付順に A→B→C を作り、
    スコア用には B→C の回数を返す
    """

    two_step_counts = {}

    if circle_order is None:
        circle_order = target_machines

    # 日付順に並べる
    settings = settings.sort_values("日付").reset_index(drop=True)

    for i in range(len(settings) - 2):

        day_a = settings.iloc[i]
        day_b = settings.iloc[i + 1]
        day_c = settings.iloc[i + 2]

        a_list = []
        b_list = []
        c_list = []

        for m in target_machines:
            col = f"{m}_設定"

            if col not in settings.columns:
                continue

            if pd.notna(day_a[col]) and day_a[col] >= high_setting:
                a_list.append(m)

            if pd.notna(day_b[col]) and day_b[col] >= high_setting:
                b_list.append(m)

            if pd.notna(day_c[col]) and day_c[col] >= high_setting:
                c_list.append(m)

        # A→B→C のうち、スコアでは B→C を使う
        for a in a_list:
            for b in b_list:
                for c in c_list:
                    diff_ab = get_circle_diff(a, b, circle_order)
                    diff_bc = get_circle_diff(b, c, circle_order)

                    if diff_ab is None or diff_bc is None:
                        continue

                    if abs(diff_ab) == 1 and abs(diff_bc) == 1:
                        key = (b, c)
                        two_step_counts[key] = two_step_counts.get(key, 0) + 1

    return two_step_counts
    
print("実行ファイル一覧:", FILE_LIST)

HIGH_SETTING = 4
BOOST_COEF = 3.0
PREV_RESULT_COEF = 0.8
RECENT_DAYS = 30
LINK_BONUS_COEF = 0.8
CYCLE_PENALTY_COEF = 0.15

def make_bonus(hit, total=30, coef=3.0):
    rate = hit / total if total > 0 else 0
    return 1 + (rate * coef)

def make_prev_top3_html(settings, prev_top3, data):
    if len(prev_top3) == 0:
        return "<div class='prev-top3-box'>前日TOP3：なし</div>"

    prev_row = settings.iloc[-2]

    def get_scalar(v):
        if isinstance(v, pd.Series):
            v = v.iloc[0]
        return v

    filtered_prev_top3 = []

    for machine in prev_top3:
        setting_col = f"{machine}_設定"

        if setting_col not in prev_row.index:
            continue

        setting = prev_row[setting_col]

        if pd.notna(setting) and setting >= 4:
            filtered_prev_top3.append(machine)

    # 4以上が3台未満なら設定3を追加
    if len(filtered_prev_top3) < 3:
        for machine in prev_top3:
            setting_col = f"{machine}_設定"

            if setting_col not in prev_row.index:
                continue

            setting = get_scalar(prev_row[setting_col])

            if pd.notna(setting) and setting == 3:
                if machine not in filtered_prev_top3:
                    filtered_prev_top3.append(machine)

            if len(filtered_prev_top3) >= 3:
                break
    prev_data_row = data.iloc[-2]

    html = "<div class='prev-top3-box'>"
    html += "<div><b>前日TOP3</b></div>"
        
    for i, machine in enumerate(filtered_prev_top3[:3], start=1):

        def find_col(keyword):
            hits = [
                c for c in prev_data_row.index
                if str(c).startswith(f"{machine}_")
                and keyword in str(c)
            ]
            return hits[0] if hits else None

        setting_col = find_col("設定")
        max_col = find_col("最大放出")
        diff_col = find_col("日別差枚")
        cycle_col = find_col("周期")

        if not setting_col:
            continue

        setting = get_scalar(prev_row[setting_col])

        max_out = get_scalar(prev_data_row[max_col]) if max_col else "-"
        diff = get_scalar(prev_data_row[diff_col]) if diff_col else "-"
        cycle = get_scalar(prev_data_row[cycle_col]) if cycle_col else "-"

        # print("setting=", type(setting), setting)
        # print("max_out=", type(max_out), max_out)
        # print("diff=", type(diff), diff)
        # print("cycle=", type(cycle), cycle)

        try:
            setting = int(setting)
        except:
            pass

        try:
            max_out = int(max_out)
        except:
            pass

        try:
            diff = int(diff)
            diff = f"{diff:+}"
        except:
            pass

        html += f"""
        <div>{i}位：{machine}番台　
        設定:{setting}　
        最大放出:{max_out}　
        差枚:{diff}　
        前日周期:{cycle}日</div>
        """

    html += "</div>"
    return html

def calc_cycle_days(settings, target):
    col = f"{target}_設定"

    if col not in settings.columns:
        return "-"

    temp = settings.copy()
    temp["日付"] = pd.to_datetime(temp["日付"], errors="coerce")

    # 設定を数値化
    temp[col] = pd.to_numeric(temp[col], errors="coerce")

    # 設定4以上の日だけ
    # 設定0以上の日も周期に含める
    high_days = temp[
        (temp[col] >= HIGH_SETTING) &
        (temp["日付"].notna())
    ]["日付"].sort_values()

    if len(high_days) == 0:
        return "-"

    last_high_date = high_days.iloc[-1]

    # 予想日基準で周期を見る
    base_date = pd.Timestamp.today().normalize()
    cycle_days = (base_date - last_high_date.normalize()).days

    return cycle_days
for FILE_NAME in FILE_LIST:

    # print("処理開始:", FILE_NAME)

    machine_key = FILE_NAME.replace(".xlsx", "")

    if machine_key not in MACHINE_CONFIGS:
        raise ValueError("機種名が不明です")

    config = MACHINE_CONFIGS[machine_key]

    CIRCLE_ORDER = config.get("circle_order", config["machines"])

    CIRCLE_ORDER = config.get("circle_order", config["machines"])
    DISPLAY_MAP = config.get("display_map", {})

    # print("CIRCLE_ORDER =", CIRCLE_ORDER)

    DISPLAY_MAP = config.get("display_map", {})

    MACHINE_NAME = config["name"]
    TARGET_MACHINES = config["machines"]
    SECTION_ID = config["section_id"]
    OUTPUT_HTML = config["html"]
    OUTPUT_TODAY_HTML = config["today_html"]

    print("機種名:", MACHINE_NAME)
    print("使用ファイル:", FILE_NAME)
    # print("対象台:", TARGET_MACHINES)

    raw = pd.read_excel(FILE_NAME, sheet_name=sheetname, header=None)
    machines = raw.iloc[1]
    types = raw.iloc[2]
    data = raw.iloc[3:].copy()

    new_columns = []
    last_machine = None

    for m, t in zip(machines, types):
        if pd.notna(m):
            try:
                last_machine = int(m)
            except:
                last_machine = None
                new_columns.append("")
                continue

        if str(t) == "日付":
            new_columns.append("日付")

        elif last_machine is not None and pd.notna(t):
            new_columns.append(f"{last_machine}_{t}")

        elif "日別差枚" in str(t) and last_machine is not None:
            new_columns.append(f"{last_machine}_日別差枚")

        else:
            new_columns.append("")

    # print("列数確認:", len(data.columns), len(new_columns))
    # print(new_columns[:10])
    data.columns = new_columns
    data = data.loc[:, data.columns != ""]

    if "日付" in data.columns:
        data["日付"] = pd.to_datetime(data["日付"], errors="coerce")
        today = pd.Timestamp.today().normalize()
        data = data[data["日付"] <= today]

        # 対象台の設定列だけ抽出
        setting_cols = []
        for machine in TARGET_MACHINES:
            col = f"{machine}_設定"
            if col in data.columns:
                setting_cols.append(col)

        settings = data[["日付"] + setting_cols].copy()

        # 重複列名を削除（同じ列名が複数あると pd.to_numeric でエラーになる）
        settings = settings.loc[:, ~settings.columns.duplicated()]

        for col in setting_cols:
            settings[col] = pd.to_numeric(settings[col], errors="coerce")

        settings = settings.dropna(how="all", subset=setting_cols)
        # 設定データが入っている日だけ使う
        settings = settings.dropna(how="all", subset=setting_cols)

        # 今日以降の空予定行を除外
        today = pd.Timestamp.today().normalize()
        settings = settings[settings["日付"] <= today]

        # 最新の実データ日
        latest_date = settings["日付"].max()
        print("\n=== 最新実データ日 ===")
        print(latest_date.date())

        print("=== 対象データ ===")

        # print(settings.tail(10))

        print("\n=== 台番別 高設定分析 ===")

        two_step_bonus = build_two_step_bonus(settings, TARGET_MACHINES, CIRCLE_ORDER)

        result = []

        for machine in TARGET_MACHINES:
            col = f"{machine}_設定"

            if col not in settings.columns:
                continue

            values = settings[col].tail(RECENT_DAYS)

            total_count = values.count()
            high_count = (values >= HIGH_SETTING).sum()
            avg_setting = values.mean()

            high_rate = high_count / total_count * 100 if total_count > 0 else 0
            result.append({
                "台番": machine,
                "データ数": total_count,
                "4以上回数": high_count,
                "4以上率": round(high_rate, 1),
                "平均設定": round(avg_setting, 2) if pd.notna(avg_setting) else None
            })

        result_df = pd.DataFrame(result)
        print(result_df.sort_values("4以上率", ascending=False))

        print("\n=== 曜日別 高設定率 ===")

        settings["曜日"] = settings["日付"].dt.day_name()

        weekday_result = []

        for weekday, group in settings.groupby("曜日"):
            values = group[setting_cols].values.flatten()
            values = pd.Series(values).dropna()

            total = len(values)
            high = (values >= HIGH_SETTING).sum()
            rate = high / total * 100 if total > 0 else 0

            weekday_result.append({
                "曜日": weekday,
                "データ数": total,
                "4以上回数": high,
                "4以上率": round(rate, 1)
            })

        weekday_df = pd.DataFrame(weekday_result)
        print(weekday_df.sort_values("4以上率", ascending=False))

        print("\n=== 直近の高設定投入履歴 ===")

        recent = settings.tail(14)

        for _, row in recent.iterrows():
            date = row["日付"]
            highs = []

            for machine in TARGET_MACHINES:
                col = f"{machine}_設定"
                if col in settings.columns and pd.notna(row[col]) and row[col] >= HIGH_SETTING:
                    highs.append(f"{machine}({int(row[col])})")

            print(str(date.date()) + ":", ", ".join(highs) if highs else "なし")

        print("\n=== 簡易ランキング_台自体の強さ ===")

        score_result = []

        for machine in TARGET_MACHINES:
            col = f"{machine}_設定"
            if col not in settings.columns:
                continue

            series = settings[col].dropna()
            if len(series) == 0:
                continue

            avg = series.mean()
            high_rate = (series >= HIGH_SETTING).mean() * 100
            recent_avg = series.tail(7).mean()
            last_value = series.iloc[-1]

            score = 0
            score += high_rate * 0.5
            score += avg * 8
            score += recent_avg * 6

            if last_value >= HIGH_SETTING:
                score -= 8

            score_result.append({
                "台番": machine,
                "総合スコア": round(score, 1),
                "平均設定": round(avg, 2),
                "直近7回平均": round(recent_avg, 2),
                "4以上率": round(high_rate, 1),
                "前回設定": int(last_value) if pd.notna(last_value) else None
            })

        score_df = pd.DataFrame(score_result)

        old_standard_map = dict(
            zip(score_df["台番"], score_df["総合スコア"])
        )
        
        print(score_df.sort_values("総合スコア", ascending=False))
        print("\n=== 横移動分析 ===")

        moves = []

        for i in range(1, len(settings)):
            prev = settings.iloc[i-1]
            curr = settings.iloc[i]

            prev_high = []
            curr_high = []

            for machine in TARGET_MACHINES:
                col = f"{machine}_設定"
                if col in settings.columns:
                    if pd.notna(prev[col]) and prev[col] >= HIGH_SETTING:
                        prev_high.append(machine)
                    if pd.notna(curr[col]) and curr[col] >= HIGH_SETTING:
                        curr_high.append(machine)

            for p in prev_high:
                for c in curr_high:
                    diff = c - p
                    moves.append(diff)

        move_series = pd.Series(moves)
        # print(move_series.value_counts().sort_index())


        print("\n=== 据え置き分析 ===")

        hold_count = 0
        total_high = 0

        for i in range(1, len(settings)):
            prev = settings.iloc[i-1]
            curr = settings.iloc[i]

            for machine in TARGET_MACHINES:
                col = f"{machine}_設定"
                if col in settings.columns:
                    if pd.notna(prev[col]) and prev[col] >= HIGH_SETTING:
                        total_high += 1
                        if pd.notna(curr[col]) and curr[col] >= HIGH_SETTING:
                            hold_count += 1

        hold_rate = (hold_count / total_high * 100) if total_high > 0 else 0

        print("据え置き回数:", hold_count)
        print("据え置き率:", round(hold_rate,1), "%")


        print("\n=== 罠台検出（直近落ち）===")

        trap_list = []

        trap_html = "<h3>罠台検出</h3>"

        if len(trap_list) > 0:
            trap_html += "<div>"
            trap_html += "、".join(str(x) for x in trap_list)
            trap_html += "</div>"
        else:
            trap_html += "<div>なし</div>"


        print("\n=== 今日の狙い補正ランキング ===")

        final_score = []

        for machine in TARGET_MACHINES:
            col = f"{machine}_設定"
            if col not in settings.columns:
                continue

            series = settings[col].dropna()
            if len(series) < 3:
                continue

            score = 0

            # ベーススコア
            avg = series.mean()
            score += avg * 10

            # 直近弱台優遇
            if series.iloc[-1] < 3:
                score += 5

            # 前日隣台高設定チェック
            prev = settings.iloc[-2] if len(settings) >= 2 else settings.iloc[-1]
            left = machine - 1
            right = machine + 1

            for near in [left, right]:
                near_col = f"{near}_設定"
                if near_col in settings.columns:
                    if pd.notna(prev[near_col]) and prev[near_col] >= HIGH_SETTING:
                        score += 8

            # 据え置き回避
            if series.iloc[-1] >= HIGH_SETTING:
                score -= 10

            # 前日高設定を少し加点
            if pd.notna(prev[col]) and prev[col] >= HIGH_SETTING:
                score += (prev[col] - HIGH_SETTING + 1) * PREV_RESULT_COEF

            final_score.append({
                "台番": machine,
                "スコア": round(score, 1),

                # 仮のpt（後で本計算へ変更）
                "pt": round(score, 2),

                "前回設定": int(prev[col]) if pd.notna(prev[col]) else 0
            })

        final_df = pd.DataFrame(final_score)
        # print("final_df列:", final_df.columns.tolist())
        # print(final_df.sort_values("pt", ascending=False))
        print("\n=== 島全体の流れ（差枚） ===")

        diff_cols = [c for c in data.columns if "日別差枚" in c]

        if diff_cols:
            pass
            # data["島差枚"] = data[diff_cols].sum(axis=1)
            # print(data[["日付","島差枚"]].tail(10))
        else:
            print("日別差枚が見つかりません")


        print("\n=== 台ごとの強さ（差枚ベース） ===")

        machine_power = []

        for machine in TARGET_MACHINES:
            diff_col = f"{machine}_日別差枚"
            if diff_col in data.columns:

                tmp = data[diff_col]

                # 同じ列名が複数ある場合は、左側の1列だけ使う
                if isinstance(tmp, pd.DataFrame):
                    tmp = tmp.iloc[:, 0]

                series = pd.to_numeric(tmp, errors="coerce").dropna()

                if len(series) > 0:
                    avg = series.mean()
                    recent = series.tail(5).mean()

                    machine_power.append({
                        "台番": machine,
                        "平均差枚": int(avg),
                        "直近差枚": int(recent)
                    })

        power_df = pd.DataFrame(machine_power)
        if len(power_df) > 0 and "直近差枚" in power_df.columns:
            pass
            # print(power_df.sort_values("直近差枚", ascending=False))
        else:
            print("日別差枚データが見つからないため、差枚分析はスキップします")


        print("\n=== 復活台検出 ===")

        revival = []

        for machine in TARGET_MACHINES:
            col = f"{machine}_設定"
            diff_col = f"{machine}_日別差枚"

            if col in settings.columns and diff_col in data.columns:
                set_series = settings[col].dropna()
                tmp = data[diff_col]

                # 同じ列名が複数ある場合は、左側の1列だけ使う
                if isinstance(tmp, pd.DataFrame):
                    tmp = tmp.iloc[:, 0]

                diff_series = pd.to_numeric(tmp, errors="coerce").dropna()

                if len(set_series) >= 2 and len(diff_series) >= 2:
                    # 前日弱い + 今日強い
                    if set_series.iloc[-2] <= 2 and diff_series.iloc[-1] > 500:
                        revival.append(machine)

        print("復活候補:", revival)


        print("\n=== ハイブリッドスコア_横移動分析前のスコア ===")

        hybrid = []

        for machine in TARGET_MACHINES:
            col = f"{machine}_設定"
            diff_col = f"{machine}_日別差枚"

            if col not in settings.columns:
                continue

            set_series = settings[col].dropna()
            if len(set_series) < 3:
                continue

            score = 0

            # 設定ベース
            avg = set_series.mean()
            score += avg * 8

            # 直近弱いなら加点
            if set_series.iloc[-1] <= 2:
                score += 5

            # 差枚要素
            if diff_col in data.columns:
                tmp = data[diff_col]

                if isinstance(tmp, pd.DataFrame):
                    tmp = tmp.iloc[:, 0]

                diff_series = pd.to_numeric(tmp, errors="coerce").dropna()

                if len(diff_series) > 0:
                    recent_diff = diff_series.tail(3).mean()
                    score += recent_diff / 500  # スケーリング

            # 復活補正
            if machine in revival:
                score += prev[col]

            # 罠回避
            if machine in trap_list:
                score -= 3.0

            hybrid.append({
                "台番": machine,
                "総合スコア": round(score,1),
                "前回設定": int(set_series.iloc[-1])
            })

        hybrid_df = pd.DataFrame(hybrid)
        # print(hybrid_df.sort_values("総合スコア", ascending=False))

        print("\n=== 横移動パターン解析 ===")

        move_list = []

        for i in range(1, len(settings)):
            prev = settings.iloc[i-1]
            curr = settings.iloc[i]

            prev_high = []
            curr_high = []

            for m in TARGET_MACHINES:
                col = f"{m}_設定"
                if col in settings.columns:
                    if pd.notna(prev[col]) and prev[col] >= HIGH_SETTING:
                        prev_high.append(m)
                    if pd.notna(curr[col]) and curr[col] >= HIGH_SETTING:
                        curr_high.append(m)

            for p in prev_high:
                for c in curr_high:
                    move_list.append(c - p)

        moves = pd.Series(move_list)
        # print(moves.value_counts().sort_index())

        print("\n=== 横移動分析 ===")

        movement = []

        # 日付でソート
        settings = settings.sort_values("日付")

        # 高設定判定（仮：4以上）
        for i in range(len(settings)-1):
            today = settings.iloc[i]
            next_day = settings.iloc[i+1]

            for col in setting_cols:
                val = today[col]

                if val >= 4:
                    base_machine = int(col.split("_")[0])

                    # 翌日の高設定探す
                    for next_col in setting_cols:
                        next_val = next_day[next_col]

                        if next_val >= 4:
                            next_machine = int(next_col.split("_")[0])
                            diff = next_machine - base_machine
                            movement.append(diff)

        # 集計
        import pandas as pd
        move_series = pd.Series(movement)

        # print(move_series.value_counts(normalize=True) * 100)

        print("\n=== 曜日別分析 ===")

        # 曜日作成
        settings["曜日"] = settings["日付"].dt.day_name()

        result = []

        for day in settings["曜日"].unique():
            df_day = settings[settings["曜日"] == day]

            total = 0
            count = 0
            high_count = 0

            for col in setting_cols:
                vals = df_day[col].dropna()

                total += vals.sum()
                count += len(vals)
                high_count += (vals >= 4).sum()

            if count > 0:
                avg = total / count
                high_rate = high_count / count * 100
            else:
                avg = 0
                high_rate = 0

            result.append([day, avg, high_rate])

        # 表示
        import pandas as pd
        df_result = pd.DataFrame(result, columns=["曜日", "平均設定", "高設定率"])

        # 並び替え（強い順）
        # df_result = df_result.sort_values("平均設定", ascending=False)

       # print(df_result)

        print("\n==============================")
        print(" 全期間 vs 直近30日 比較 ")
        print("==============================")

        # ========= 全期間 =========
        print("\n--- 全期間 曜日分析 ---")

        settings_all = settings.copy()
        settings_all["曜日"] = settings_all["日付"].dt.day_name()

        result_all = []

        for day in settings_all["曜日"].unique():
            df_day = settings_all[settings_all["曜日"] == day]

            total = 0
            count = 0
            high_count = 0

            for col in setting_cols:
                vals = df_day[col].dropna()

                total += vals.sum()
                count += len(vals)
                high_count += (vals >= 4).sum()

            if count > 0:
                avg = total / count
                high_rate = high_count / count * 100
            else:
                avg = 0
                high_rate = 0

            result_all.append([day, avg, high_rate])

        df_all = pd.DataFrame(result_all, columns=["曜日", "平均設定", "高設定率"])
        df_all = df_all.sort_values("平均設定", ascending=False)

        print(df_all)


        # ========= 直近30日 =========
        print("\n--- 直近30日 曜日分析 ---")

        latest_date = settings["日付"].max()
        settings_recent = settings[settings["日付"] >= latest_date - pd.Timedelta(days=30)]

        settings_recent["曜日"] = settings_recent["日付"].dt.day_name()

        result_recent = []

        for day in settings_recent["曜日"].unique():
            df_day = settings_recent[settings_recent["曜日"] == day]

            total = 0
            count = 0
            high_count = 0

            for col in setting_cols:
                vals = df_day[col].dropna()

                total += vals.sum()
                count += len(vals)
                high_count += (vals >= 4).sum()

            if count > 0:
                avg = total / count
                high_rate = high_count / count * 100
            else:
                avg = 0
                high_rate = 0

            result_recent.append([day, avg, high_rate])

        df_recent = pd.DataFrame(result_recent, columns=["曜日", "平均設定", "高設定率"])
        df_recent = df_recent.sort_values("平均設定", ascending=False)

        print(df_recent)

        print("\n==============================")
        print(" 横移動・1つ飛び・据え置き分析（全期間 vs 直近30日）")
        print("==============================")

        def analyze_move_full(data, title):
            print(f"\n--- {title} ---")

            data = data.sort_values("日付").copy()
            moves = []

            for i in range(len(data) - 1):
                today = data.iloc[i]
                next_day = data.iloc[i + 1]

                for col in setting_cols:
                    if pd.notna(today[col]) and today[col] >= 4:
                        base_machine = int(col.split("_")[0])

                        for next_col in setting_cols:
                            if pd.notna(next_day[next_col]) and next_day[next_col] >= 4:
                                next_machine = int(next_col.split("_")[0])
                                diff = next_machine - base_machine

                                # 据え置き・横・1つ飛びだけ
                                if diff in [-2, -1, 0, 1, 2]:
                                    moves.append(diff)

            if len(moves) == 0:
                print("データなし")
                return

            s = pd.Series(moves)

            result = pd.DataFrame({
                "回数": s.value_counts(),
                "割合%": (s.value_counts(normalize=True) * 100).round(1)
            }).sort_index()

            print(result)

            # print("\n見方")
            # print(" 0  = 据え置き")
            # print("+1 = 右隣")
            # print("-1 = 左隣")
            # print("+2 = 右1つ飛び")
            # print("-2 = 左1つ飛び")


        # ========= 全期間 =========
        analyze_move_full(settings, "全期間")

        # ========= 直近30日 =========
        latest_date = settings["日付"].max()
        settings_recent = settings[settings["日付"] >= latest_date - pd.Timedelta(days=30)]

        analyze_move_full(settings_recent, "直近30日")

        print("\n=== 台番号ごとのクセ分析_高設定判定レベル調整可能 ===")

        # 高設定判定（ここは自由に調整OK）
        HIGH_LEVEL = 2

        # 日付順に並び替え
        data_sorted = settings.sort_values("日付")

        pattern_dict = {}

        for i in range(len(data_sorted) - 1):
            today = data_sorted.iloc[i]
            next_day = data_sorted.iloc[i + 1]

            for col in setting_cols:
                val_today = today[col]
                if pd.isna(val_today):
                    continue

                if val_today >= HIGH_LEVEL:
                    base_machine = int(col.split("_")[0])

                    # 次の日の高設定台探す
                    for col2 in setting_cols:
                        val_next = next_day[col2]
                        if pd.isna(val_next):
                            continue

                        if val_next >= HIGH_LEVEL:
                            next_machine = int(col2.split("_")[0])

                            diff = next_machine - base_machine

                            if base_machine not in pattern_dict:
                                pattern_dict[base_machine] = []

                            pattern_dict[base_machine].append(diff)

        # print("setting_cols:", setting_cols)
        # print("pattern_dict件数:", len(pattern_dict))
        # print("pattern_dict台番:", list(pattern_dict.keys()))

        # 出力
        for machine, diffs in pattern_dict.items():
            s = pd.Series(diffs)

            # ★ここ追加（超重要）
            s = pd.to_numeric(s, errors="coerce").dropna()

            ratio = (s.value_counts(normalize=True) * 100).round(1)

            # print(f"\n■ 台 {machine}")
            # print(ratio.sort_index())

        # ===== 島全体の流れ（差枚） =====
        diff_series_list = []

        for i, col in enumerate(data.columns):
            if "日付差枚" in str(col):
                vals = pd.to_numeric(data.iloc[:, i], errors="coerce").fillna(0)
                diff_series_list.append(vals)

        if len(diff_series_list) == 0:
            island_diff = pd.Series([0] * len(data))
        else:
            island_diff = pd.concat(diff_series_list, axis=1).sum(axis=1)

        island = pd.DataFrame({
            "日付": data["日付"].values,
            "島差枚": island_diff.values
        })

        # print("\n=== 2段移動分析 A→B→C ===")

        two_step_results = []

        data_sorted = settings.sort_values("日付").copy()

        for i in range(len(data_sorted) - 2):
            day_a = data_sorted.iloc[i]
            day_b = data_sorted.iloc[i + 1]
            day_c = data_sorted.iloc[i + 2]

            for col_a in setting_cols:
                if pd.notna(day_a[col_a]) and day_a[col_a] >= HIGH_SETTING:
                    machine_a = int(col_a.split("_")[0])

                    for col_b in setting_cols:
                        if pd.notna(day_b[col_b]) and day_b[col_b] >= HIGH_SETTING:
                            machine_b = int(col_b.split("_")[0])
                            move_ab = machine_b - machine_a

                            for col_c in setting_cols:
                                if pd.notna(day_c[col_c]) and day_c[col_c] >= HIGH_SETTING:
                                    machine_c = int(col_c.split("_")[0])
                                    move_bc = machine_c - machine_b
                                    move_ac = machine_c - machine_a

                                    two_step_results.append({
                                        "A": machine_a,
                                        "B": machine_b,
                                        "C": machine_c,
                                        "A→B": move_ab,
                                        "B→C": move_bc,
                                        "A→C": move_ac
                                    })

        two_step_df = pd.DataFrame(two_step_results)

        # print("\n=== 2段移動スコア計算 ===")

        two_step_score = {}

        if 'two_step_df' in locals() and not two_step_df.empty:
            for _, row in two_step_df.iterrows():
                c = row["C"]

                if c not in two_step_score:
                    two_step_score[c] = 0

                two_step_score[c] += 1

            if len(two_step_score) > 0:
                max_val = max(two_step_score.values())
                for k in two_step_score:
                    two_step_score[k] = two_step_score[k] / max_val
        else:
            print("2段移動データなし")

        # print(island[["日付", "島差枚"]].tail(5))

        # print("pattern_dict件数:", len(pattern_dict))
        # print("pattern_dict台番:", list(pattern_dict.keys()))

        # print("\n=== 最終ハイブリッド予想 ===")

        # ===== 設定 =====
        BASE_MACHINE = 1180        # 今日の基点（当たり台）
        USE_RECENT_WEEK = True     # 直近30日を使う

        # 曜日補正テーブル（あなたの出力をここにコピペ）
        weekday_weight_all = {
            "Monday": 1.21, "Tuesday": 1.04, "Wednesday": 1.09,
            "Thursday": 1.10, "Friday": 1.31, "Saturday": 1.38, "Sunday": 1.06
        }
        weekday_weight_recent = {
            "Monday": 1.59, "Tuesday": 1.23, "Wednesday": 0.74,
            "Thursday": 0.45, "Friday": 0.84, "Saturday": 0.61, "Sunday": 1.40
        }

        # ===== 最大放出スコア =====
        max_release_score = {}

        for i, col in enumerate(data.columns):
            if "最大放出" in str(col):
                # print(col)
                machine = int(str(col).split("_")[0])

                vals = pd.to_numeric(data.iloc[:, i], errors="coerce").fillna(0)
                max_release_score[machine] = float(vals.tail(7).max()) / 1000

        # 島の流れ（直近の島差枚の平均でざっくり判定）
        # 島の流れ（直近3日）

        flow_vals = pd.to_numeric(island["島差枚"], errors="coerce").fillna(0)
        recent_flow = flow_vals.tail(3).mean()

        if recent_flow > 0:
            flow_weight = 1.2  # 放出
        else:
            flow_weight = 0.8  # 回収

        # 今日の曜日
        today_weekday = settings["日付"].dropna().iloc[-1].strftime("%A")

        if USE_RECENT_WEEK:
            w_weight = weekday_weight_recent.get(today_weekday, 1.0)
        else:
            w_weight = weekday_weight_all.get(today_weekday, 1.0)

        # ===== 前日 差枚TOP3 =====
        latest_date = data["日付"].max()
        prev_date = data[data["日付"] < latest_date]["日付"].max()

        prev_row = data[data["日付"] == prev_date].iloc[0]

        prev_scores = []

        import re

        for col in data.columns:
            if "日別差枚" in str(col):
                match = re.search(r"\d+", str(col))
                if not match:
                    continue

                machine = int(match.group())

                if machine in TARGET_MACHINES:
                    tmp = prev_row[col]

                    # 同じ列名が重複している場合は、左側の1個だけ使う
                    if isinstance(tmp, pd.Series):
                        tmp = tmp.iloc[0]

                    val = pd.to_numeric(tmp, errors="coerce")

                    if pd.notna(val):
                        prev_scores.append({
                            "台番": machine,
                            "基準値": val
                        })

        # print("日別差枚列:", [c for c in data.columns if "日別差枚" in str(c)])

        # print(prev_scores)

        if len(prev_scores) == 0:
            prev_top3 = []
        else:
            prev_top3 = (
                pd.DataFrame(prev_scores)
                .sort_values("基準値", ascending=False)
                .drop_duplicates(subset=["台番"])
                .head(3)["台番"]
                .tolist()
            )

        print("前日基準TOP3:", prev_top3)

        # ===== 横移動クセ取得 =====

        # ===== スコア計算 =====
        # ===== 複数基準で合算スコア計算 =====
        total_scores = {}
        contrib = {}

        print("prev_top3:", prev_top3)
        for b in prev_top3:
            pass
            # print(b, pattern_dict.get(b, []))

        for base in prev_top3:

            base_pattern = pattern_dict.get(base, [])
            
            s = pd.Series(base_pattern)

            s = pd.to_numeric(s, errors="coerce").dropna()

            if len(s) == 0:
                total_scores[base] = 0
                continue

            score += max_release_score.get(base, 0) * 0.1

            ratio = s.value_counts(normalize=True)

            # print("base:", base)
            # print("ratio:", ratio)
            for move, prob in ratio.items():
                move = int(move)

                base_idx = TARGET_MACHINES.index(base)
                target_idx = (base_idx + move) % len(TARGET_MACHINES)
                target = TARGET_MACHINES[target_idx]

                # 存在しない台番は除外
                # if target not in TARGET_MACHINES:
                #    continue

                setting_col = f"{base}_設定"
                setting_val = 1

                if setting_col in settings.columns:
                    setting_raw = prev_row[setting_col]

                if isinstance(setting_raw, pd.Series):
                    setting_raw = setting_raw.iloc[0]

                setting_val = pd.to_numeric(setting_raw, errors="coerce")

                if pd.isna(setting_val):
                    setting_val = 1

                move_bonus = 1.0

        # 曜日別のクセ補正
                if today_weekday in ["Friday", "Saturday", "Sunday"]:
                    if move == 0:
                        move_bonus *= 1.25   # 据え置き強化
                    if abs(move) == 1:
                        move_bonus *= 1.15   # 横移動強化

                if today_weekday in ["Monday", "Tuesday"]:
                    if abs(move) == 2:
                        move_bonus *= 1.20   # 2つ飛び強化

                        # サークル移動成功率ボーナス
                        move_success_bonus = 1.0
                        stay_score_bonus = 1.0

                        # 移動あり：成功率が高いほど加点
                        if move != 0:
                            move_success_bonus = 1.0 + prob * 0.30

                        # 据え置き：高ければ加点、低ければ減点
                        if move == 0:
                            if prob >= 0.35:
                                stay_score_bonus = 1.20
                            elif prob >= 0.25:
                                stay_score_bonus = 1.10
                            elif prob <= 0.10:
                                stay_score_bonus = 0.85

                        # ===== ① 古いデータを弱くする =====
            # 直近ほど強く、古いデータほど弱くする
            recent_weight = 1.0

            if "日付" in prev_row:
                prev_date = pd.to_datetime(prev_row["日付"], errors="coerce")
                days_ago = (pd.Timestamp.today().normalize() - prev_date).days if pd.notna(prev_date) else 999

                if days_ago <= 7:
                    recent_weight = 1.30
                elif days_ago <= 14:
                    recent_weight = 1.15
                elif days_ago <= 30:
                    recent_weight = 1.00
                elif days_ago <= 60:
                    recent_weight = 0.75
                else:
                    recent_weight = 0.50


            # ===== ② 同じ基準台の連続使用に減衰 =====
            # 前回1位基準台と同じ場合だけ弱める
            same_base_penalty = 1.0
            
            if base == prev_top3[0]:
                same_base_penalty = 0.90


            # ===== ③ 周期を強化 =====
            # 設定4以上の周期が今日に近い台を強化
            # cycle_bonus = 1.0

            setting_col = f"{target}_設定"

            if setting_col in settings.columns:
                high_days = settings[settings[setting_col] >= HIGH_SETTING]["日付"].sort_values()

                if len(high_days) >= 2:
                    last_high_date = high_days.iloc[-1]
                    days_since_high = (pd.Timestamp.today().normalize() - last_high_date).days

                    cycle_candidates = []

                    for i in range(1, len(high_days)):
                        diff_days = (high_days.iloc[i] - high_days.iloc[i - 1]).days
                        if 1 <= diff_days <= 14:
                            cycle_candidates.append(diff_days)

                    if len(cycle_candidates) > 0:
                        avg_cycle = round(sum(cycle_candidates) / len(cycle_candidates))
                        cycle_gap = abs(days_since_high - avg_cycle)

                        # print(
                            # "周期確認",
                            # target,
                            # "days_since_high=",
                            # days_since_high,
                            # "avg_cycle=",
                            # avg_cycle,
                            # "gap=",
                            # cycle_gap
                        # )

                        if cycle_gap == 0:
                            cycle_bonus = 1.40
                        elif cycle_gap <= 2:
                            cycle_bonus = 1.25
                        elif cycle_gap <= 4:
                            cycle_bonus = 1.15
                        elif cycle_gap <= 7:
                            cycle_bonus = 1.05

            move_success_bonus = 1.0
            stay_score_bonus = 1.0

            setting_coef = 1 + ((setting_val - 1) * 0.15)
            setting_coef = min(setting_coef, 1.6)

            # 古いデータ補正：全期間データは少し弱める
            score = (
                prob
                * w_weight
                * flow_weight
                * setting_coef
                * recent_weight
                * same_base_penalty
                * cycle_bonus
                * move_bonus
                * move_success_bonus
                * stay_score_bonus
            )
            
            score += two_step_score.get(target, 0) * 2

            if target not in total_scores:
                total_scores[target] = 0

            total_scores[target] = max(total_scores.get(target, 0), score)

            if target not in contrib:
                contrib[target] = {}

            if target == 1161:
                print(
                    "DEBUG",
                    target,
                    prob,
                    w_weight,
                    flow_weight,
                    setting_coef,
                    recent_weight,
                    same_base_penalty,
                    cycle_bonus,
                    move_bonus,
                    score
                )

            base_score_display = round(score, 2)    

            contrib[target][base] = contrib[target].get(base, 0) + score

        for m in TARGET_MACHINES:
            if m not in total_scores:
                total_scores[m] = 0

        # ===== 台番単体の強さを最終スコアへ加算 =====
        for m in TARGET_MACHINES:
            col = f"{m}_設定"

            if col not in settings.columns:
                continue

            recent_values = settings[col].tail(RECENT_DAYS)

            high_count = int((recent_values >= HIGH_SETTING).sum())
            avg_setting = recent_values.mean()

            # 前日設定
            if len(settings) >= 2:
                prev_setting = settings[col].iloc[-2]
            else:
                prev_setting = 0

            base_bonus = 0

            # 直近30日の4以上回数
            base_bonus += high_count * 1.0

            # 平均設定
            if pd.notna(avg_setting):
                base_bonus += avg_setting * 2.0

            # 前日設定が4以上なら据え置き期待で加点
    
            if prev_setting >= HIGH_SETTING:
                base_bonus += prev_setting * 2.0

            # 罠台補正：前日高設定から直近落ちしている台は減点
            if target in trap_list:
                base_bonus -= 10.0    

            total_scores[m] += min(base_bonus, 25.0)       

        result = []

        for target, score in total_scores.items():
            target_col = f"{target}_設定"

            recent_data = settings.tail(RECENT_DAYS)

            # ===== 前日設定 =====
            if len(settings) >= 2 and target_col in settings.columns:
                prev_setting_for_score = settings[target_col].iloc[-2]
            else:
                prev_setting_for_score = 0

            # ===== 周期補正 =====
            cycle_days_for_score = calc_cycle_days(settings, target)
            cycle_bonus_for_score = 1.0

            try:
                cycle_num = int(cycle_days_for_score)

                if cycle_num <= 7:
                    cycle_bonus_for_score = 1.0
                else:
                    over_blocks = (cycle_num - 7) // 7 + 1
                    cycle_bonus_for_score = max(
                        0.5,
                        1.0 - (over_blocks * CYCLE_PENALTY_COEF)
                    )
            except:
                cycle_bonus_for_score = 1.0

            # ===== 前日TOP3連動補正 =====
            target_int = int(target)
            target_str = str(target)

            base_contrib = contrib.get(target_int, contrib.get(target_str, {}))

            valid_contrib = {
                k: v for k, v in base_contrib.items()
                if v >= 1.0 and k in prev_top3
            }

            if len(valid_contrib) == 0:
                top_machine_for_score = prev_top3[0] if len(prev_top3) > 0 else target
            else:
                top_machine_for_score = max(valid_contrib.items(), key=lambda x: x[1])[0]

            link_hit_for_score = 0
            link_total_for_score = 0

            base_col = f"{top_machine_for_score}_設定"

            if base_col in recent_data.columns and target_col in recent_data.columns:
                for i in range(len(recent_data) - 1):
                    today_row = recent_data.iloc[i]
                    next_row = recent_data.iloc[i + 1]

                    if today_row[base_col] >= HIGH_SETTING:
                        link_total_for_score += 1

                        if next_row[target_col] >= HIGH_SETTING:
                            link_hit_for_score += 1

            link_rate_for_score = (
                round(link_hit_for_score / link_total_for_score * 100, 1)
                if link_total_for_score > 0
                else 0
            )

            link_bonus_for_score = 1.0

            if top_machine_for_score in prev_top3 and top_machine_for_score != target:
                link_bonus_for_score = 1.0 + (link_rate_for_score / 100) * LINK_BONUS_COEF

            # =========================
            # 2段移動 B→C 加点
            # =========================

            two_step_score = 0

            for prev_machine in prev_top3:

                count = two_step_bonus.get((prev_machine, target), 0)

                # print("2段移動確認:", prev_machine, "→", target, "回数:", count)

                if count >= 4:
                    two_step_score += 1.0

                elif count == 3:
                    two_step_score += 0.6

                elif count == 2:
                    two_step_score += 0.3

                elif count == 1:
                    two_step_score += 0.1

            score += two_step_score  

            # ===== 最終スコアへ反映 =====
            final_score = score * link_bonus_for_score * cycle_bonus_for_score

            result.append({
                "台番": target,
                "標準スコア": round(score, 2),
                "最終スコア": round(final_score, 2),
                "最終pt": 0.0
            })
            
        hybrid_result = pd.DataFrame(result).sort_values(
            "最終スコア",
            ascending=False
        ).reset_index(drop=True)

        print("=== 完全ハイブリッドスコア ===")
        print(hybrid_result)

        two_step_bonus = build_two_step_bonus(settings, TARGET_MACHINES, CIRCLE_ORDER)

        # ===== 前日実績TOP3を作る =====
        prev_top3_machines = []

        top3_by_day = {}

        for back_day in [1, 2, 3]:

            if len(settings) >= back_day + 1:

                target_row = settings.iloc[-(back_day + 1)]

                prev_scores = []

                for m in TARGET_MACHINES:

                    col = f"{m}_設定"

                    if col in target_row.index:
                        prev_scores.append((m, target_row[col]))

                high_prev_scores = [
                    (m, v)
                    for m, v in prev_scores
                    if pd.notna(v) and v >= 4
                ]

                sub_prev_scores = [
                    (m, v)
                    for m, v in prev_scores
                    if pd.notna(v) and v == 3
                ]

                valid_scores = (
                    sorted(high_prev_scores, key=lambda x: x[1], reverse=True)
                    + sorted(sub_prev_scores, key=lambda x: x[1], reverse=True)
                )

                top3_by_day[back_day] = valid_scores[:3]

            else:
                top3_by_day[back_day] = []

        df_result = hybrid_result

        if len(settings) >= 2:
            prev_row = settings.iloc[-2]

            prev_scores = []

            for m in TARGET_MACHINES:
                col = f"{m}_設定"

                if col in prev_row.index:
                    prev_scores.append((m, prev_row[col]))

            # 設定4以上
            high_prev_scores = [
                (m, v)
                for m, v in prev_scores
                if pd.notna(v) and v >= 4
            ]

            # 設定3
            sub_prev_scores = [
                (m, v)
                for m, v in prev_scores
                if pd.notna(v) and v == 3
            ]

            # 4以上優先、不足時のみ3を追加
            valid_prev_scores = (
                sorted(high_prev_scores, key=lambda x: x[1], reverse=True)
                + sorted(sub_prev_scores, key=lambda x: x[1], reverse=True)
            )

            prev_top3_machines = [
                m for m, v in valid_prev_scores[:3]
            ]

        print("前日実績TOP3:", prev_top3_machines)
        # print("valid_prev_scores:", valid_prev_scores)  

        yesterday_top3_machines = [m for m in prev_top3_machines]

        forecast_date = data["日付"].max()

        print(f"\n機種名：{MACHINE_NAME}")
        print(f"予想日：{forecast_date.strftime('%Y-%m-%d')}")

        print("\n順位 | 台番 | 最終スコア | 貢献TOP3")
        print("-" * 75)

        # print("\n--- 2段移動 全体パターン ---")
        # print(
            # two_step_df
            # .groupby(["A→B", "B→C"])
            # .size()
            # .reset_index(name="回数")
            # .sort_values("回数", ascending=False)
            # .head(5)
        # )

        # print("\n--- 台番ごとの2段移動 A→B→C ---")
        # print(
            # two_step_df
            # .groupby(["A", "B", "C"])
            # .size()
            # .reset_index(name="回数")
            # .sort_values("回数", ascending=False)
            # .head(5)
        # )

        for rank, (_, row) in enumerate(df_result.iterrows(), start=1):
            target = int(row["台番"])
            recent_data = settings.tail(RECENT_DAYS)

            high_count = 0
            move_hit = 0
            stay_hit = 0
            revival_hit = 0

            target_col = f"{target}_設定"

            prev_setting = "-"

            prev_row = settings.iloc[-2]

            if target_col in prev_row.index:
                prev_setting = prev_row[target_col]

                if target_col in recent_data.columns:
                    high_count = (recent_data[target_col] >= HIGH_SETTING).sum()

                    # 据え置き：翌日も同じ台が設定4以上
                    for i in range(len(recent_data) - 1):
                        today_row = recent_data.iloc[i]
                        next_row = recent_data.iloc[i + 1]

                        if today_row[target_col] >= HIGH_SETTING:
                            if next_row[target_col] >= HIGH_SETTING:
                                stay_hit += 1

                            # 復活：1〜3日以内に再度設定4以上
                            for d in [1, 2, 3]:
                                if i + d < len(recent_data):
                                    future_row = recent_data.iloc[i + d]
                                    if future_row[target_col] >= HIGH_SETTING:
                                        revival_hit += 1
                                        break

                # 移動：隣 / 1つ飛び / 2つ飛び
                for i in range(len(recent_data) - 1):
                    today_row = recent_data.iloc[i]
                    next_row = recent_data.iloc[i + 1]

                    if target_col not in recent_data.columns:
                        continue

                    for other in TARGET_MACHINES:
                        other_col = f"{other}_設定"

                        if other_col not in recent_data.columns:
                            continue

                        if today_row[other_col] >= HIGH_SETTING and next_row[target_col] >= HIGH_SETTING:
                            diff = get_circle_diff(other, target, CIRCLE_ORDER)
                            if diff is None:
                                continue
                            diff = abs(diff)

                            if diff in [1, 2, 3]:
                                move_hit += 1
                                break

                # 移動・据え置き・復活のカウント処理が終わった後

                move_total = high_count
                stay_total = high_count
                revival_total = high_count

                move_rate = round(move_hit / move_total * 100, 1) if move_total > 0 else 0
                stay_rate = round(stay_hit / stay_total * 100, 1) if stay_total > 0 else 0
                revival_rate = round(revival_hit / revival_total * 100, 1) if revival_total > 0 else 0

                move_success_bonus = make_bonus(move_hit, RECENT_DAYS, BOOST_COEF)

                # =========================
                # 据え置きpt
                # =========================

                # stay_pt = 0

                # prev_setting_num = 0

                # if target_col in settings.columns:
                    # recent_values = settings[target_col].dropna().tail(7)

                    # 0除外
                    # recent_values = recent_values[recent_values != 0]

                    # if len(recent_values) > 0:
                        # prev_setting_num = float(recent_values.iloc[-1])

                # if prev_setting_num >= 4:
                    # stay_pt = round(
                        # prev_setting_num
                        # * stay_rate
                        # / 100
                        # * 10,
                        # 2
                    # )

                # =========================
                # 復活pt
                # =========================

                revival_pt = round(revival_rate / 100, 2)

                # =========================
                # 周期pt
                # =========================

                cycle_pt = 0

                try:
                    cycle_num = int(cycle_days)

                    if cycle_num == 1:
                        cycle_pt = 1.00

                    elif cycle_num == 2:
                        cycle_pt = 0.70

                    elif cycle_num == 3:
                        cycle_pt = 0.40

                except:
                    pass
                
                stay_score_bonus = make_bonus(stay_hit, RECENT_DAYS, BOOST_COEF)
                revival_bonus = make_bonus(revival_hit, RECENT_DAYS, BOOST_COEF)

                # =========================
                # 復活率 × 周期補正
                # =========================

                try:
                    cycle_num = int(cycle_days)

                    # 周期2〜5日は復活しやすい扱いで少し加点
                    if 2 <= cycle_num <= 5:
                        revival_bonus *= 1.10

                    # 周期6〜7日は少し弱め
                    elif 6 <= cycle_num <= 7:
                        revival_bonus *= 0.95

                    # 周期8日以上は復活期待を弱める
                    elif cycle_num >= 8:
                        revival_bonus *= 0.90

                except:
                    pass

                cycle_days = calc_cycle_days(settings, target)
                target_int = int(target)
                target_str = str(target)

                base_contrib = contrib.get(target_int, contrib.get(target_str, {}))

                if len(base_contrib) == 0:
                    top_str = "なし"
                else:
                    valid_contrib = {
                    k: v for k, v in base_contrib.items()
                    if v >= 1.0 and k in prev_top3
                }

                if len(valid_contrib) == 0:
                    top_str = "前日TOP3連動なし"
                    top_machine = int(prev_top3[0]) if len(prev_top3) > 0 else int(target)
                else:
                    top_items = sorted(
                        valid_contrib.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:3]

                    total = sum(v for _, v in top_items)

                    top_str = " / ".join(
                        f"{machine}({value:.1f})"
                        for machine, value in top_items
                    )

                    top_machine = top_items[0][0]

                    true_base_machine = int(top_items[0][0])
                    true_base_score = min(
                        round(float(top_items[0][1]), 1),
                        25.0
                    )

                    top_items = [(top_items[0][0], true_base_score)]

                    hybrid_result.loc[
                        hybrid_result["台番"] == target,
                        "本当の基準台"
                    ] = true_base_machine

                    hybrid_result.loc[
                        hybrid_result["台番"] == target,
                        "本当の基準スコア"
                    ] = true_base_score

                    base_score_display = min(round(float(top_items[0][1]), 1), 25.0)

                    print(
                        f"{rank:>2}位 | "
                        f"{target:>4} | "
                        f"{row['最終スコア']:>8.2f} | "
                        f"{top_str}"
                )

                if "総合pt" not in hybrid_result.columns:
                   hybrid_result["総合pt"] = hybrid_result["最終スコア"]    

                # print("=== HTMLに使うランキング ===")
                # print(html_result[["台番", "最終スコア"]])

                # ==========================
                # 罠台検出
                # 前日TOP3限定
                # ==========================
                trap_list = []

                prev_top3_set = set(prev_top3_machines)

                for machine in prev_top3_set:

                    col = f"{machine}_設定"

                    if col not in settings.columns:
                        continue

                    series = settings[col].dropna().tail(8)

                    for i in range(1, len(series)):

                        prev_set = series.iloc[i - 1]
                        curr_set = series.iloc[i]

                        if (
                            prev_set >= HIGH_SETTING
                            and curr_set < HIGH_SETTING
                        ):
                            trap_list.append(int(machine))
                            break

                html_cards = ""

                html_result = hybrid_result.copy().sort_values(
                    "総合pt",
                    ascending=False
                ).reset_index(drop=True)
                    
                for rank, (_, row) in enumerate(html_result.iterrows(), start=1):
                        target = int(row["台番"])
                        score = float(row["最終pt"])
                        top_str = "なし"
                        top_machine = target

                        # print("HTML表示:", rank, target, score)

                        recent_data = settings.tail(RECENT_DAYS)

                        target_col = f"{target}_設定"

                        high_count = 0
                        move_hit = 0
                        stay_hit = 0
                        revival_hit = 0

                        move_total = 0
                        stay_total = 0
                        revival_total = high_count

                        prev_setting = "-"

                        prev_row = settings.iloc[-2]
                        if target_col in prev_row.index:
                            prev_setting = prev_row[target_col]

                        prev_setting_num = 0

                        if target_col in settings.columns:

                            recent_values = pd.to_numeric(
                                settings[target_col],
                                errors="coerce"
                            ).dropna()

                             # 予想日(0)を除外
                            recent_values = recent_values[recent_values != 0]

                            # 最新7件
                            recent_values = recent_values.tail(7)

                            if len(recent_values) > 0:
                                prev_setting_num = float(recent_values.iloc[-1])

                            # if target == 1170:
                                # print("rank =", rank, "target =", target)    

                            stay_pt = 0

                            if prev_setting_num >= 4:
                                stay_pt = round(
                                    prev_setting_num
                                    * stay_rate
                                    / 100
                                    * 10,
                                    2
                                )

                            # hybrid_result.loc[
                                # hybrid_result["台番"] == target,
                                # "据え置きpt"
                            # ] = stay_pt    

                            # if target == 1170:
                                # print("1170 recent_values =", list(recent_values))
                                # print("1170 prev_setting_num =", prev_setting_num)
                                # print("1170 stay_rate =", stay_rate)
                                # print("1170 stay_pt =", stay_pt)    
                        

                        recent_setting_str = "-"

                        if target_col in settings.columns:
                            recent_values = settings[target_col].dropna()

                            # 予想日の0は除外して、前日までを直近設定にする
                            if len(recent_values) > 0 and recent_values.iloc[-1] == 0:
                                recent_values = recent_values.iloc[:-1]

                            # 直近設定は0も表示する
                            recent_values = recent_values.tail(7)

                            if len(recent_values) > 0:
                                recent_setting_str = "→".join(str(int(v)) for v in recent_values)    

                        if target_col in recent_data.columns:
                            high_count = int((recent_data[target_col] >= HIGH_SETTING).sum())

                            move_total = high_count
                            stay_total = high_count
                            revival_total = 0

                            for i in range(len(recent_data) - 1):
                                today_row = recent_data.iloc[i]
                                next_row = recent_data.iloc[i + 1]

                                if today_row[target_col] >= HIGH_SETTING:
                                    if next_row[target_col] >= HIGH_SETTING:
                                        stay_hit += 1

                                    for other in TARGET_MACHINES:
                                        other_col = f"{other}_設定"
                                        if other_col not in recent_data.columns:
                                            continue

                                        if other == target:
                                            continue

                                        diff = get_circle_diff(target, other, CIRCLE_ORDER)
                                        if diff is None:
                                            continue
                                        diff = abs(diff)

                                        if diff in [1, 2, 3] and next_row[other_col] >= HIGH_SETTING:
                                            move_hit += 1
                                            break

                                    # =========================
                                    # 復活判定
                                    # ・翌日低設定
                                    # ・2日後 or 3日後に復活
                                    # =========================

                                    # 翌日確認
                                    if i + 1 < len(recent_data):

                                        next_row = recent_data.iloc[i + 1]

                                        # 翌日が低設定
                                        if next_row[target_col] < HIGH_SETTING:

                                            revival_total += 1

                                            revived = False

                                            # 2日後
                                            if i + 2 < len(recent_data):
                                                day2_row = recent_data.iloc[i + 2]

                                                if day2_row[target_col] >= HIGH_SETTING:
                                                    revived = True

                                            # 3日後
                                            if not revived and i + 3 < len(recent_data):
                                                day3_row = recent_data.iloc[i + 3]

                                                if day3_row[target_col] >= HIGH_SETTING:
                                                    revived = True

                                            if revived:
                                                revival_hit += 1

                        move_rate = round(move_hit / move_total * 100, 1) if move_total > 0 else 0
                        stay_rate = round(stay_hit / stay_total * 100, 1) if stay_total > 0 else 0
                        revival_rate = round(revival_hit / revival_total * 100, 1) if revival_total > 0 else 0

                        cycle_days = calc_cycle_days(settings, target)

                        # ===== 周期補正 =====

                        try:
                            cycle_num = int(cycle_days)

                            if cycle_num <= 7:
                                pass

                            else:
                                over_blocks = (cycle_num - 7) // 7 + 1
                                pass

                        except:
                            pass

                        if len(base_contrib) == 0:
                            if len(prev_top3_machines) > 0:
                                top_machine = int(prev_top3_machines[0])
                                top_str = f"{top_machine}(基準)"
                            else:
                                top_machine = target
                                top_str = "前日TOP3なし"

                        else:
                            # =========================
                            # 前日TOP3の中だけを候補にする
                            # =========================

                            # 前日TOP3を数値化
                            prev_top3_int = [int(x) for x in prev_top3_machines]

                            # 前日TOP3の中だけを候補にする
                            valid_contrib = {
                                int(k): v
                                for k, v in base_contrib.items()
                                if int(k) in prev_top3_int
                            }

                        # 前日TOP3の中から、貢献がある台だけ表示する
                            if len(valid_contrib) > 0:

                                top_items = sorted(
                                    valid_contrib.items(),
                                    key=lambda x: float(x[1]),
                                    reverse=True
                                )[:3]

                                # print("top_items =", top_items)

                                top_machine = int(top_items[0][0])
                                base_score_display = min(round(float(top_items[0][1]), 2), 25.0)

                            else:

                                top_machine = int(prev_top3_machines[0]) if len(prev_top3_machines) > 0 else int(target)
                                base_score_display = 0.0

                            link_hit = 0
                            link_total = 0

                            base_col = f"{top_machine}_設定"
                            target_col = f"{target}_設定"

                            if base_col in recent_data.columns and target_col in recent_data.columns:
                                for i in range(len(recent_data) - 1):
                                    today_row = recent_data.iloc[i]
                                    next_row = recent_data.iloc[i + 1]

                                    if today_row[base_col] >= HIGH_SETTING:
                                        link_total += 1

                                        if next_row[target_col] >= HIGH_SETTING:
                                            link_hit += 1

                            link_rate = round(link_hit / link_total * 100, 1) if link_total > 0 else 0
                            
                        move_success_bonus = 1.0
                        stay_score_bonus = 1.0

                        if move_rate > 0:
                            move_success_bonus = 1.0 + (move_rate / 100) * 0.30

                        # 前日Top3台は据え置き補正を無効
                        if machine in prev_top3_machines:
                            stay_score_bonus = 1.00

                        # =========================
                        # 据え置き補正（重複加点防止）
                        # =========================

                        # 前日Top3台は据え置き補正なし
                        if machine in prev_top3_machines:
                            stay_score_bonus = 1.00

                        # 前日高設定時のみ据え置き率を適用
                        try:
                            prev_setting = float(prev_setting)
                        except:
                            prev_setting = 0
                        if prev_setting >= HIGH_SETTING:

                            if stay_rate >= 35:
                                stay_score_bonus = 1.20

                            elif stay_rate >= 25:
                                stay_score_bonus = 1.10

                            elif stay_rate <= 10:
                                stay_score_bonus = 0.85

                            else:
                                stay_score_bonus = 1.00

                        # 前日低設定なら据え置き補正なし
                        else:
                            stay_score_bonus = 1.00

                        link_hit = 0
                        link_total = 0

                        base_col = f"{top_machine}_設定"
                        target_col = f"{target}_設定"

                        if base_col in recent_data.columns and target_col in recent_data.columns:
                            for i in range(len(recent_data) - 1):
                                today_row = recent_data.iloc[i]
                                next_row = recent_data.iloc[i + 1]

                                if today_row[base_col] >= HIGH_SETTING:
                                    link_total += 1

                                    if next_row[target_col] >= HIGH_SETTING:
                                        link_hit += 1

                        link_rate = round(link_hit / link_total * 100, 1) if link_total > 0 else 0

                        # ===== 前日TOP3連動補正 =====
                        # link_bonus = 1.0

                        # 前日実績TOP3から来ている時
                        if top_machine in prev_top3_machines and top_machine != target:
                            pass

                        # 自己連動
                        elif top_machine == target:
                            pass

                        # その他
                        else:
                                pass

                        # ===== HTML表示用 =====

                        score = float(row["最終pt"])
                        # pt = float(row["final_pt"])

                        true_base_machine_raw = row.get("本当の基準台", top_machine)
                        true_base_score_raw = row.get("本当の基準スコア", 0)

                        if pd.isna(true_base_machine_raw):
                            true_base_machine = int(top_machine)
                        else:
                            true_base_machine = int(true_base_machine_raw)

                        if pd.isna(true_base_score_raw):
                            true_base_score = 0.0
                        else:
                            true_base_score = min(
                            round(float(true_base_score_raw), 1),
                            25.0
                        )

                        # 基準台スコア表示用
                        base_score = float(row.get("基準台スコア", 0))

                        # 前日Top3台一覧
                        prev_top3_machines = prev_top3

                        trap_list = [
                            x for x in trap_list
                            if x not in revival
                        ]

                        # print("罠台候補:", trap_list)

                        # TOP3基準台
                        top1_machine = prev_top3_machines[0] if len(prev_top3_machines) > 0 else "-"
                        top2_machine = prev_top3_machines[1] if len(prev_top3_machines) > 1 else "-"
                        top3_machine = prev_top3_machines[2] if len(prev_top3_machines) > 2 else "-"

                        # =========================
                        # 9本連動pt計算
                        # top1〜top3 × 3日前〜1日前
                        # =========================

                        link_scores = []
                        link_html = ""

                        for top_rank in range(1, 4):
                            link_html += f"<div class='machine_rank_list'><b>top{top_rank} 連動</b><br>"

                            for days_ago in [3, 2, 1]:
                                top_setting = 0
                                top_machine = None

                                day_scores = get_valid_top_scores(settings, forecast_date, days_ago, machines)

                                if len(day_scores) >= top_rank:
                                    top_machine = int(day_scores[top_rank - 1][0])
                                    top_setting = day_scores[top_rank - 1][1]

                                if top_machine is not None:
                                    link_rate, link_total = calc_recent_move_rate(settings, top_machine, target)
                                    link_hit = round(link_rate * link_total / 100)

                                    # 1段目：純連動
                                    link_pt = round(
                                        top_setting * link_rate / 100,
                                        2
                                    )

                                    # 2段目：日別係数込み
                                    link_day_pt = round(
                                        link_pt * DAY_COEFFICIENTS[days_ago],
                                        2
                                    )

                                    # 3段目：倍率反映
                                    link_weight_pt = round(
                                        link_day_pt * LINK_WEIGHT_COEF,
                                        2
                                    )

                                else:
                                    link_rate = 0
                                    link_total = 0
                                    link_hit = 0
                                    link_score = 0

                                link_scores.append(link_weight_pt)

                                link_html += (
                                    f"<div class='link-line'>"
                                    f"{top_setting} {top_machine}（{days_ago}日前）→{target}　"
                                    f"連動率：{link_hit}/{link_total} ({link_rate:.0f}%)　"
                                    f"pt：{link_weight_pt:.2f}"
                                    f"</div>"
                                )

                            link_html += "</div>"

                        link_total_weight_pt = round(
                            sum(link_scores),
                            2
                        )

                        standard_score = round(
                            float(old_standard_map.get(target, row["標準スコア"])),
                            2
                        )
                        standard_penalty = 0

                        try:
                            target_int = int(target)
                        except:
                            target_int = target

                        standard_penalty = 0.0

                        if target_int in trap_list:
                            standard_penalty = 8.0

                        standard_score = round(
                            standard_score - standard_penalty,
                            2
                        )

                        total_pt = round(
                            standard_score +
                            link_total_weight_pt,
                            2
                        )

                        # print(
                            # target,
                            # "link_total_pt=", link_total_pt,
                            # "final_pt=", final_pt,
                            # "link_weight_pt=", link_weight_pt,
                            # "total_pt=", total_pt
                        # )

                        hybrid_result.loc[
                            hybrid_result["台番"] == target,
                            "standard_pt"
                        ] = standard_score

                        hybrid_result.loc[
                            hybrid_result["台番"] == target,
                            "link_total_weight_pt"
                        ] = link_total_weight_pt

                        hybrid_result.loc[
                            hybrid_result["台番"] == target,
                            "総合pt"
                        ] = total_pt

                        # print("罠台確認", target, target_int, trap_list, standard_penalty, total_pt)

                        # 総合pt順位MAPを先に作成
                        final_rank_result = hybrid_result.sort_values(
                            "総合pt",
                            ascending=False
                        ).reset_index(drop=True)

                        for _, rr in final_rank_result.iterrows():

                            all_top15.append({
                                "機種": MACHINE_NAME,
                                "台番": int(rr["台番"]),
                                "総合pt": float(rr["総合pt"]),
                                "standard_pt": float(rr["standard_pt"]),
                                "link_total_weight_pt": float(rr["link_total_weight_pt"])
                            })

                        rank_map = {}

                        for r, (_, rr) in enumerate(final_rank_result.iterrows(), start=1):
                            rank_map[int(rr["台番"])] = r

                        # =========================
                        # 基準台表示用：前日TOP3の中で最も貢献した台
                        # =========================

                        prev_top3_int = [int(x) for x in prev_top3_machines]

                        # HTML表示直前で据え置きptを再計算
                        stay_pt_display = stay_pt

                        try:
                            display_prev_setting = float(
                                str(recent_setting_str).split("→")[-1]
                            )
                        except:
                            display_prev_setting = None

                        display_stay_pt = 0

                        if display_prev_setting is not None and display_prev_setting >= 4:
                            display_stay_pt = round(
                                display_prev_setting * stay_rate / 100,
                                2
                            )

                        # standard_pt保存
                        hybrid_result.loc[
                            hybrid_result["台番"] == target,
                            "standard_pt"
                        ] = standard_score

                        # link_pt保存
                        hybrid_result.loc[
                            hybrid_result["台番"] == target,
                            "link_pt"
                        ] = link_weight_pt

                        # 総合pt保存
                        hybrid_result.loc[
                            hybrid_result["台番"] == target,
                            "総合pt"
                        ] = total_pt

                        html_cards += f"""
                        <div class="card">
                            <div class="rank">{rank}位：{target}番台 [{get_island(target)}]</div>

                            <div>総合pt：<span class="score">{total_pt:.2f}</span></div>

                            <div>
                                standard_スコア：{standard_score}<br>
                                link_t/w_pt：{link_total_weight_pt}<br>
                                基準台：{true_base_machine}(基準)
                            </div>

                            {link_html}

                            <div>据え置き率：{stay_rate}% ({stay_hit}/{stay_total})</div>
                            <div>復活率：{revival_rate}% ({revival_hit}/{revival_total})</div>
                            <div>復活検出：
{
                                '<span class="detect-text">検出あり</span>'
                                if target in revival
                                else '検出なし'
                            }
                            </div>

                            <div>罠台検出：
                            {
                                '<span class="detect-text">検出あり</span>'
                                if target in trap_list
                                else '検出なし'
                            }
                            </div>
                            <div>高設定回数：{high_count}回 ({high_count}/{RECENT_DAYS})</div>
                            <div>直近設定：{recent_setting_str}</div>
                            <div>周期：{cycle_days}日</div>
                        </div>
                        """
                        
                         # 台番順位一覧作成
                        if rank == 1:
                            rank_map = {}

                            final_rank_result = hybrid_result.sort_values(
                                "総合pt",
                                ascending=False
                            ).reset_index(drop=True)

                            html_result = final_rank_result.copy()

                            for r, (_, rr) in enumerate(final_rank_result.iterrows(), start=1):
                                rank_map[int(rr["台番"])] = r

                            rank_list_html = "<div class='machine_rank_list'><b>台番順位一覧</b><br>"

                            top3_html = ""

                            if len(final_rank_result) >= 3:
                                top1 = final_rank_result.iloc[0]
                                top2 = final_rank_result.iloc[1]
                                top3 = final_rank_result.iloc[2]

                                top3_html = f"""
                            <div class="top3-box">
                            ━━━━━━━━━━<br>
                            🥇本命　{int(top1["台番"])}（{top1["総合pt"]:.1f}pt）<br>
                            🥈対抗　{int(top2["台番"])}（{top2["総合pt"]:.1f}pt）<br>
                            🥉穴　　{int(top3["台番"])}（{top3["総合pt"]:.1f}pt）<br>
                            ━━━━━━━━━━
                            </div>
                            """

                            for machine in sorted(rank_map.keys()):
                                rnk = rank_map[machine]

                                if rnk <= 5:
                                    rank_list_html += f"{machine}:<span class='rank_top3'>{rnk}位</span>　"
                                else:
                                    rank_list_html += f"{machine}:{rnk}位　"

                                if (machine - min(rank_map.keys()) + 1) % 7 == 0:
                                    rank_list_html += "<br>"

                            rank_list_html += "</div><br>"

                            # 総合TOP15作成
                            top15_html = """
                            <div class='top15_box'>
                            <b>総合TOP15</b><br>
                            """

                            for r, (_, rr) in enumerate(final_rank_result.head(15).iterrows(), start=1):

                                top15_html += (
                                    f"{r}位 "
                                    f"{int(rr['台番'])}番 "
                                    f"({rr['総合pt']:.1f}pt)"
                                    "<br>"
                                )

                            top15_html += "</div><br>"

                        section_id = SECTION_ID

                        revival_html = ""

                        if revival:
                            revival_html = (
                                "<div class='revival-box'>"
                                "<div class='revival-title'>復活検出</div>"
                                "<div class='revival-number'>"
                                + "、".join(map(str, revival))
                                + "</div></div>"
                            )
                        else:
                            revival_html = (
                                "<div class='revival-box'>"
                                "<div class='revival-title'>復活検出</div>"
                                "<div class='revival-number'>なし</div>"
                                "</div>"
                            )

                        trap_html = ""

                        if trap_list:
                            trap_html = (
                                "<div class='trap-box'>"
                                "<div class='trap-title'>罠台検出</div>"
                                "<div class='trap-number'>"
                                + "、".join(map(str, trap_list))
                                + "</div></div>"
                            )
                        else:
                            trap_html = (
                                "<div class='trap-box'>"
                                "<div class='trap-title'>罠台検出</div>"
                                "<div class='trap-number'>なし</div>"
                                "</div>"
                            )
                        
                        html_sections[section_id] = f"""

                                <div class="section" id="{section_id}">
                                <h2>【LINK】{MACHINE_NAME}</h2>
                                <p>予想日：{forecast_date.strftime('%Y-%m-%d')}</p>
                                {make_prev_top3_html(settings, prev_top3, data)}
                                {revival_html}
                                {trap_html}
                                {top3_html}
                                {rank_list_html}
                                {html_cards}
                                </div> 
                                """
            # Aの日 → Bの翌日 → Cの翌々日 を見る

            if "two_step_df" not in locals() or len(two_step_df) == 0:
                print("2段移動データなし")
                
            latest_date = data_sorted["日付"].max()
            recent_sorted = data_sorted[data_sorted["日付"] >= latest_date - pd.Timedelta(days=30)]

            recent_two_step = []

            for i in range(len(recent_sorted) - 2):
                day_a = recent_sorted.iloc[i]
                day_b = recent_sorted.iloc[i + 1]
                day_c = recent_sorted.iloc[i + 2]

                for col_a in setting_cols:
                    if pd.notna(day_a[col_a]) and day_a[col_a] >= HIGH_SETTING:
                        machine_a = int(col_a.split("_")[0])

                        for col_b in setting_cols:
                            if pd.notna(day_b[col_b]) and day_b[col_b] >= HIGH_SETTING:
                                machine_b = int(col_b.split("_")[0])

                                for col_c in setting_cols:
                                    if pd.notna(day_c[col_c]) and day_c[col_c] >= HIGH_SETTING:
                                        machine_c = int(col_c.split("_")[0])

                                        recent_two_step.append({
                                            "A": machine_a,
                                            "B": machine_b,
                                            "C": machine_c,
                                            "A→B": machine_b - machine_a,
                                            "B→C": machine_c - machine_b,
                                            "A→C": machine_c - machine_a
                                        })

                    recent_two_step_df = pd.DataFrame(recent_two_step)

            # if len(recent_two_step_df) == 0:
                # print("直近30日の2段移動データなし")
            # else:
                # print(
                    # recent_two_step_df
                    # .groupby(["A", "B", "C"])
                    # .size()
                    # .reset_index(name="回数")
                    # .sort_values("回数", ascending=False)
                    # .head(5)
                # )

        # ===== 共通CSS =====
        common_style = """
        <style>
        body {
            font-family: sans-serif;
            background: #f5f5f5;
            padding: 16px;
            margin: 0;
            box-sizing: border-box;
            overflow-x: hidden;
        }
        h1 {
        font-size: 28px;
        }
        h2 {
        font-size: 24px;
        }
        .predict-date{
            font-size:18px;
            font-weight:bold;
            margin-bottom:18px;
            color:#444;
        }
        .menu-button {
        display: block;
        background: #333;
        color: white;
        text-decoration: none;
        text-align: center;
        padding: 18px;
        margin: 16px 0;
        border-radius: 12px;
        font-size: 24px;
        font-weight: bold;
        }
        .link-row{
            margin-top:10px;
            line-height:1.4;
        }

        .link-rate{
            color:#1565ff;
            font-weight:bold;
            margin-left:20px;
        }
        .back {
        display: block;
        margin-bottom: 16px;
        color: #333;
        font-size: 18px;
        }

        .machine_rank_list{
            font-size:14px;
            line-height:1.8;
            margin-bottom:15px;
        }
        .rank_top3{
            color:#d00000;
            font-weight:bold;
        }

        .total-card{
            background:white;
            border-radius:12px;
            padding:14px;
            margin:12px 0;
            box-shadow:0 2px 8px rgba(0,0,0,0.12);
        }

        .total-rank{
            font-size:22px;
            font-weight:bold;
        }

        .total-main{
            font-size:28px;
            font-weight:bold;
            margin-top:4px;
        }

        .total-main span{
            font-size:18px;
        }

        .total-score{
            font-size:22px;
            font-weight:bold;
            color:#d60000;
            margin-top:6px;
        }

        .total-sub{
            font-size:18px;
            margin-top:4px;
        }

        .card {
            background: white;
            border-radius: 10px;
            padding: 14px;
            margin: 14px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.12);
            box-sizing: border-box;
            width: 100%;
            max-width: 100%;
        }
        .rank {
        font-size: 26px;
        font-weight: bold;
        }
        .score {
        color: #d00000;
        font-weight: bold;
        }
        .prev-top3-box {
            background: #fff8dc;
            border-left: 5px solid orange;
            padding: 4px;
            margin-bottom: 8px;
            border-radius: 8px;
            font-size: 14px;
        }

        .card {
            width: 100%;
            max-width: none;
            box-sizing: border-box;
            display: block;
            clear: both;
            float: none;
        }

        @media screen and (max-width: 600px) {
            body {
                padding: 10px;
                overflow-x: hidden;
            }

            .card {
                width: 100%;
                max-width: 100%;
                margin: 12px 0;
                padding: 14px;
                box-sizing: border-box;
            }

            .link-line {
                white-space: normal;
                word-break: keep-all;
            }
        }

        html, body {
            width: 100%;
            max-width: 100%;
            overflow-x: hidden;
        }

        body > div,
        .section {
            display: block;
            width: 100%;
            max-width: 100%;
            clear: both;
        }

        .card {
            display: block !important;
            width: 100% !important;
            max-width: 100% !important;
            margin: 12px 0 !important;
            float: none !important;
            clear: both !important;
        }

        .card .card {
            margin-left: 0 !important;
            margin-right: 0 !important;
            width: 100% !important;
            max-width: 100% !important;
        }

        .section > .card {
            margin-left: 0 !important;
            width: 100% !important;
        }
        
        .revival-box{
            margin-top:8px;
            margin-bottom:8px;
        }

        .revival-title{
            font-size:22px;
            font-weight:bold;
            margin-bottom:4px;
        }

        .revival-number{
            font-size:18px;
            color:#0066ff;
            font-weight:bold;
        }

        .trap-box{
            margin-top:8px;
            margin-bottom:8px;
        }

        .trap-title{
            font-size:22px;
            font-weight:bold;
            margin-bottom:4px;
        }

        .trap-number{
            font-size:18px;
            color:#0066ff;
            font-weight:bold;
        }

        .revival-title,
        .trap-title{
            font-size:20px;
            font-weight:bold;
            margin-top:10px;
            margin-bottom:4px;
        }

        .revival-number,
        .trap-number{
            font-size:18px;
            color:#0066ff;
            font-weight:bold;
            margin-bottom:10px;
        }

        .detect-text{
            color:#0066ff;
            font-weight:bold;
        }

        </style>
        """

        all_top15_df = pd.DataFrame(all_top15)

        # 機種＋台番の重複を1つにまとめる
        all_top15_df = (
            all_top15_df
            .groupby(["機種", "台番"], as_index=False)[["総合pt", "standard_pt", "link_total_weight_pt"]]
            .max()
        )

        all_top15_df = (
            all_top15_df
            .sort_values("総合pt", ascending=False)
            .head(15)
        )

        total_top15_html = "<h2>全機種総合TOP15</h2>"

        for i, (_, r) in enumerate(all_top15_df.iterrows(), start=1):
            medal = ""
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"

            total_top15_html += f"""
            <div class="total-card">
            <div class="total-rank">{medal} {i}位</div>
            <div class="total-main">{int(r['台番'])}番台 <span>({r['機種']})</span></div>
            <div class="total-score">総合pt：{r['総合pt']:.1f}pt</div>
            <div class="total-sub">
            standard_スコア:{r['standard_pt']:.1f}
            link_t/w_pt:{r['link_total_weight_pt']:.1f}
            </div>
            </div>
            """

        total_top_html = f"""   
        <!DOCTYPE html>
        <html lang="ja">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>総合TOP</title>
        {common_style}
        </head>
        <body>

        <a class="back" href="index_link.html">← メニューへ戻る</a>

        <h1>総合TOP</h1>

        <div class="predict-date">
        予想日：{forecast_date.strftime('%Y-%m-%d')}
        </div>

        {total_top15_html}

        </body>
        </html>
        """

        with open("total_top_link.html", "w", encoding="utf-8") as f:
            f.write(total_top_html)    

        # ===== メニュー画面 index.html =====
        index_html = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>LINK</title>
        {common_style}
        </head>
        <body>

        <h1>LINK</h1>

        <a class="menu-button" href="total_top_link.html">総合TOP</a>

        <a class="menu-button" href="god_link.html">GOD</a>
        <a class="menu-button" href="vvv_link.html">VVV2</a>
        <a class="menu-button" href="okidoki_link.html">沖ドキ</a>
        <a class="menu-button" href="tokyo_link.html">東京喰種</a>
        <a class="menu-button" href="hokuto_link.html">北斗の拳</a>

        </body>
        </html>
        """

        html_page = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{MACHINE_NAME}LINK</title>
        {common_style}
        </head>
        <body>

        <a class="back" href="index_link.html">← メニューへ戻る</a>

        {html_sections.get(SECTION_ID, "")}

        </body>
        </html>
        """

        with open("index_link.html", "w", encoding="utf-8") as f:
            f.write(index_html)

        with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
            f.write(html_page)

        print("HTMLを作成しました")

        # =========================
        # TODAY INDEX 作成
        # =========================

        today_index_html = f"""
        <html>

        <head>

        <meta charset="utf-8">

        <style>

        body {{
            background:#f5f5f5;
            font-family:Meiryo;
            padding:30px;
        }}

        .title {{
            font-size:48px;
            font-weight:bold;
            margin-bottom:30px;
        }}

        .card {{

            background:#2d2d2d;
            color:white;

            border-radius:15px;

            padding:40px;

            margin-bottom:20px;

            text-align:center;

            font-size:28px;

            font-weight:bold;

            cursor:pointer;

            transition:0.2s;
        }}

        .card:hover {{
            transform:scale(1.02);
        }}

        a {{
            text-decoration:none;
        }}

        </style>

        </head>

        <body>

        <div class="title">
        TODAY
        </div>

        <a href="god_today.html">
        <div class="card">
        GOD_today
        </div>
        </a>

        <a href="vvv_today.html">
        <div class="card">
        VVV2_today
        </div>
        </a>

        <a href="okidoki_today.html">
        <div class="card">
        沖ドキ_today
        </div>
        </a>

        <a href="tokyo_today.html">
        <div class="card">
        東京喰種_today
        </div>
        </a>

        <a href="hokuto_today.html">
        <div class="card">
        北斗の拳_today
        </div>
        </a>

        </body>

        </html>
        """

        with open("index_today.html", "w", encoding="utf-8") as f:
            f.write(today_index_html)

        print("TODAY INDEX 作成完了")

        # =========================
        # 当日連動率HTML 作成
        # =========================

        def calc_same_day_link_rate(
            df,
            machine_col="台番号",
            date_col="日付",
            setting_col="設定",
            target_settings=(3, 4, 5, 6),
            days=45
        ):

            df = df.copy()

            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

            max_date = df[date_col].max()
            start_date = max_date - pd.Timedelta(days=days - 1)

            df = df[
                (df[date_col] >= start_date)
                & (df[date_col] <= max_date)
            ]

            result_rows = []

            # 対象日ごとの高設定台
            high_by_day = {}

            for _, row in df.iterrows():

                date = row[date_col]

                high_machines = []

                for machine in TARGET_MACHINES:

                    col = f"{machine}_設定"

                    if col not in df.columns:
                        continue

                    val = row[col]

                    try:
                        val = float(val)
                    except:
                        continue

                    if val >= 3:
                        high_machines.append(machine)

                high_by_day[date] = high_machines

            for base in TARGET_MACHINES:

                base_days = []

                for date, highs in high_by_day.items():

                    if base in highs:
                        base_days.append(date)

                base_count = len(base_days)

                if base_count == 0:
                    continue

                link_count = {}

                for date in base_days:

                    highs = high_by_day[date]

                    for other in highs:

                        if other == base:
                            continue

                        if other not in link_count:
                            link_count[other] = 0

                        link_count[other] += 1

                for other, cnt in link_count.items():

                    rate = cnt / base_count

                    result_rows.append({
                        "基準台": base,
                        "連動台": other,
                        "連動率": f"{cnt}/{base_count} ({rate:.0%})"
                    })

            return pd.DataFrame(result_rows)


        today_link_df = calc_same_day_link_rate(data)

        today_link_df["rate_num"] = (
            today_link_df["連動率"]
            .str.extract(r"\((\d+)%\)")
            .astype(int)
        )

        today_link_df = today_link_df.sort_values(
            ["基準台", "rate_num"],
            ascending=[True, False]
        )

        today_link_df = today_link_df.drop(columns=["rate_num"])

        rows_html = ""

        current_base = None
        toggle = False

        for _, row in today_link_df.iterrows():

            base = row["基準台"]

            if base != current_base:
                toggle = not toggle
                current_base = base

            bg = "#111111" if toggle else "#444444"

            rate_text = row["連動率"]

            try:
                rate_num = int(
                    str(rate_text).split("(")[-1].replace("%)", "")
                )
            except:
                rate_num = 0

            rate_color = "#ff4d4d" if rate_num >= 50 else "white"

            rows_html += f"""
            <tr style="background:{bg};">
                <td>{row['基準台']}</td>
                <td>{row['連動台']}</td>
                <td style="color:{rate_color}; font-weight:bold;">
                    {row['連動率']}
                </td>
            </tr>
            """

        today_html_table = f"""
        <table>

        <tr>
        <th>基準台</th>
        <th>連動台</th>
        <th>連動率</th>
        </tr>

        {rows_html}

        </table>
        """

        today_html = f"""
        <html>
        <head>
        <meta charset="utf-8">

        <style>

        body {{
            background:#111;
            color:white;
            font-family:Meiryo;
            padding:20px;
        }}

        table {{
            border-collapse: collapse;
            width:100%;
            margin:auto;
        }}

        th, td {{
            border:1px solid #555;
            padding:20px;
            text-align:center;
            font-size:24px;
        }}

        th {{
            background:#333;
        }}

        h1 {{
            font-size:24px;
        }}

        .back {{

            display:inline-block;
            margin-bottom:20px;
            color:white;
            text-decoration:none;
            font-size:24px;
        }}

        </style>

        </head>

        <body>

        <a class="back" href="index_today.html">
        ← メニューへ戻る
        </a>

        <h1>{MACHINE_NAME} 当日連動率_45日間</h1>

        {today_html_table}

        </body>
        </html>
        """

        with open(OUTPUT_TODAY_HTML, "w", encoding="utf-8") as f:
            f.write(today_html)

        print(f"{MACHINE_NAME} TODAY HTML 作成完了")
