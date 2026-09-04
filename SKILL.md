---
name: literature-review-workflow
description: 综述论文半自动生产推进台。当用户说"推进""继续综述流程""推进到下一扇门"时使用：读取工作根目录 progress.md 状态块，按当前走廊 SOP 调用 scripts/ 内预写脚本执行，只在人工闸门处停下汇报。需宿主具备终端执行 Python、本地文件读写与网络访问能力（详见部署 README 能力契约）。
---

# literature-review-workflow：综述论文半自动生产推进台

## 0. 三方分工（先读这个）

- **脚本是工人**：检索、核验、下载、转换、统计、审计全部由 `scripts/` 内预写脚本完成。动手前先查“这一步是否已有脚本”；调用前先读脚本头部 docstring 弄清输入输出。**禁止现场重写脚本已有的逻辑。**
- **AI 是操作者，脚本是它的工具**：读状态账本 → 按走廊 SOP 调脚本、读论文做判断、写产物；状态块只经脚本命令维护（new / --at-gate / --advance / --reset-attempt），不手工编辑 JSON。
- **人是拍板者**：只在闸门处决策。

推进节奏：正常推进时不停、不问，一路到下一扇门。例外是 §6 的三类异常（缺下载渠道/解析大面积差/主题漂移两轮）——那不是“停门”而是异常终断：立即停、置 blocked_on、汇报。两类停顿不矛盾：闸门=流程设计，异常=风险熔断。

## 1. 硬规则（违反即事故）

1. **禁止网络发布与对外发送**：任何产物、库文件不得上传、邮件、推送、同步到任何外部服务。本流程只落本地文件。
2. **不覆盖、不删除（范围界定）**：原始输入（source/ 下用户投递件）与已交付产物不覆盖，版本一律新文件（v1/v2/v3）；禁止删除任何文件，需删除时提示用户自行处理。账本类文件不在此列内，按各自规则更新：`library.tsv` 行内更新的唯一通道是 `check --mark-read`；`excluded.tsv` 只追加；`progress.md` 状态块只由脚本命令（new / --at-gate / --advance / --reset-attempt）原子替换（围栏外自然语言区 AI 可写）。
3. **不谎报**：下载没成功就是没成功（fetch_status 是唯一事实）；摘要缺失显式写"无摘要"，不得编造；结论只来自已读内容。
4. **不绕过付费墙**：非开放获取文献下载失败即转人工补缺清单，禁止任何绕过手段。
5. **极低速率**：一切网络请求走脚本内置限速（默认 3 秒 + 随机 2 秒抖动），禁止并发轰炸。
6. **预印本一律排除**（既定决策）：入库论文必须是能核验到正式发表版的；但会议论文（proceedings-article）是正当文献，不排除。已正式发表者允许从 arXiv 镜像下载全文（条目按正式版记录，source 记 arxiv-mirror）。
7. **人工助理（饺子）只改文字句子**，不给其增加任何技术负担。

触发边界（并入闲聊不启动）：仅当用户指令明确面向推进（“推进/继续综述流程/推进到下一扁门”）才执行一轮。对话中顺带提及综述、提问、闲聊不构成触发。

## 2. 账本与目录

- **轮级状态唯一真相源** = `<工作根目录>/progress.md` 顶部 JSON 状态块（`<!--LITERATURE-REVIEW-WORKFLOW:STATE:BEGIN-->` 与 `END` 标记之间）。状态块由 check 脚本命令维护（`--at-gate` 停门登记 / `--advance` 门后推进 / `--reset-attempt` 重开 / new 自举），临时文件+原子替换，AI 不手改 JSON 块。**脚本不可用 = 环境阻塞**：停下向用户报告。AI 只写围栏标记以下的自然语言区。
- **篇级账本** = `<工作根目录>/source/papers/library.tsv`（22 列，每行一篇；列含义见 `scripts/literature_review_lib.py` 的 LIBRARY_FIELDS 注释）。
- **排除账** = `notes/history/excluded.tsv`（写入即留痕，论文被拒的原因永远可查；追加式不删不改。若某条排除需撤销：同 DOI（或同归一化题名，DOI 为空时）追加一行 reason 以 `withdrawn` 开头的逆转行，旧行保留；check --full 按“同键最后一行”判定回灌，键 = DOI 优先、无 DOI 记录用归一化题名备用键）。
- 工作根目录结构（`literature_review_new.py` 自举建立，目录名即语义）：

