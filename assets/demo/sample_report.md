# LQA 自动扫描报告

- 范围: assets/demo/strings_demo.csv　语言: de
- 文本条数: 16　发现: 2 条

## 占位符/标签（placeholder，参考等级 S2）— 2 条

| 文件 | 行 | key | 问题 | SRC | TGT |
|---|---|---|---|---|---|
| assets/demo/strings_demo.csv | 3 | ui.march.speed | 缺少 {0} | Increases march speed by {0}% | Erhöht Marschgeschwindigkeit um % |
| assets/demo/strings_demo.csv | 13 | ui.tag.color | 缺少 </b>；多出 </i> | Your shield expires <b>soon</b> | Dein Schutz endet <b>bald</i> |

