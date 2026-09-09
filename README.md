# Literature Review Workflow

This repository provides two standalone Agent skill packages. Use the package that matches the language of the user interface; each directory contains its own `SKILL.md`, scripts, references, templates, tests, and requirements, and neither package depends on the other.

English package: `en/literature-review-workflow/`

Chinese package: `zh/literature-review-workflow-zh/`

Register the corresponding directory directly with your Agent and point it to that package's `SKILL.md`. No ZIP archive, download link, or `BILINGUAL.md` is required. The two editions are developed, reviewed, and released synchronously from the same data contract; the English edition is not a later translation.

Both packages enforce the same workflow rules: conference papers are admitted only for confirmed computer-science reviews; all papers use normalized DOI as the sole identifier; preprints are excluded; CrossRef verifies formal publication type; and a final review is delivered from one frozen content baseline as clean Markdown, DOCX, a complete LaTeX project, and its compiled PDF. LaTeX delivery requires `latexmk` and `xelatex`.

## 中文说明

本仓库提供两个可独立部署的 Agent Skill 包：`en/literature-review-workflow/` 和 `zh/literature-review-workflow-zh/`。中文用户直接注册后者，英文用户直接注册前者；每个目录都自带 `SKILL.md`、脚本、参考资料、模板、测试和依赖声明，不依赖另一个语言包。

当前不提供 ZIP、下载链接或 `BILINGUAL.md`。中英文版本从同一数据契约出发同步开发、评审和发布，英文版不是事后补译。两包遵循相同准入与交付规则：仅计算机相关领域接受会议论文，全文流程统一使用 DOI，最终同一终稿同步交付 MD、DOCX、完整 LaTeX 工程及编译 PDF；LaTeX 需要 `latexmk` 和 `xelatex`。

## License

No open-source license is attached. Public visibility does not grant redistribution or modification rights unless the owner states otherwise.
