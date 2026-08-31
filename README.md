# slg-qa — SLG 游戏国际服质检 Agent Skill

一个 ZCode Agent Skill：把 SLG 游戏国际服运营中**重复性的质检工作**交给脚本和清单沉淀，覆盖本地化、版本、运营活动、合规四大质检线，以及《W3》灰度违规评定与 GS 聊天文本质量评估的每日抽检模式。

## 功能总览

### 四大质检线（references/）

| 质检线 | 文件 | 覆盖内容 |
|---|---|---|
| 本地化 LQA | `references/lqa-checklist.md` | 9 类机器可查项 + AI 语义判断（by/to 数值语义、敬语、文化敏感）+ 16 语言高危速查 |
| 版本/包体 | `references/build-checklist.md` | 提审前检查：签名、targetSdk、隐私清单、强更死锁、商店材料 |
| 运营/活动 | `references/liveops-checklist.md` | 时间三口径、概率校验、IAP 掉单、KvK/赛季/合服 |
| 国际合规 | `references/compliance-checklist.md` | 10 市场合规矩阵（韩国概率公示、日本コンプガチャ、德国符号红线等） |

### 自动化脚本（scripts/）

- **`lqa_scan.py`** — 本地化文本自动扫描器：占位符/富文本标签、未翻译（空/相同/漏 key）、术语（required+forbidden）、超长（按语言膨胀系数或 max-length 列）、空格、重复标点、转义、编码（乱码/bidi/全半角）、大小写风格。支持 CSV / XLSX / JSON / Android strings.xml（双文件模式），输出 text / md / json。
- **`w3_gray.py`** — 《W3》灰度每日抽检引擎：
  - `sample` 20 人抽 6–7 人（最久未查优先 + 日期种子随机，当日可复现）
  - `record` 违规入台账，自动套用月度累计 / 30 天窗口规则定级
  - `quality` 聊天文本六维评分（响应及时 20 / 准确专业 25 / 教学引导 15 / 联盟管理 15 / 话术规范 15 / 服务共情 10），自动定高/中/低档，与当天灰度记录联动降档
  - `quality-summary` / `status` 月度质量与违规台账汇总

### 输出模板（assets/）

质检报告模板、bug 单模板（S1–S5 统一分级 + 定位三要素）、W3 灰度日报模板、演示数据（`assets/demo/`）。

## 目录结构

```text
slg-qa/
├── SKILL.md                        # 触发条件 + 路由表 + 固定工作流
├── references/                     # 质检规则书（按需加载）
│   ├── lqa-checklist.md
│   ├── build-checklist.md
│   ├── liveops-checklist.md
│   ├── compliance-checklist.md
│   ├── bug-and-report-format.md
│   ├── slg-domain-notes.md
│   ├── w3-gray-assessment.md       # 灰度违规评定（红线/一级/二级/三级）
│   └── w3-chat-quality.md          # 聊天文本质量六维评分
├── scripts/
│   ├── lqa_scan.py
│   └── w3_gray.py
└── assets/
    ├── qa-report-template.md
    ├── bug-report-template.md
    ├── w3-daily-report-template.md
    ├── demo/                       # 自测演示数据
    └── w3/                         # W3 名册模板与源文档提取件
```

## 快速上手

```bash
# 本地化扫描（CSV，德语，带术语表）
python scripts/lqa_scan.py strings.csv --src-col en --tgt-col de --lang de --glossary glossary.csv

# Android 双文件（含整条漏翻检查）
python scripts/lqa_scan.py --src-file values/strings.xml --tgt-file values-de/strings.xml --lang de

# W3 每日抽检
python scripts/w3_gray.py sample
python scripts/w3_gray.py record --name 张三 --type "发中文后撤回" --server 14服 --evidence "证据摘录"
python scripts/w3_gray.py quality --name 张三 --scores 18,25,12,15,10,8
python scripts/w3_gray.py status --month 2026-08 && python scripts/w3_gray.py quality-summary --month 2026-08
```

依赖：Python 3.10+；读 XLSX 需 `openpyxl`。

## 安装为 ZCode Skill

把本目录放入 `~/.agents/skills/slg-qa/`（用户级）或 `<project>/.agents/skills/slg-qa/`（项目级），ZCode 会根据 SKILL.md 的 description 自动触发。

## 说明

- W3 灰度规则（`references/w3-gray-assessment.md`、`assets/w3/`）来自实际项目内部规范，**仓库默认保持私有**；如需开源请先脱敏。
- 运行期产生的员工抽检数据（`assets/w3/data/*.csv`）已在 `.gitignore` 中排除，不会入库。