```
工作根目录/
├── progress.md                  # 状态块 + 自然语言进度
├── source/papers/roundNN/       # 全文 pdf 与转换后 md（paper_id 命名）
├── source/papers/library.tsv    # 篇级账本（唯一）
├── source/manual/roundNN/       # 人工补缺投递处
├── source/jiaozi/               # 助理回件投递处
├── artifacts/01-topic/          # 方向说明、检索式、检索报告、候选池
├── artifacts/02-recommend/      # 每轮推荐报告（含五维打分、主题精炼）
├── artifacts/03-library/        # 验收、去重、扩圈候选、体检报告
├── artifacts/04-knowledge-base/ # 每篇阅读笔记
├── artifacts/05-outline/       # 提纲（及修改版）
├── artifacts/06-writing-req/   # 成文要求
├── artifacts/07-draft/         # 初稿与各版修改稿、修改日志
├── artifacts/08-jiaozi/        # 助理交接包
├── artifacts/09-deliver/       # 最终交付物与审计报告
└── notes/history/               # 运行日志、排除账
```

- **每次推进的固定循环**：读状态块 → 判定当前走廊 → 执行 SOP → 每个子步骤完成后经脚本更新状态 → 遇闸门停下汇报。

## 3. 状态块字段（progress.md JSON）

| 键 | 含义 |
|---|---|
| attempt | 第几次尝试（抛弃重来计数） |
| corridor / gate | 当前走廊 / 最近通过的闸门 |
| theme / theme_boundary | 主题锚句 / 当前主题边界一句话 |
| weak_dimensions | 待补强维度（下轮推荐优先补） |
| rounds.planned / completed | 计划总轮数（4-8，C2 定）/ 已完成轮数 |
| papers.target / expand_target | 主体目标 40 / 扩圈目标 20 |
| papers.fulltext / abstract_only / manual_needed | 三种状态论文计数 |
| pending_decisions | 待用户拍板事项队列 |
| blocked_on | 阻塞对象（user / jiaozi / 空） |

## 4. 走廊与闸门

### C1 自举 + 定方向 + 候选池（启动 → 门1）

1. 工作根目录不存在则 `python scripts/literature_review_new.py <工作根目录> --title "主题"`。
2. 方向模糊时**提 2-3 个子方向供用户择定**（每个一句话定位 + 检索入口差异），不自己拍板大方向。
3. 设计 3-5 组检索式（同义词 / 上下位词 / 时间窗），落 `artifacts/01-topic/检索式.md`，逐组 `python scripts/literature_review_search.py <工作根目录> --query "..."` 合并候选池（产物固定落盘 `artifacts/01-topic/候选池-<日期>.tsv`，多组检索自动同池合并去重；人工去重入口 `dedup --candidates <该tsv>`）。
4. 候选池软下限 60（去重后）：不足则明示告警（主题过窄/检索式需扩），不硬凑。
5. 官方数据源按领域另查（统计机构/标准组织/权威项目库），在检索报告单列小节，不混入文献池。
6. 产出 `artifacts/01-topic/检索报告.md`：池统计、各组命中、官方数据源小节 + 方向候选清单（门1 拍板对象逐条列出）。
7. **停 门1（检索方案确认）**：呈报告摘要 + 方向候选，用户定基调。回到这里重来（attempt+1）也是从这里授权。停门后 `check --at-gate 门1` 登记；门通过后 `check --advance C2` 推进。

### C2 首轮推荐 + 下载 + 精读 + 定总轮数（门1 → 门2）

1. 读候选池标题+摘要，**两层推荐**：
   - 第一层门：主题相关性 0/1（不相关直接挡）；
   - 第二层排序：五维打分——奠基性 / 方法代表性 / 近期进展（SOTA）/ 争议焦点 / 数据与基准支撑，各 1-5 分，加权合计。
2. 推荐 10 篇，落 `artifacts/02-recommend/round01-推荐.md`（打分表 + 每篇推荐理由 + 该批整体覆盖说明）。
3. `python scripts/literature_review_fetch.py <工作根目录> --candidates artifacts/01-topic/候选池-<日期>.tsv --round 1 [--limit 12]`（脚本内自动：预印本一律排除、CrossRef 核验、OA 下载、人工补缺清单）。
4. **可下载性补位（D1）**：首轮 10 篇名额只算 fetch 成功（fetch_status=ok）者；候选按超采样顺位多取 2-3 篇，下载失败/付费墙/预印本被挡的不占名额，自动顺延补足到 10 达标。
5. `python scripts/literature_review_convert.py <工作根目录> --round 1` 转 md 后，AI 逐篇读，写"一句话贡献"并 `python scripts/literature_review_check.py <工作根目录> --mark-read <paper_id> --contribution "一句话" --evidence A`；阅读笔记落 `artifacts/04-knowledge-base/<paper_id>.md`。
6. **主题精炼**：在该轮推荐报告追加"主题精炼"节（子方向证据状态、方向过宽/过窄判断），weak_dimensions 写入状态。
7. **定总轮数**：按首读问题密度与池子匹配率定 rounds.planned（4-8，默认 4，写一句理由入状态自然语言区）。
8. `python scripts/literature_review_check.py <工作根目录> --round 1`（验收报告落盘 `artifacts/03-library/round01-验收.md`，即门2 呈报件）。
9. **停 门2（首轮语料批准）**：呈首读摘要 + 精炼后主题 + 推荐轮数 + 验收报告。用户判"方向失败"→ 抛弃重来（§8）。停门后 `check --at-gate 门2`；门通过后 `check --advance C3`。

