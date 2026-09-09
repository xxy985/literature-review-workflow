# 中英文同步维护 / Bilingual maintenance

[中文入口](README.md) · [English entry](en/README.md)

## 共同契约 / Shared contract

中英文是同一技能的同步版本，共享根目录scripts/、requirements.txt与机器字段，agents界面文案按语言配对。每次修改同时更新文档、模板与CHANGELOG。根目录中文文件对应en/下英文文件。en/仅为开发源，不直接注册；构建后两包各自包含全部依赖，无需另一个包。

Chinese and English are maintained together, sharing scripts/, requirements.txt, and machine fields; Agent interface text is paired by language. Update both documents, templates, and changelogs in the same change. Matching paths under en/ identify English sources. The en/ directory is for authoring, not direct installation. Each built package includes all required files and never depends on the other language package.

## 语言与接口 / Language and interfaces

用户交流、Agent笔记与报告沿用用户语言；论文语言、长度单位和引用样式单独确认。脚本的中文输出和固定路径目前保持不变，由Agent解释结果；必须保留真实路径、CLI参数、JSON/TSV字段及状态枚举。门1–门4是机器参数，英文界面可称Gate 1–4；jiaozi表示文字助理等待状态，不是英文用户必须认识的人名。

Use the user's language for conversation, agent-written notes, and reports. Confirm manuscript language, length units, and citation style separately. Some script messages and fixed filenames remain Chinese; the agent explains them in English while preserving exact paths, CLI arguments, JSON/TSV keys, and state values. Gate 1–4 correspond to the literal CLI values 门1–门4. The jiaozi state means waiting for a copyeditor; users do not need to know anyone by that name.

## 维护验收 / Maintenance checks

逐项核对数字、否定、义务强度、条件、例外、命令与文件契约，独立通读英文。运行 `python -m unittest discover -s evals -p "test_bilingual.py" -v` 检查配对完整、模板表格、状态结构、包内链接及日志日期。自动检查不证明语义等价，维护者仍需逐命题核对。

Review numbers, prohibitions, obligation strength, conditions, exceptions, commands, and file contracts, then read the English on its own. Run `python -m unittest discover -s evals -p "test_bilingual.py" -v` for file parity, template tables, state structure, package-local links, and changelog dates. Structural checks do not establish semantic equivalence.

## 分发 / Distribution

执行 `python maintenance/build_packages.py --version 2026.09.09.1`，同步生成dist下两个ZIP、SHA256SUMS.txt。脚本仅按清单打包，不包含.git、缓存或另一语言文档。两包VERSION.json的release相同，content_sha256分别记录内容。更新后先验证再重建两个包，并在同一提交推送源文件与dist。

Run `python maintenance/build_packages.py --version 2026.09.09.1` to produce both ZIPs and SHA256SUMS.txt under dist/. Only allowlisted files are included, excluding .git, caches, and the other edition. VERSION.json shares a release value and records each edition's content hash. Validate, rebuild both archives, and commit source and dist together. Existing versioned local deliveries are preserved; stable download links point to the latest dist files.

术语 / Terms: 走廊 = stage; 人工门 = decision gate; 扩圈 = citation expansion; 盲区审计 = coverage-gap audit; 精读 = close reading; 论断核验 = claim verification; 饺子 = copyeditor; 骨架 = workspace structure.
