# LaTeX 终稿交付

最终成品必须是 LaTeX 工程及由它编译出的 PDF。Markdown 用于内部写作，DOCX 用于助理改文字，二者均不能替代终稿。

1. 门1记录课题领域；同时提前运行 `python <skill>/scripts/literature_review_env_check.py --delivery`。缺 TeX 环境不妨碍采集，但阻塞最终交付。TeX Live / MiKTeX 需提供 latexmk、XeLaTeX 及模板所需宏包；用 BibLaTeX 时还需要 biber。
2. 门3确认期刊模板、语言、参考文献样式。模板由用户提供；无模板时经认可使用通用模板，并注明未验证目标期刊适配。Agent 按模板编写 main.tex、参考文献数据库和图表，合入助理修改后再次核对论断。
3. 正文工作稿使用 `[doi:10.1234/example]`。参考文献数据库每条必须保留规范化 DOI；优先以 DOI 为引用键。模板不支持某些 DOI 字符时，仅将引用键编码，并在 `doi-map.tsv` 保留“编码键、DOI、成稿引用”一一映射，不引入另一个论文编号系统。
4. 把 main.tex、所有引用的 tex/bib/图表、必需的 cls/sty 和 doi-map.tsv 放在独立版本工程目录。使用相对路径，禁止依赖作者机器绝对路径。保留模板来源及许可信息。
5. 执行 `python <skill>/scripts/literature_review_latex.py <工程绝对路径> <新交付目录绝对路径>`。工具复制工程并用 latexmk + XeLaTeX 编译，保存日志；非零退出、缺 PDF、未解析引用均不能通过。失败后修正源工程，使用新的输出版本重试。
6. 实际逐页渲染 PDF，检查中文字体、公式、表格、图注、参考文献和溢出。逐项对照工作稿、DOI映射和参考文献。编译通过不等于学术或版式验收通过。

门4交付：完整可重编译工程、main.pdf、构建日志、DOI映射、库导出、机械审计与论断核验报告。缺编译器、宏包、字体或模板时记录阻塞；不得宣布终稿已完成。