### C3 滚动至 40 + 扩圈 20 + 知识库 + 拟提纲（门2 → 门3）

每轮固定子步骤（顺序不可减）：推荐 10（优先补 weak_dimensions）→ fetch → convert → 逐篇精读（阅读笔记 + `check --mark-read`）→ 主题精炼 → `check --round <当前轮号>`。round 字段合法值 = 整数 1-99 或 `X`（扩圈批次，目录 `roundXX/`，paper_id 前缀 `RX-`）；`--round` 参数指当前验收的轮次号，不是计划总轮数。

1. 滚动停止规则：fulltext+abstract_only ≥ 40 即停；若达到 rounds.planned（软上限）或 8 轮硬上限仍未满 40 → 生成短缺报告（缺多少、降级路径用过哪些、候选池还剩多少顺位）并**停下向用户请求裁决**（加轮 / 收缩主题 / 降目标数），不得无限推进或静默突破上限。
2. **扩圈 20（扩圈前必读）**：先读 `references/expansion-and-coverage.md`，再按其中的“自动发现 → AI 判断 → 入库交接”顺序执行：
   1. 运行 `python scripts/literature_review_cite.py <工作根目录> --target 40 --mode both`，自动发现引文、被引和相关推荐候选；该命令只输出候选，不自动入库。
   2. 复制 `templates/expansion-selection.md` 为 `artifacts/03-library/扩圈筛选说明.md`，逐条填写 `include / exclude / hold / manual-review` 决策；高被引综述挖掘、关键词共现补检由 AI 手工完成，并记录来源通道。
   3. 复制 `templates/blind-spot-audit.md` 为 `artifacts/03-library/盲区审计-roundX.md`，完成时间、方法、来源结构、研究群落、语言地域五个切面；每个未覆盖维度必须写理由和再进入条件。
   4. 将 `include` 候选另存为“扩圈待入库” TSV，保留 fetch 所需字段；不要修改原始候选 TSV。
   5. 用 `python scripts/literature_review_fetch.py <工作根目录> --candidates <扩圈待入库.tsv> --round X` 统一核验与下载，再运行 `convert --round X`、补齐精读记录和 `check --full`。
3. 补齐阅读笔记与精读标记；`python scripts/literature_review_check.py <工作根目录> --full` 库体检（体检报告落盘 `artifacts/03-library/库体检-<日期>.md`，含核验断言三件：全库核验 / 无排除回灌 / 预印本零命中，即常规汇报件，不停门）。
4. **拟提纲** `artifacts/05-outline/提纲-v1.md`：按主题/方法/时间/争议组织（**绝不逐篇罗列**）；每节核心论点 + 关键文献（paper_id+DOI）；图表/伪码规划 ≥3；结论落点。
5. 拟提纲后**不停门**：库概览（60 篇构成、A/B 级比例=库体检报告）常规汇报；提纲意见随初稿一并交门3。

### C4 成文要求（并入初稿）→ C5 初稿（→ 门3）

