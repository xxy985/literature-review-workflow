#!/usr/bin/env python3
"""自举：建立工作根目录骨架与初始状态（走廊 C1 起点）。

用法：python literature_review_new.py <工作根目录> --title "综述主题"
行为：
- 建立全部目录骨架与三本账（幂等，已存在则跳过）；
- progress.md 已有状态块则拒办（不覆盖原则），需 --resume 补建缺失骨架；
- 写初始状态块（attempt=1, corridor=C1, theme=标题）并留运行日志。
退出码：0 成功；1 运行失败；2 参数错误。
"""

import argparse
import os
import sys


def _parse_args(argv):
    p = argparse.ArgumentParser(description="自举工作根目录骨架与初始状态")
    p.add_argument("work_dir", help="工作根目录（不存在则创建）")
    p.add_argument("--title", default="", help="综述主题（写进状态块 theme）")
    p.add_argument(
        "--resume",
        action="store_true",
        help="progress.md 已存在时仅补建缺失骨架，不动状态",
    )
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    import literature_review_lib as lib

    lib.fix_encoding()
    work_dir = args.work_dir
    try:
        os.makedirs(work_dir, exist_ok=True)
        lib.ensure_paths(work_dir)
    except (OSError, RuntimeError) as e:
        print(f"建立骨架失败：{e}", file=sys.stderr)
        return 1
    prog = os.path.join(work_dir, lib.PROGRESS_REL)
    if os.path.isfile(prog):
        state = lib.read_state(work_dir)
        if state:
            if args.resume:
                print(f"骨架补建完成（保留既有状态）：{work_dir}")
                return 0
            print(
                "progress.md 已有状态块，拒办（不覆盖原则）。",
                "重建请移走旧目录或用 --resume 补建骨架。",
                file=sys.stderr,
            )
            return 1
    theme = (args.title or "").strip() or "（待 C1 定方向）"
    try:
        state = lib.write_state(
            work_dir, theme=theme, corridor="C1", gate="", attempt=1, blocked_on=""
        )
        lib.log_run(work_dir, "C1", "new-init", f"theme={theme[:80]}")
    except RuntimeError as e:
        print(f"写入状态失败：{e}", file=sys.stderr)
        return 1
    print(f"自举完成：{work_dir}")
    print(f"  主题：{theme}")
    print(f"  状态：attempt={state.get('attempt')} corridor={state.get('corridor')}")
    print("下一步：按 SKILL.md C1 设计 3-5 组检索式，运行 literature_review_search.py。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

