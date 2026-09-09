---
name: literature-review-workflow
description: Bilingual literature review workflow / 综述论文半自动生产技能。Use when asked to start, advance, or resume a literature review; 用户要求启动、推进或继续综述流程时使用。Supports source verification, synthesis, claim review, recovery, and four decision gates. Requires Python, terminal, local files, and research-stage network access.
---

# 综述论文半自动工作流

本包为中文独立部署版，所有相对路径均位于本包内；英文用户可从 [部署说明](README.md) 的英文包链接独立安装。两包同步维护、构建及验证，脚本与数据契约一致。交流及笔记沿用用户语言，论文语言单独确认。

目标：从可追溯的文献证据形成有比较、有论证的综述。Agent 负责研究判断与执行；脚本负责确定性机械操作；人在关键门处拍板。讨论技能设计或闲聊不启动论文生产。

## 启动与恢复

1. 明确技能根目录与本篇综述的工作根目录，两者不得混用。命令中的脚本使用技能根目录的绝对路径，输入产物使用工作根目录的绝对路径；引用的文档路径均相对技能根目录。
2. 首次部署运行 `python <skill>/scripts/literature_review_env_check.py`；需要网络时加 `--net`。PDF 转换从 C2 起需要 pymupdf，DOCX 交接需要 python-docx。缺能力时说明阻塞和可继续部分，不假装已完成。
3. 新工作运行 `python <skill>/scripts/literature_review_new.py <work> --title "主题"`。已有工作先读 progress.md，再运行 `python <skill>/scripts/literature_review_check.py <work> --corridor`，按 [恢复规范](references/recovery.md) 核对产物。
4. 仅加载当前阶段操作卡。正常连续推进；小批次结束保存检查点并继续，检查点不是人工门。
5. 明确遇门、等助理、缺环境、重大证据缺口或轮数上限时才停。已有 gate 不能因用户只说“继续”就视为批准，须能从用户回复确定对该门问题的决定。

## 核心约束

- 文献与产物只落本地，不自动上传、邮件、发布或同步。
- 原始输入与交付版本不覆盖；报告、笔记和稿件用版本文件名。机械账本及未交付的机器派生缓存允许工具更新；脚本的临时文件可自行清理，不删除用户文件。
- library.tsv / excluded.tsv 由包内工具写，Agent 不手改。排除账追加留痕；撤销排除追加同键 reason 以 withdrawn 开头的记录，详见公共库说明。
- progress.md 状态块由 new/check 命令写；围栏外自然语言可编辑。计数来自库，研究判断来自笔记，不以状态字段代替证据。
- 正式发表版须经 CrossRef 核验，预印本不入库；仅计算机相关领域接受会议论文，其他领域一律排除，领域未确认时默认排除。不得仅因使用计算机方法将其他领域课题归为计算机领域。已确认正式版的 arXiv 镜像可提供全文。
- 全程以规范化 DOI 为唯一论文标识，工作稿引用写作 `[doi:10.1234/example]`。去掉 doi.org/doi: 前缀并统一小写；无 DOI 的材料只保留为线索。轮次只表示采集批次，不生成论文编号。磁盘文件名为 DOI 的 URL 百分号编码，库中保留原 DOI 与路径。此版不兼容旧编号库，重新核验导入后使用，不覆盖旧资料。
- 最终必须同步交付同一终稿的 Markdown、DOCX、完整 LaTeX 工程，并附 LaTeX 编译出的 PDF。三种格式的正文、论断、数据、公式、图表和参考文献须一致，以该 PDF 作为正式排版验收依据，按 [多格式终稿交付规范](references/latex-delivery.md) 执行。助理交接稿不能代替最终 DOCX；任一必需成果缺失或未通过核对，均不得宣布完整交付。
- 网络请求走包内限速与有限重试，不并发抓取。
- A=已读全文，B=已读摘要；这只表示材料来源，不表示研究质量。B 仅支撑非核心论断，停门向用户报告具体支撑点，终稿不加内部级别标记。
- 保留生产规模：主体40篇、扩圈20篇，主体4–8轮。数量、覆盖和论断支持分别验收，不靠凑数补证据。
- 饺子只改文字或回复意见，不要求其维护技术标记。

## 按阶段加载

| 阶段 | 输入与动作 | 完成后 |
|---|---|---|
| C1 选题与检索 | [采集操作卡](references/stages/collection.md)：研究任务、方向与候选池 | 门1：研究问题、范围、读者及检索方案 |
| C2 首轮阅读 | 同上，并读 [阅读规则](references/reading.md)：首轮10篇全文、笔记、首轮综合 | 门2：首轮语料、主题修正、轮数与文章贡献 |
| C3 滚动与扩圈 | 采集操作卡 + [综合规则](references/synthesis.md) + [扩圈规则](references/expansion-and-coverage.md) | 库与核心问题覆盖合格后继续 |
| C4–C5 提纲与初稿 | [写作操作卡](references/stages/writing.md) + [论断核验](references/claim-review.md) | 门3：初稿、提纲、成文要求与引用边界 |
| C6 修改 | 写作操作卡：逻辑、内容、格式三轮销项 | 自动继续 |
| C7–C8 交接与交付 | [交付操作卡](references/stages/delivery.md) | 门4：终稿验收 |

门通过后 `check --advance C2|C3|C6`；自动阶段之间同样用 `--advance C4|C5|C7|C8` 记录位置，不引入新人工门。停门用 `--at-gate 门1|门2|门3|门4`，完整命令始终包含脚本路径和工作根目录。`--advance` 只登记位置，不能证明授权或质量通过；Agent 必须核对该阶段产物与用户决定。

停门汇报：已完成内容及文件 / 当前门 / 证据缺口与 B 级支撑点 / 需要用户决定的具体问题。门4通过后在自然语言进度区登记验收和交付版本；保留门4状态作为最后检查位置，不重复交付。

## 产物与路径

自举创建 source/papers、source/manual、source/jiaozi、notes/history 和 artifacts/01-topic 至 09-deliver。产物职责：
01-topic 研究任务与检索；02-recommend 排序推荐；03-library 库验收与扩圈；
04-knowledge-base 阅读证据；05-outline 综合与提纲；06-writing-req 成文要求；
07-draft 工作稿与论断核验；08-jiaozi 交接；09-deliver 终稿及审计。

模板按使用时加载：[阅读笔记](templates/reading-note.md)、[综合表](templates/synthesis.md)、[论断记录](templates/claim-evidence.md)、[检查点](templates/checkpoint.json)、[成文要求](templates/writing-req.md)。第一次执行阅读、综合或核验时参考 [贯通示例](examples/evidence-to-synthesis.md)，示例为虚构教学材料，不能入真实文献库。

## 验证与能力边界

脚本通过只证明它声明检查的机械条件。论文是否支持论断、研究是否可比以及缺口是否成立，由 Agent 按原文核验；无法判断则保留未解决项。

维护或迁移技能时使用 [验收任务](evals/README.md)。离线回归与教学样例不代替真实课题首跑；测试可缩小语料规模，生产仍遵守40+20和既定人工门。包内工具不可用时可做人工判断与整理，但不得声称完成机械链路。
