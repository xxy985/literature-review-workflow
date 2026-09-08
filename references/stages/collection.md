# C1–C3 采集与阅读操作卡

命令缩写 search/fetch/convert/cite/check 均指 `python <skill>/scripts/literature_review_<名称>.py <work>`。调用前可读 --help；产物参数使用绝对路径，避免混淆当前目录。

## C1：研究任务与候选池

门1必须记录课题领域 `computer-science` 或 `other` 及依据。仅前者接受会议论文；交叉领域若归属含混，默认 other，交门1裁决。此后每次 fetch 都传 `--review-field <已确认值>`，该参数遗漏时默认 other。候选发现不等于准入；入库由 CrossRef 类型核验把关，不能使用 OpenAlex article 作为期刊证明。

输入：用户主题、已有材料及用途。先记录研究问题、综述类型（叙述/范围/系统等）、读者、范围与预期贡献到 artifacts/01-topic/研究任务-v1.md。信息不足但可推断时显式列默认值；方向真正含混时给2–3个子方向供门1选择。不得把本流程自动声称为系统综述，系统综述需另有纳排标准、完整检索记录及相应方法要求。

设计3–5组同义词、上下位词与时间窗检索式，逐组 `search --query "..."`。候选池按日期合并；每次完成后保留版本快照，推荐与采集引用快照。去重后60为软下限，不足说明原因。官方统计、标准等单列来源、日期与具体支撑用途，不伪装为论文。

输出：研究任务、检索式、候选池与检索报告。验收：范围与候选匹配、来源可追溯、数量与盲区如实说明。
`check --at-gate 门1`，确认研究问题、范围、读者及检索方案；通过后 `check --advance C2`。

## C2：首轮语料和方向

输入：门1决定及候选池。按相关性先筛，再比较奠基性、方法代表性、近期进展、争议、数据支撑；五维1–5分可辅助排序，但必须写理由。选10篇及候补，保存推荐报告，再将按推荐顺序排列的条目另存 round01-selected-v1.tsv；保持原候选字段，不直接把整个未排序候选池交给 fetch。

`fetch --candidates <所选TSV> --round 1 --limit 10 --fulltext-only`。摘要入账但不占首轮10个全文名额，并列入人工补缺。首次不足时用候补继续；重跑只传剩余新增名额，详见恢复规范。候选耗尽不硬凑。

`convert --round 1` 后按 reading.md 完成笔记与 mark-read；摘要条目用B并单独报告。按 synthesis.md 完成首轮综合，提出文章可能的贡献和主题调整。用 checkpoint 保存 theme_boundary、weak_dimensions、rounds.planned（4–8，默认4）和已完成轮次。

`check --round 1 --require-fulltext 10` 输出轮报告。未通过返回2，先解决原因；若不可解决，将不足与影响提交门2裁决，不能称已满足标准。

输出：推荐表、至少10篇全文的首轮目标完成情况、阅读笔记、综合表、主题与轮数建议。门2确认首轮语料和文章方向；失败且获准重开时按 recovery.md；通过后 `check --advance C3`。

## C3：滚动40与扩圈20

每轮：补缺口推荐 → 所选TSV → fetch → convert → 笔记及mark-read → 综合更新 → `check --round N` → checkpoint。每轮约10篇，生产主体总目标40（A+B，B不可替代核心证据）；库量与当前尝试纳入清单分别统计。

达到计划轮数仍短缺时列清缺多少、原因、候选余量和已试路径，提交继续至8轮/收缩主题/调整目标的裁决；不自行突破8轮。数量够但核心证据不足也应补检或收缩论断，不强行成文。

主体完成后按 expansion-and-coverage.md 自动发现、人工筛选与盲区审计，扩圈目标20。`cite --target 40 --mode both` 仅产候选；将 include 条目另存TSV，再 `fetch --candidates <入选TSV> --round X --limit 20`、`convert --round X`、阅读、综合、`check --round X` 与 `check --full`。

验收：当前尝试主体40/扩圈20及A/B分布清楚；核心问题有证据；未覆盖面有理由和处理决定；不存在未核验文献、排除回灌与预印本。轮报告/库体检是机械检查，不是文章质量证明。完成后 `check --advance C4`，不停新门。

## 人工补缺与已有材料

人工补缺按清单给出的 DOI 编码文件名放 source/manual/roundNN 或 roundXX，运行 `fetch --collect-manual --round N|X`，再 convert 并更新阅读记录。例如 `10.1234/example` 对应 `10.1234%2Fexample.pdf`。人工补入不会自动变成已读A。

已有文献集合仍需题名/DOI候选TSV通过 fetch 核验入账，PDF再按人工补缺入口关联；convert不负责创建库行。方向已明确可从首轮准备开始；未确认范围则先门1。无DOI或未能核验的输入保留为线索，不直接绕过入库规则。
