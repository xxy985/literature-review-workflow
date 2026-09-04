# literature-review-workflow 综述论文半自动生产包

本文件是**注册与部署说明**，不是运行时 SOP。正常调用本 Skill 时，Agent 应读取同目录的 `SKILL.md` 及其明确引用的 `references/`、`templates/`；不应依赖本 README 才能推进业务流程。

## 0. 注册卡（给陌生 Agent）

将本目录注册为 `literature-review-workflow` Skill，并向 Agent 注入以下信息：

```text
你已注册 Skill：literature-review-workflow。
请先阅读：<literature-review-workflow 包路径>/SKILL.md
工作根目录：<工作根目录>
当用户明确说“推进”“继续综述流程”或“推进到下一扇门”时，按 SKILL.md 执行一轮。
运行时只依赖 SKILL.md 及其明确引用的 references/templates，不依赖本 README 或任何外部工作区规则。
```

注册完成的判断：Agent 能说出本 Skill 的用途、三方分工、工作根目录、触发词和四道人工闸门，并知道首次运行应先做环境检查和 `literature_review_new.py` 自举。

## 1. 前置条件（能力契约）

**适用环境**：具备终端命令执行、本地文件读写、网络访问能力的 agent 环境（含人工终端）。只有对话能力、无本地执行能力的模型，或门禁型沙箱（逐命令审批不可授权）环境无法跑本包——这不是缺陷，是流程需要真实文件与真实请求。

**启动器选择**（命令表中的 `python` 按你所在系统替换）：Windows 常为 `python` 或 `py -3`；macOS / Linux 常为 `python3`。下文统一写 `python`。

- Python **3.8+**（Windows / macOS / Linux 均可；当前已在 Windows 11 实测，macOS/Linux 未实测，属待验证项）
- Python 包（见 `requirements.txt`）：**检索、核验、账本核心仅标准库零依赖**；完整流程含阶段依赖——`pymupdf`（C3 convert：PDF转md）与 `python-docx`（C7/C8 docx 交接）在对应走廊前安装即可；无安装权限/无平台 wheel 时对应走廊降级走人工补缺
- 网络可达 `api.openalex.org` 与 `api.crossref.org`（必需）；`api.semanticscholar.org`、`export.arxiv.org`（可选检索与线索源）；PDF 下载阶段会命中论文实际托管域（出版社/机构库，不固定）——企业代理或域名白名单环境需自行放行，异常时可用 `HTTPS_PROXY` 环境变量，自签证书环境见 §7
- 免任何 API 密钥
- 环境自检：`python scripts/literature_review_env_check.py` —— 缺什么会打印精确安装命令；默认离线体检，加 `--net` 才附加 OpenAlex/CrossRef 各 1 次连通性探测（`--net` 通过不能保证后续 PDF 托管域都可达，两者分开判断）

## 2. 目录结构（全部约定自包含，不依赖任何外部工作区规则）

```
literature-review-workflow/                       ← 本技能包（整体拷走即可迁移）
├── SKILL.md                  ← AI 操作手册（走廊 SOP / 停门规则）
├── scripts/                  ← 12 个可执行脚本（见第 6 节命令表）
├── templates/writing-req.md  ← 成文要求模板（C4 用）
├── templates/expansion-selection.md ← 扩圈筛选说明模板（C3 用）
├── templates/blind-spot-audit.md    ← 盲区审计模板（C3 用）
├── references/               ← 扩圈策略 / 盲区审计 / 格式检查表 SOP
├── agents/openai.yaml        ← 可选的 OpenAI 入口描述（非必需入口，任意 agent 可忽略）
└── requirements.txt

<工作根目录>/                 ← 任意空目录，literature_review_new.py 自举生成
├── progress.md               ← 顶部 JSON 状态块=唯一进度账本（脚本唯一写者）
├── source/papers/            ← PDF 全文 + 转出的 md；roundNN/ 分轮存放，roundXX/ 为扩圈批
│   └── library.tsv           ← 论文总账（22 列，一稿一条）
├── source/manual/            ← 人工补缺的 PDF 落点
├── source/jiaozi/            ← 人类助理交回的修改文件（"饺子"为项目内部称谓，指人工文字协作者，可按需改名）
├── artifacts/01-topic ... 09-deliver   ← 九级产物（方向报告→…→交付包）
└── notes/history/            ← 运行日志、排除账（预印本/核验失败记录）
```

## 3. 注册后的首次部署（仅部署，不替代 SKILL.md）

先约定两个路径（下称 `<literature-review-workflow包路径>` 与 `<工作根目录>`，示例中用 `/opt/literature-review-workflow` 与 `/srv/survey`，换成你的实际路径，路径含空格时整体加引号）：在你的 agent 会话里注入这段指令（按你所用工具的方式：系统提示 / 规则文件 / 直接粘贴均可）：

