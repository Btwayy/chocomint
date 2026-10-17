# chocomint

个人网页与学习工具。

## 日语 N1 本地复习工具

[项目说明](jlpt-n1-lab/README.md) · [52 天计划](jlpt-n1-lab/reports/study-plan.md) · [题库数据](jlpt-n1-lab/data/reviewed.json)

- 2026-10-17 至 2026-12-07，每天 30 题；360 道不同题目与间隔复习组成 1,560 次练习。
- 题库、答案、中文解析与 AI 编辑复核记录均已预先保存。
- 使用 Python 标准库运行，无需模型、付费 API 或额外依赖。

```sh
cd jlpt-n1-lab
python3 server.py
```

打开 <http://127.0.0.1:8765/>。Mac 也可双击项目中的 `启动题库.command`。

此应用包含 Python/SQLite 后端，GitHub Pages 不运行这个服务；GitHub 上保存的是可在本地运行的完整项目。原有个人网页保留在仓库根目录。

题库来源、许可和 AI 复核边界见项目说明。个人学习记录仅保存在本地 `data/lab.sqlite`，不纳入公开 Git 历史。
