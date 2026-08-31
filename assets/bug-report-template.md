# Bug 单（示例 + 空白模板）

## 空白模板

```
ID:        BUG-YYYYMMDD-NNN
标题:      [模块][语言/市场] 现象 + 关键条件（英文）
严重等级:  S1/S2/S3/S4/S5    优先级: P0/P1/P2/P3
模块:      Localization / Store-IAP / Event-LiveOps / Battle-Combat / Alliance /
           March-Map / Ranking / Social-Chat / UI-Rendering / Update-Hotfix /
           Compliance / Payment-Order / Notification / Account
环境:      平台(iOS/Android) + 版本号 + 语言 + 服务器/市场
前置条件:  账号状态、配置状态
复现步骤:
  1. …
  2. …
  3. …
期望结果:  …
实际结果:  …
复现率:    必现 / N 次中 M 次
证据:      截图/录屏/日志路径
定位信息:  文件 + key/行号 + 原文摘录（文本类必填三要素）
初步分析:  （可选）可能原因，与"实际结果"分开写
```

## 示例 1：本地化 S2（占位符丢失）

```
ID:        BUG-20260831-001
标题:      [L10N][DE] Placeholder {0} missing in march speed buff description
严重等级:  S2    优先级: P1
模块:      Localization
环境:      Android 2.3.1 (build 2310) 德语 S-1204
前置条件:  账号已研究 Lv3 行军科技
复现步骤:
  1. 切换游戏语言为 Deutsch
  2. 打开 Academy → Research → March Speed Lv3
  3. 查看 buff 描述
期望结果:  "Erhöht Marschgeschwindigkeit um {0}%"
实际结果:  "Erhöht Marschgeschwindigkeit um %"（{0} 丢失，数值不显示）
复现率:    必现
证据:      screenshot_de_march_speed.png
定位信息:  strings.csv 行 1204 / key: ui.research.march_speed.desc / 源文: "Increases march speed by {0}%"
初步分析:  译文占位符被误删，需回翻并回归全量占位符扫描
```

## 示例 2：运营 S2（活动时区）

```
ID:        BUG-20260831-002
标题:      [Event] KvK sign-up countdown shows wrong remaining time (UTC offset not applied)
严重等级:  S2    优先级: P1
模块:      Event-LiveOps
环境:      iOS 2.3.1 全语言 服务器 EU-301
前置条件:  KvK 报名将于 2026-09-01 00:00 UTC 结束
复现步骤:
  1. 2026-08-31 20:00 UTC（当地 22:00 CEST）登录
  2. 查看 KvK 报名页倒计时
期望结果:  剩余 4 小时
实际结果:  剩余 2 小时（按本地时间误算）
复现率:    必现
证据:      log_timezone_mismatch.txt；配置 event_kvk_s1.json end_time="2026-09-01T00:00:00Z"
定位信息:  event_kvk_s1.json / end_time / UI 倒计时组件用 local time 直接 diff
初步分析:  前端用本地时区渲染，未换算 UTC；影响所有非 UTC 服务器玩家报名截止判断
```

## 示例 3：合规 S2（概率公示未更新）

```
ID:        BUG-20260831-003
标题:      [Compliance][KR] Gacha probability page not updated for new pool "Dragon Legend"
严重等级:  S2    优先级: P0
模块:      Compliance
环境:      全平台 2.3.1 韩语市场
前置条件:  新卡池 Dragon Legend 已于 2026-08-30 上线
复现步骤:
  1. 进入抽卡页 → 概率公示
  2. 对比公示 SSR 概率与 gacha_pool_v3.json 配置
期望结果:  公示页数值 = 配置数值（SSR 1.5%）
实际结果:  公示页仍显示旧池数值（SSR 2.0%）
复现率:    必现
证据:      screenshot_kr_prob_page.png；gacha_pool_v3.json
定位信息:  gacha_pool_v3.json / ssr_rate / 公示页静态资源 prob_page_v2.html
初步分析:  韩国市场概率公示为法定义务，属于违法级展示错误，需 P0 修复后才能在 KR 商店更新
```