> 请阅读 `/opt/literature-review-workflow/SKILL.md` 并严格按其 SOP 推进综述工作流，工作根目录为 `/srv/survey`。每次用户说"推进"或"继续综述流程"，你就执行一轮：读状态 → 跑当前走廊 → 只在人工闸门处停下等拍板。命令一律以带引号的脚本绝对路径调用（如 `python "/opt/literature-review-workflow/scripts/literature_review_check.py" "/srv/survey" --corridor`），不依赖当前目录。

工具无关性说明：不依赖任何特定 IDE/agent 框架的功能——状态持久化用普通 markdown，运行时规则写在 SKILL.md，换工具只需照搬上面的注册卡。前提是宿主具备 §1 的能力契约（终端执行 / 文件读写 / 网络）；非 agent 环境可人工逐命令使用。

## 4. 流程与闸门（详见 SKILL.md）

| 走廊 | 内容 | 尽头闸门 | 谁拍板 |
|---|---|---|---|
| C1 | 自举+方向+候选池报告 | 门1 检索方案（定主题基调） | 人 |
| C2 | 首轮 10 篇+精读+定轮数(4–8) | 门2 首轮语料批准（可整轮重来） | 人 |
| C3 | 滚动至 40+扩圈 20+建知识库+拟提纲 | 常规汇报（不停门；提纲意见并入门3） | 人 |
| C4 | 成文要求草案 | 并入初稿一起交门3 | 人 |
| C5 | 初稿+引用审计 | 门3 初稿与引用边界确认 | 人 |
| C6 | 三轮修改（逻辑/内容/格式） | 每轮结束自然汇报 | 人 |
| C7 | 交人类助理（docx） | 等助理回件（无门） | 人（含助理） |
| C8 | 定稿格式化+交付包 | 门4 终稿验收 | 人 |

## 5. 硬规则（红线，violated = 事故）

1. **禁止网络发布与对外发送**——任何产物不上传、不外发，仅本地
2. **不覆盖原件**——版本一律新文件（v1/v2/v3），不删除文件（要删请人删）
3. **诚实账本**——没下载到就说没下载到（fetch_status 是唯一真相），不编摘要不编结论
4. **不绕付费墙**——非 OA 拿不到就走人工补缺清单，绝无绕过尝试
5. **极低速率请求**——所有网络请求过内置 RateLimiter（默认 3s+随机抖动 2s）
6. **预印本一律不入库**（无正式发表版不收）；会议论文（proceedings-article）是合法文献

## 6. 命令表（人工逐命令使用时参考）

```
python scripts/literature_review_new.py <工作根目录> --title "主题"           # 自举
python scripts/literature_review_search.py <根> --query "..." [--query ...]    # 检索（可重复）
python scripts/literature_review_fetch.py <根> --candidates <tsv> --round N|X # 核验+下载（N|X=轮号/扩圈）
python scripts/literature_review_dedup.py <根> [--candidates <tsv>]            # 去重
python scripts/literature_review_convert.py <根> --round N|X                   # PDF→md（扩圈批同）
python scripts/literature_review_cite.py <根> --target 20                      # 引文扩圈
python scripts/literature_review_check.py <根> --round N | --full | --corridor | --advance C2 | --at-gate 门N | --diff 旧.md 新.md | --cite-audit 终稿.md
python scripts/literature_review_to_docx.py 草稿.md 交件.docx                  # 交人类助理
python scripts/literature_review_from_docx.py 回件.docx 回件.md                # 收回修改
```

（每条命令 `--help` 有中文说明；完整运行顺序以 SKILL.md 为准。）

## 7. 故障处置

- **下载受限/被 ban** → 脚本自动放慢+如实在 `source/manual/` 生成人工补缺清单（标题/作者/DOI/候选链接），人手动下载放入 `source/manual/roundNN/`（扩圈批 roundXX/）后 `python scripts/literature_review_fetch.py <根> --collect-manual --round N|X` 收编（文件名须为 R02-03.pdf / RX-01.pdf 形式，即 paper_id+.pdf）
- **预印本/核验不过** → 不入 library，进 `notes/history/excluded.tsv` 排除账（带原因），报告里报数
- **脚本异常** → 读报错 → 同命令重试至多 1 次 → 仍失败则停下问人，附错误全文

## 8. 最小走查（验证部署是否成功）

```
python scripts/literature_review_env_check.py
python scripts/literature_review_new.py ./demo-root --title "演示"
python scripts/literature_review_search.py ./demo-root --query "graph neural network survey"
python scripts/literature_review_fetch.py ./demo-root --candidates <上一步输出的tsv> --round 1
python scripts/literature_review_check.py ./demo-root --corridor
```

跑通即完成最小部署检查。演示目录是否移走由用户自行决定；Skill 不主动删除任何文件。之后每次推进只在 Agent 会话里说一声“推进”。

## 能力边界（诚实声明）

自动检索源为 OpenAlex / CrossRef /（可选）Semantic Scholar / arXiv（仅作正式版线索）；付费数据库（Web of Science 等）**不进自动链**——其文献通过官方链接在人工补缺清单兜底。无 OCR（扫描件标记 low 转人工）；LaTeX 格式化脚本为后续版本项，首版由 AI 按模板手工成稿。

