# Literature Review Workflow

一个面向 Agent 的半自动学术综述生产 Skill。

它帮助具备终端、文件读写和网络能力的 Agent，按可恢复、可审计的方式推进：

`选题 → 文献检索 → 正式发表核验 → 全文获取 → 精读与扩圈 → 跨论文综合 → 提纲 → 初稿 → 论断核验 → 修改与交付`

这是一个 Skill 包，不是无人值守的论文生成程序。Agent 负责判断、阅读、编排和写作；脚本负责确定性的检索、核验、下载、转换、账本和审计；人在关键闸门处拍板。

## 适用范围

适合：

- 需要跨会话恢复的综述论文项目；
- 需要保留文献来源、全文状态和版本记录的研究工作；
- 使用不同 Agent、IDE 或本地工作目录进行迁移和协作。

不适合：

- 没有终端或本地文件能力的纯聊天模型；
- 期待无人监督生成可靠终稿的场景；
- 需要绕过付费墙、自动发布或对外发送材料的场景。

## 快速开始

### 1. 获取 Skill

可以直接下载本仓库，或克隆到本地：

```bash
git clone https://github.com/xxy985/literature-review-workflow.git
```

Skill 包根目录就是包含本文件和 `SKILL.md` 的目录。

### 2. 注册给 Agent

将本目录注册为 Skill，并向 Agent 提供下面的信息：

```text
你已注册 Skill：literature-review-workflow。
请先阅读 <skill-path>/SKILL.md。
工作根目录为 <work-root>。
当用户明确说“推进”“继续综述流程”或“推进到下一扇门”时，按 SKILL.md 执行一轮。
运行时只依赖 SKILL.md 及其明确引用的 references/templates，不依赖本 README 或其他外部工作区规则。
```

其中：

- `<skill-path>` 是本仓库在本机的绝对路径；
- `<work-root>` 是用于某一篇综述的独立工作根目录，不要与 Skill 包目录混用。

### 3. 检查环境

```bash
python scripts/literature_review_env_check.py
```

需要检查网络时：

```bash
python scripts/literature_review_env_check.py --net
```

### 4. 开始工作

注册后明确要求“启动综述流程”，Agent 按 `SKILL.md` 自举工作根目录并推进到第一个人工门。之后说“推进”可继续；停在决策门时需回答该门问题。只注册或讨论技能不会自动启动论文生产。

命令示例中的 `scripts/` 相对技能根目录。Agent实际调用推荐使用脚本和输入文件的绝对路径。当前版统一使用 DOI，不兼容旧编号库；请在独立目录重新核验导入，保留旧资料。版本历史见 [CHANGELOG](CHANGELOG.md)。

## 能力要求

| 能力 | 用途 | 必需阶段 |
| --- | --- | --- |
| Python 3.8+ | 运行包内脚本 | 全流程 |
| 终端执行 | 调用脚本和查看结果 | 全流程 |
| 本地文件读写 | 创建工作区、账本和产物 | 全流程 |
| 网络访问 OpenAlex/CrossRef | 检索和正式发表核验 | C1-C3 |
| `pymupdf` | PDF 转 Markdown | C2-C3 |
| `python-docx` | DOCX 交接 | C7-C8 |
| latexmk + XeLaTeX（TeX Live / MiKTeX） | LaTeX 源码编译为终稿 PDF | C8 必需 |

检索、核验和账本核心只使用 Python 标准库；完整流程的阶段性依赖见 `requirements.txt`。没有脚本执行能力时，可以参考流程规则进行人工处理，但无法完成完整的机械链路。

## 工作方式

| 角色 | 主要职责 |
| --- | --- |
| Agent | 读取状态、选择下一步、推荐文献、精读、主题精炼、写作和汇报 |
| 脚本 | 检索、CrossRef/OpenAlex 核验、预印本过滤、下载、转换、账本和审计 |
| 人 | 主题基调、首轮语料、初稿与引用边界、终稿验收 |

运行时规范以 `SKILL.md` 为准。README 只负责项目介绍、注册和部署，不重复运行时 SOP。

## 文件导航

- `SKILL.md`：Agent 运行时操作手册，正常调用时首先阅读。
- `scripts/`：确定性工具；每个脚本都支持 `--help`，公共接口以脚本实际参数为准。
- `references/stages/`：采集、写作、交付操作卡，明确输入、动作、产物、验收与恢复。
- `references/`：精读、跨论文综合、论断核验、恢复、扩圈及格式规则。
- `templates/`：阅读证据、综合、论断映射、检查点、成文要求等工作表。
- `examples/`：从原文证据到综合写作的教学示例（虚构材料，不可用于真实引用）。
- `evals/`：离线回归与中断恢复、证据边界等行为验收任务。
- `agents/openai.yaml`：可选的 OpenAI 入口描述；其他 Agent 可以忽略。
- `requirements.txt`：阶段性 Python 依赖清单。

## 重要边界

- 预印本不进入正式文献库；已正式发表论文可以使用其预印本镜像作为全文来源。
- 仅计算机相关领域接受会议论文；其他领域及未确认领域默认排除。CrossRef 确认正式类型，OpenAlex article 不能证明是期刊论文。
- DOI 为全程唯一论文标识。最终交付固定为 LaTeX 工程及编译 PDF；Word 仅作助理交接。
- 不绕过付费墙；下载失败会留下人工补缺清单。
- 摘要级证据只能支撑非核心论点，不能伪装成全文证据。
- 所有材料只落本地，不自动上传、发布、邮件发送或同步到外部服务。
- 原始文件不覆盖，版本独立保存，删除操作由用户自行决定。
- 最终学术判断、事实复核和署名责任仍由用户承担。

## 当前状态

当前版本已包含：

- 13 个 Python 工具脚本；
- CrossRef/OpenAlex 核验和预印本过滤；
- 引文、被引和相关推荐扩圈；
- AI 手工扩圈筛选和盲区审计模板；
- PDF/Markdown/DOCX 交接与 LaTeX 编译链路；
- 版本差异、引用和全库审计。
- 可验证产物的检查点写入、逐单元恢复和原子状态保存；
- 精读证据、跨论文综合及核心论断核验规范；
- 工作稿 `[doi:...]` 与终稿引文映射，显式区分机械审计和语义核验。

交付前执行 `python scripts/literature_review_env_check.py --delivery`；编译入口为 `python scripts/literature_review_latex.py <工程目录> <新交付目录>`，详见 [LaTeX交付规范](references/latex-delivery.md)。缺编译器或编译失败即阻塞，不能以 Word/Markdown 替代终稿。

维护者可运行 `python -m unittest discover -s evals -p "test_*.py" -v`。引用审计 `--strict` 在零可识别引用、未知编号或阅读状态不完整时失败；轮验收未通过返回2。`--fulltext-only` 让首轮配额只计全文；下载中断后的 `--limit` 是本次新增名额，需扣除已取得数量。

研究问题、读者与范围在前两门确认；初稿细节在门3确认。四道人工作决策门和生产40+20规模保持不变。真实首跑前不把机械回归结果解读为论文质量达标。

仍待通过真实使用校准：

- 真实课题从 C1 到 C3 的首跑；
- macOS/Linux 实测；
- 候选过滤率、OA 下载率、扩圈质量和轮数参数校准。

## License

当前仓库未附加开源许可证。除非仓库所有者另行说明，代码、文档和模板的公开可见不等于授予再分发或改编许可。
