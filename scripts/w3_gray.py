#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
w3_gray.py — 《W3》灰度风险评定引擎（每日抽检模式）

子命令:
  sample           从 20 人名册中抽出今日 6-7 人（最久未查优先 + 日期种子随机，当日可复现）
  record           把一条违规记入台账（自动按规则表判定等级与累计后果）
  quality          记录一人当日聊天质量六维评分（总分/档位自动计算，联动灰度台账）
  quality-summary  汇总当月（或指定月）各成员质量档位分布与均分
  status           汇总当月（或指定月）各成员累计违规与绩效影响
  rules            打印规则速查表

数据文件（均在本 skill 的 assets/w3/ 下，自动创建/追加）:
  roster.csv            名册: name,servers,active
  data/sample_history.csv   每日抽样记录: date,names
  data/violation_ledger.csv 违规台账: date,name,server,type,ordinal,level,evidence,notes
  data/quality_log.csv      质量评分: date,name,server,d1..d6,total,grade,issues,evidence,notes

规则依据: references/w3-gray-assessment.md（源: 《W3》灰度风险评定与处理措施.docx）
          references/w3-chat-quality.md（聊天质量六维评分与高中低分档）
退出码: sample/status/quality-summary 正常结束为 0；record/quality 的参数不存在时为 2。
"""

import argparse
import csv
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(__file__).resolve().parent.parent / "assets" / "w3"
ROSTER = BASE / "roster.csv"
DATA = BASE / "data"
HISTORY = DATA / "sample_history.csv"
LEDGER = DATA / "violation_ledger.csv"
QUALITY_LOG = DATA / "quality_log.csv"
QUALITY_HEADER = ["date", "name", "server", "d1", "d2", "d3", "d4", "d5", "d6",
                  "total", "grade", "issues", "evidence", "notes"]

# 聊天质量六维（满分 100，扣分制；规则书 references/w3-chat-quality.md）
QUALITY_DIMS = [
    ("d1", "响应及时性", 20), ("d2", "准确性与专业度", 25), ("d3", "教学引导", 15),
    ("d4", "联盟管理/协调", 15), ("d5", "话术规范", 15), ("d6", "服务态度/共情", 10),
]

# ---------------------------------------------------------------- 规则表

TYPES = {
    # key: (中文名, family, 直接触发等级, 处理说明)
    "copy_private": ("话术复制粘贴(私聊)", "immediate", "三级",
                     "同句5分钟内≥10次，单次直接三级；当月绩效×0.9 + 通报批评"),
    "copy_channel": ("话术复制粘贴(世界/联盟频道)", "window30", "三级",
                     "同句5分钟内≥3次且同一账号30天内第3次 → 三级；当月绩效×0.9 + 通报批评"),
    "recall_unnoticed": ("发中文后撤回(玩家未察觉)", "monthly", "",
                         "自然月第1次: 群内+开会通报+扣10分; 第2次: 三级(绩效×0.9)+通报批评"),
    "activity_unnoticed": ("发送中文活动消息(未被察觉)", "monthly", "",
                           "自然月第1次: 群内+开会通报+扣10分; 第2次: 三级(绩效×0.9)+通报批评"),
    "recall_noticed": ("发中文后撤回(玩家发现并询问)", "immediate", "二级",
                       "单次构成二级；当月绩效上限×0.8 + 通报批评"),
    "image_chinese_time": ("发送图片含中文和时间", "immediate", "红线",
                           "绩效清零"),
    "political": ("政治敏感内容", "immediate", "一级",
                  "即使被系统拦截也构成；当月绩效×0.5(未造成重大后果)/劝退(重大后果) + 通报批评"),
    "insult_unapproved": ("辱骂/阴阳玩家(未报备回击)", "immediate", "一级",
                          "未报备擅自回击；当月绩效×0.5或劝退 + 通报批评（报备获批的回击不算灰度，不要记台账）"),
    "no_recall": ("发送中文未撤回", "immediate", "一级",
                  "单次直接一级；当月绩效×0.5(未造成重大后果)/劝退(重大后果) + 通报批评"),
}
MONTHLY_FAMILY = ("recall_unnoticed", "activity_unnoticed")  # 月度累计共用次数

LEVEL_EFFECT = {
    "红线": "绩效清零",
    "一级": "当月绩效×0.5（未造成重大后果）/ 劝退（造成重大后果）+ 通报批评",
    "二级": "当月绩效上限×0.8 + 通报批评",
    "三级": "当月绩效×0.9 + 通报批评",
    "通报+扣10分": "群内+开会通报 + 扣10分（不乘绩效系数）",
}


def find_type(name_or_key):
    q = name_or_key.strip()
    if q in TYPES:
        return q
    for k, (cn, *_rest) in TYPES.items():
        if q == cn or q in cn or cn in q:
            return k
    return None


# ---------------------------------------------------------------- IO

def read_csv_rows(path, header):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.DictReader(f)]


def append_csv_row(path, header, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        if new:
            w.writeheader()
        w.writerow(row)


def load_roster():
    rows = read_csv_rows(ROSTER, ["name", "servers", "active"])
    if not rows:
        raise SystemExit(f"错误: 名册为空或不存在 {ROSTER}（name,servers,active 三列）")
    return [r for r in rows if r.get("active", "yes").strip().lower() not in ("no", "false", "0")]


def load_ledger():
    return read_csv_rows(LEDGER, ["date", "name", "server", "type", "ordinal", "level", "evidence", "notes"])


# ---------------------------------------------------------------- sample

def cmd_sample(args):
    today = date.today()
    roster = [r["name"].strip() for r in load_roster()]
    if len(roster) < int(str(args.n).split("-")[-1]):
        raise SystemExit(f"错误: 在册活跃人数 {len(roster)} 少于抽样人数")

    rng = random.Random(f"w3-{today.isoformat()}")
    n = rng.choice([6, 7]) if args.n == "6-7" else int(args.n)

    # 当日已抽样则直接返回（幂等）
    for row in read_csv_rows(HISTORY, ["date", "names"]):
        if row["date"] == today.isoformat():
            picked = [x for x in row["names"].split(";") if x]
            print(f"今日({row['date']})已抽过，名单（幂等返回，--force 可重抽）:")
            for i, p in enumerate(picked, 1):
                print(f"  {i}. {p}")
            return

    last = {}
    for row in read_csv_rows(HISTORY, ["date", "names"]):
        d = datetime.strptime(row["date"], "%Y-%m-%d").date()
        for p in [x for x in row["names"].split(";") if x]:
            last[p] = max(last.get(p, d), d)
    never = 9999

    def staleness(p):
        return never if p not in last else (today - last[p]).days

    # 分桶: 最久未查的桶优先，桶内随机
    picked = []
    names = sorted(roster, key=lambda p: (-staleness(p), p))
    i = 0
    while len(picked) < n and i < len(names):
        bucket_val = staleness(names[i])
        bucket = []
        while i < len(names) and staleness(names[i]) == bucket_val:
            bucket.append(names[i]); i += 1
        rng.shuffle(bucket)
        picked += bucket[: n - len(picked)]
    picked = picked[:n]

    append_csv_row(HISTORY, ["date", "names"], {"date": today.isoformat(), "names": ";".join(picked)})
    print(f"今日抽检名单 {today}（共 {len(picked)} 人 / 在册 {len(roster)} 人，最久未查优先）:")
    for i, p in enumerate(picked, 1):
        note = "从未抽检" if staleness(p) == never else f"上次抽检 {staleness(p)} 天前"
        print(f"  {i}. {p}（{note}）")


# ---------------------------------------------------------------- record

def month_count(ledger, name, family_keys, month):
    return sum(1 for r in ledger
               if r["name"] == name and r["type"] in family_keys and r["date"][:7] == month)


def cmd_record(args):
    key = find_type(args.type)
    if not key:
        print(f"错误: 未知违规类型 '{args.type}'，可选:", file=sys.stderr)
        for k, (cn, _f, _l, _e) in TYPES.items():
            print(f"  {k:22s} {cn}", file=sys.stderr)
        sys.exit(2)
    cn, family, level, effect = TYPES[key]
    d = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    month = d.strftime("%Y-%m")
    ledger = load_ledger()

    ordinal, outcome = "", effect
    if family == "monthly":
        prev = month_count(ledger, args.name, MONTHLY_FAMILY, month)
        ordinal = str(prev + 1)
        if prev + 1 == 1:
            level, outcome = "通报+扣10分", "自然月第1次: 群内+开会通报 + 扣10分"
        else:
            level, outcome = "三级", f"自然月第{prev + 1}次(撤回/活动类合并计): 当月绩效×0.9 + 通报批评"
    elif family == "window30":
        win = [r for r in ledger if r["name"] == args.name and r["type"] == key
               and abs((datetime.strptime(r["date"], "%Y-%m-%d").date() - d).days) <= 30]
        ordinal = str(len(win) + 1)
        if len(win) + 1 >= 3:
            level, outcome = "三级", f"30天内第{len(win) + 1}次 → 三级: 当月绩效×0.9 + 通报批评"
        else:
            level, outcome = f"记录(30天内第{len(win) + 1}次)", "累计到30天内第3次才构成三级，本次先记录在案"

    append_csv_row(LEDGER, ["date", "name", "server", "type", "ordinal", "level", "evidence", "notes"],
                   {"date": d.isoformat(), "name": args.name, "server": args.server or "",
                    "type": key, "ordinal": ordinal, "level": level,
                    "evidence": args.evidence or "", "notes": args.notes or ""})
    print(f"已入台账: {d} {args.name} {'@' + args.server if args.server else ''}")
    print(f"  类型: {cn}")
    print(f"  判定: {level or '(见累计规则)'}")
    print(f"  处理: {outcome}")


# ---------------------------------------------------------------- quality

def compute_grade(total, dims):
    """档位自动计算：高≥85且D2≥20；中70-84；低<70。（references/w3-chat-quality.md）"""
    d2 = dims[1]
    if total < 70:
        return "低"
    if total >= 85 and d2 >= 20:
        return "高"
    return "中"


def gray_link_grade(day, name):
    """联动规则：当天有灰度违规记录 → 最高"中"；红线/一级 → 直接"低"。无记录返回 None。"""
    worst, order = None, ["红线", "一级", "二级", "三级", "通报+扣10分"]
    for r in load_ledger():
        if r["date"] == day.isoformat() and r["name"] == name:
            lv = r["level"]
            if lv and not lv.startswith("记录"):
                if worst is None or order.index(lv) < order.index(worst):
                    worst = lv
    if worst is None:
        return None
    return "低" if worst in ("红线", "一级") else "中"


def cmd_quality(args):
    d = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    dims = []
    if args.scores:
        parts = [x.strip() for x in args.scores.split(",")]
        if len(parts) != len(QUALITY_DIMS):
            raise SystemExit(f"错误: --scores 需要 {len(QUALITY_DIMS)} 个数（D1..D6 逗号分隔），收到 {len(parts)} 个")
        dims = [float(x) for x in parts]
    else:
        given = [args.d1, args.d2, args.d3, args.d4, args.d5, args.d6]
        if all(v is None for v in given):
            raise SystemExit("错误: 需要 --scores d1,d2,d3,d4,d5,d6 或逐维 --d1..--d6")
        dims = [float(v) if v is not None else 0.0 for v in given]
    for (key, cname, mx), v in zip(QUALITY_DIMS, dims):
        if not 0 <= v <= mx:
            raise SystemExit(f"错误: {key}({cname}) 得分 {v} 超出 0–{mx}")
    total = sum(dims)
    grade = compute_grade(total, dims)

    # 联动灰度台账
    linked = gray_link_grade(d, args.name)
    link_note = ""
    if linked and not args.grade:
        if grade != linked and (grade == "高" or (linked == "低" and grade != "低")):
            link_note = f"（联动调整: 自动档 {grade} → {linked}，因当天灰度记录）"
            grade = linked
    if args.grade:
        grade = args.grade
        link_note = f"（人工覆盖档位，理由需写入 notes）"

    append_csv_row(QUALITY_LOG, QUALITY_HEADER,
                   {"date": d.isoformat(), "name": args.name, "server": args.server or "",
                    **{k: int(v) for (k, _c, _m), v in zip(QUALITY_DIMS, dims)},
                    "total": int(total), "grade": grade,
                    "issues": args.issues or "", "evidence": args.evidence or "",
                    "notes": args.notes or ""})
    per_dim = "  ".join(f"{cname} {v:g}/{mx}" for (_k, cname, mx), v in zip(QUALITY_DIMS, dims))
    print(f"已入质量台账: {d} {args.name}{' @' + args.server if args.server else ''}")
    print(f"  六维: {per_dim}")
    print(f"  总分: {total:g}/100 → 档位: 【{grade}】{link_note}")
    if args.issues:
        print(f"  扣分点: {args.issues}")


def cmd_quality_summary(args):
    month = args.month or date.today().strftime("%Y-%m")
    rows = [r for r in read_csv_rows(QUALITY_LOG, QUALITY_HEADER) if r["date"][:7] == month]
    if args.name:
        rows = [r for r in rows if r["name"] == args.name]
    if not rows:
        print(f"{month} 无质量评分记录。")
        return
    print(f"══ {month} 聊天质量评分汇总 ══\n")
    by_person = {}
    for r in rows:
        by_person.setdefault(r["name"], []).append(r)
    order = ["高", "中", "低"]
    for name in sorted(by_person):
        rs = sorted(by_person[name], key=lambda r: r["date"])
        grades = [r["grade"] for r in rs]
        dist = {g: grades.count(g) for g in order if grades.count(g)}
        avg = sum(float(r["total"]) for r in rs) / len(rs)
        lows = [r["date"] for r in rs if r["grade"] == "低"]
        print(f"● {name} — 评了 {len(rs)} 天｜均分 {avg:.1f}｜分布 {dist}")
        if lows:
            print(f"   ⚠ 低档日期: {', '.join(lows)} → 建议主管复盘（连续3天中档或单次低档触发）")
        for r in rs:
            if r["issues"]:
                print(f"   {r['date']} 【{r['grade']}】{r['total']}  扣分点: {r['issues']}")
        print()




def cmd_status(args):
    month = args.month or date.today().strftime("%Y-%m")
    ledger = [r for r in load_ledger() if r["date"][:7] == month]
    if args.name:
        ledger = [r for r in ledger if r["name"] == args.name]
    if not ledger:
        print(f"{month} 无台账记录。")
        return
    print(f"══ {month} 灰度违规台账汇总 ══\n")
    by_person = {}
    for r in ledger:
        by_person.setdefault(r["name"], []).append(r)
    for name in sorted(by_person):
        rows = sorted(by_person[name], key=lambda r: r["date"])
        servers = sorted({r["server"] for r in rows if r["server"]})
        levels = [r["level"] for r in rows if r["level"] and not r["level"].startswith("记录")]
        print(f"● {name}{'（服务器: ' + '/'.join(servers) + '）' if servers else ''} — 共 {len(rows)} 条")
        for r in rows:
            cn = TYPES.get(r["type"], (r["type"],))[0]
            fam = TYPES.get(r["type"], ("", "", "", ""))[1] if r["type"] in TYPES else ""
            ord_note = ""
            if r["ordinal"]:
                ord_note = f"（当月第{r['ordinal']}次）" if fam == "monthly" else f"（30天窗口第{r['ordinal']}次）"
            print(f"   {r['date']} {cn} → {r['level'] or '记录'}{ord_note}"
                  f"{'｜证据: ' + r['evidence'] if r['evidence'] else ''}")
        if levels:
            order = ["红线", "一级", "二级", "三级"]
            worst = min(levels, key=lambda l: order.index(l) if l in order else 9)
            print(f"   → 本月最重等级: {worst}（{LEVEL_EFFECT.get(worst, '')}）")
            if len(levels) > 1:
                print(f"   ⚠ 同月多条 ({'/'.join(levels)})：是否叠加系数源文档未定义，默认按最重单次处理，需人工裁定")
        if len(servers) > 1:
            print(f"   ⚠ 涉及多服结算错位：适用《特殊情况》——已结算月份处理后，未结算服到其结算月不再重复扣分")
        print()


# ---------------------------------------------------------------- rules

def cmd_rules(_args):
    print("W3 灰度违规规则速查（判定依据 references/w3-gray-assessment.md）\n")
    print("【违规类型】")
    for k, (cn, family, level, effect) in TYPES.items():
        fam = {"immediate": "单次即触发", "monthly": "自然月累计", "window30": "30天窗口累计"}[family]
        print(f"  {cn}")
        print(f"    key={k}｜{fam}｜等级: {level or '按累计'}")
        print(f"    处理: {effect}")
    print("\n【等级 → 绩效】")
    for lv, eff in LEVEL_EFFECT.items():
        print(f"  {lv:10s} {eff}")


# ---------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(description="W3 灰度风险评定引擎")
    sub = p.add_subparsers(dest="cmd", required=True)
    ps = sub.add_parser("sample", help="抽取今日 6-7 人")
    ps.add_argument("--n", default="6-7", help="6 / 7 / 6-7(每日随机取其一，默认)")
    ps.add_argument("--force", action="store_true", help="当日已抽过也重新返回名单（不重复入历史）")
    ps.set_defaults(fn=cmd_sample)
    pr = sub.add_parser("record", help="记录一条违规")
    pr.add_argument("--name", required=True)
    pr.add_argument("--type", required=True, help="类型中文名或 key，见 rules")
    pr.add_argument("--date", help="YYYY-MM-DD，默认今天")
    pr.add_argument("--server", help="所在服务器，如 14服")
    pr.add_argument("--evidence", help="证据摘录（消息内容/时间/频道）")
    pr.add_argument("--notes")
    pr.set_defaults(fn=cmd_record)
    pq = sub.add_parser("quality", help="记录一人当日聊天质量评分（六维，自动定档）")
    pq.add_argument("--name", required=True)
    pq.add_argument("--server", help="所在服务器")
    pq.add_argument("--scores", help="六维得分逗号分隔: d1,d2,d3,d4,d5,d6（如 18,25,12,15,10,8）")
    pq.add_argument("--d1", type=float, help="响应及时性 0-20")
    pq.add_argument("--d2", type=float, help="准确性与专业度 0-25")
    pq.add_argument("--d3", type=float, help="教学引导 0-15")
    pq.add_argument("--d4", type=float, help="联盟管理/协调 0-15")
    pq.add_argument("--d5", type=float, help="话术规范 0-15")
    pq.add_argument("--d6", type=float, help="服务态度/共情 0-10")
    pq.add_argument("--grade", choices=["高", "中", "低"], help="人工覆盖自动档位（理由写 --notes）")
    pq.add_argument("--date", help="YYYY-MM-DD，默认今天")
    pq.add_argument("--issues", help="扣分点摘要（每条带消息原文引用）")
    pq.add_argument("--evidence", help="关键证据（消息原文+时间+频道）")
    pq.add_argument("--notes")
    pq.set_defaults(fn=cmd_quality)
    pqs = sub.add_parser("quality-summary", help="当月聊天质量档位汇总")
    pqs.add_argument("--month", help="YYYY-MM，默认当月")
    pqs.add_argument("--name", help="只看某人")
    pqs.set_defaults(fn=cmd_quality_summary)
    pt = sub.add_parser("status", help="当月台账汇总")
    pt.add_argument("--month", help="YYYY-MM，默认当月")
    pt.add_argument("--name", help="只看某人")
    pt.set_defaults(fn=cmd_status)
    pl = sub.add_parser("rules", help="打印规则速查表")
    pl.set_defaults(fn=cmd_rules)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