- C4：按 `templates/writing-req.md` 拟 `artifacts/06-writing-req/成文要求.md`（语言/篇幅/引用格式默认 GB-T 7714/图表与伪码/公式 LaTeX+算法环境/专节取舍/数据红线/**终稿输出格式选择：md / docx / LaTeX**），写作要求**随初稿一并交门3** 确认。C8 只执行门3 已确认的格式，不再中途开放选择。
- C5：依提纲+要求+知识库写 `artifacts/07-draft/初稿-v1.md`。纪律：每个论断可追溯 paper_id；B 级（摘要级）引用允许出现于终稿，但只支撑非核心论点，且推文中不加任何标记（引用列表正常列出）；每次停门向用户报 B 级占位数与支撑点。不自称"AI"；不编数据。完稿后 `check --cite-audit 07-draft/初稿-v1.md`。**停 门3（初稿与引用边界确认）**：呈初稿 + 引用边界报告（B 级占位与支撑点），收首轮（逻辑维度）修改意见，意见清单落 `artifacts/07-draft/修改意见-v1.md`。停门后 `check --at-gate 门3`；门通过后 `check --advance C6`。

### C6 三轮修改（多轮迭代，每轮结束自然汇报）

- 每轮 = 意见清单 md → 改后稿 vN → `python scripts/literature_review_check.py <工作根目录> --diff <旧> <新>` 生成修改日志（不凭记忆写日志）。
- 轮 1 **逻辑**：结构连贯/论点推进/章节权重/证据链闭合/逻辑跳跃。
- 轮 2 **内容**：事实准确/覆盖遗漏/客观性/数据支撑/争议平衡。
- 轮 3 **格式**：引用统一/图表编号对应/术语一致/语言润色（细则见 `references/formatting-checklist.md`）。
- 纪律：不引入库外文献（确需补充 → 回 C3 流程并告知）；参考文献编号 1-N 连续无缺口、无"沿用某稿"占位注记。

### C7 助理交接（等回件）→ C8 收尾（→ 门4）

- C7（从工作根目录执行）：`python scripts/literature_review_to_docx.py artifacts/07-draft/改后稿-vN.md artifacts/08-jiaozi/饺子-v1.docx`（两个参数=输入 md 与输出 docx 的相对路径；内置引号配对/斜体污染检查会自动跑）；同目录写 `交接说明.md` 给人类助理：**改文字句子，改完要么存 source/jiaozi/ 要么直接回复意见**。置 blocked_on=jiaozi 等回件（无门）。
- C8：助理回件后（两种形式走同一流程，D3：不做改动大小分支）——回件是文件 → `python scripts/literature_review_from_docx.py <回件.docx> <回件.md>` 回转 → `check --diff` 出助理改动日志；回件是意见 → 直接作为修改意见清单处理。之后 AI 审内容（语义跳变/错漏字）→ 合入为改后稿 vN+1 出下一版 → 按门3 已确认格式成稿（LaTeX 首版由 AI 按模板手工成稿，literature_review_format 脚本为后续版本项）→ `check --cite-audit --strict` → 交付包落 `artifacts/09-deliver/`（终稿+引用审计+库导出+人工核对清单）。**停 门4（终稿验收）**：停门后 `check --at-gate 门4`。

## 5. 停门汇报模板

每次停门输出：已完成内容（数字）/ 当前门 / 发现的问题 / 等待决策的具体问题（逐条）。停门后 `check --at-gate 门N` 登记（blocked_on=user）；C7 等助理回件为 `jiaozi`（无门）；门通过后 `check --advance C<下一走廊>` 推进。不要在非门处停（异常终断除外，见 §0）。

## 6. 失败响应（四级）

1. **重试**：脚本内置，最多 2 次。
2. **降级**：下载失败→摘要级或人工补缺；解析=low 标记。如实记录。人工补缺回灌：用户按清单手动下载 PDF 投递 `source/manual/round<NN|XX>/`（文件名 = paper_id.pdf，如 R02-03.pdf、RX-01.pdf）→ `python scripts/literature_review_fetch.py <工作根目录> --collect-manual --round <N|X>`（配对、复制入 papers/、更新库行）→ `check --round` 复核计数。
3. **跳过**：候选失败→取下一个；绝不硬凑数量。
4. **停下问**（仅三类）：下载渠道大面积缺失、解析大面积低质、连续两轮推荐抽样发现主题漂移。

## 7. 包内参考文件

- `references/expansion-and-coverage.md` — 扩圈策略与盲区审计 SOP（C3 扩圈前必读）
- `references/formatting-checklist.md` — 格式轮检查清单（C6 轮 3 与 C8）
- `templates/writing-req.md` — 成文要求模板（C4）
- `templates/expansion-selection.md` — 扩圈候选入选/剔除与结构检查模板（C3）
- `templates/blind-spot-audit.md` — 时间、方法、来源、群落、语言地域盲区审计模板（C3）

## 8. 抛弃重来

仅门2 处经用户同意触发。机制：reset-attempt 命令自动将 attempt+1、轮计数与 papers 计数清零；**不删不动任何既有文件**；已下载论文经去重机制跨尝试复用，**复用者计入当前尝试计数**（库为全局累积事实，状态块计数为当前尝试快照——C2 首轮重跑时由脚本按 fetch 重扫结果重算，旧尝试已读过的论文 is_read 保留、无需重读）；旧尝试的报告原地保留。工作根目录继续用，账本全局累计。

## 9. 已有文献起步（变体）

用户提供起始文献集合时跳过 C1 检索：先逐篇 convert（PDF）/或以 B 级入账（仅摘要），精读贡献照做，直接从 C2 起跑。状态 theme 标注"已有集合起步"。

## 10. 无脚本环境的最小原则

迁移到没有脚本执行能力的环境时，机械层无法代偿的部分**停下向用户报告环境阻塞**（正常工作流也无法推进，因为下载/转换/审计都依赖脚本）；判断层规则（推荐、精读、主题精炼、扩圈筛选、诚实记账、不删文件）仍可作为纯人工流程的页内约束使用。状态块在任何情况下都不得手改（§2）。

