# 综述论文半自动工作流

可独立部署的中文 Agent Skill。直接注册本目录并先阅读 [SKILL.md](SKILL.md)。本目录自带全部脚本、参考资料、模板、测试和依赖声明，不依赖英文包。

注册提示：

```text
你已注册 Skill：literature-review-workflow-zh。
请先阅读 <skill-path>/SKILL.md。工作根目录为 <work-root>。
当我说“推进”“继续综述流程”或“推进到下一扇门”时，按 SKILL.md 执行一轮。
```

在本目录运行 `python scripts/literature_review_env_check.py` 检查环境。最终交付必须基于同一冻结内容基准，包含清洁 Markdown、最终 DOCX、完整 LaTeX 工程和由其编译的 PDF。仅计算机相关领域接受会议论文，DOI 是全程唯一论文标识；LaTeX 需要 `latexmk` 和 `xelatex`。

本包与 `en/literature-review-workflow/` 使用同一脚本和数据契约同步开发、评审与发布，不是英文包的事后翻译。
