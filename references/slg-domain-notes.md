# SLG 领域术语与雷区速查

质检 SLG（策略/战争类）游戏时用。拿不准概念、判断 bug 归属时看这里。

## 核心系统词汇（中/英对照）

| 中文 | 英文 | 说明 |
|---|---|---|
| 主城/城堡 | Keep / Castle / City | 等级是账号进度核心指标 |
| 建筑 | Building | |
| 研究/科技 | Research / Technology | Academy（学院）里做 |
| 部队 | Troop / Troops | 兵种：步兵/骑兵/弓兵/攻城（Infantry/Cavalry/Archer/Siege） |
| 行军 | March | 行军速度、行军上限、行军队列 |
| 集结 | Rally | 联盟多人打一个目标；发起者叫 Rally Initiator |
| 增援/驻防 | Reinforce / Garrison | 援助盟友城防 |
| 侦察 | Scout | |
| 迁城 | Teleport | 随机/定点迁城 |
| 护盾 | Shield | 新手保护、免战 |
| 联盟 | Alliance | **术语一致性最高危词**——Alliance/Guild/Clan 不得混用 |
| 领土/旗帜 | Territory / Flag / Banner | 联盟占地机制 |
| 圣坛/奇观 | Altar / Wonder | KvK 最终目标常是 Wonder |
| KvK | Kingdom vs. Kingdom | 跨服大战，赛季制核心 |
| 赛季 | Season | 赛季重置范围是玩家最敏感的规则 |
| 合服 | Server Merge | 合服规则（榜单/联盟/邮件保留） |
| 加速 | Speed-up / Boosts | 通用加速 vs 专用加速 |
| 资源 | Resources | 粮/木/石/金（Food/Wood/Stone/Gold），SLG 显示常用 K/M/B |
| VIP | VIP | 依赖活跃度的成长线 |
| 战令 | Battle Pass / Event Pass | |
| 月卡 | Monthly Card / Daily Deal | 资金决算法相关（日本市场） |
| 首充 | First Recharge / First Top-up | |
| 掉落 | Drop / Loot | |
| 副本 | Expedition / Stages | PvE 线 |
| 野怪 | Barbarians / Monsters | |
| 联盟礼物 | Alliance Gifts | 打野怪掉落给全盟 |

## SLG 高频事故模式（质检时优先怀疑）

1. **时区**：活动配置 UTC、展示没换算 → 欧洲玩家看到的活动时间差 1–8 小时。任何带时间的活动必查三口径。
2. **数值语义**：by/to、up to、per 误译 → 玩家实际获得的加成与理解不符 → 客诉与补偿成本。
3. **大数值显示**：资源单位 K/M/B 换算精度、上溢（999.99K → 1M）、多语言千分位。
4. **跨服/合服**：排行榜快照、联盟归属、邮件保留。
5. **补偿邮件**：发错附件、重复领取不幂等 → 全服补偿（真实事故案例：领取按钮可连点）。
6. **占位符重排**：`{player} 击败了 {enemy}` 语序在 ja/ko/de 中需要重排，占位符被硬编码顺序锁死。
7. **术语漂移**：多供应商翻译导致 Alliance 在同一版本里 3 种译法。
8. **概率公示**：新卡池上线忘更新公示页（韩国市场违法级）。
9. **商店错挂**：礼包内容与展示图不符、测试价上线。
10. **强更死锁**：版本号比较用字符串（`2.10.0` < `2.9.0`）导致错误强更。

## 质检输出时的模块命名

统一用以下模块名写 bug 单（方便汇总统计）：
`Localization` / `Store-IAP` / `Event-LiveOps` / `Battle-Combat` / `Alliance` / `March-Map` / `Ranking` / `Social-Chat` / `UI-Rendering` / `Update-Hotfix` / `Compliance` / `Payment-Order` / `Notification` / `Account`
