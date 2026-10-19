# 余白 · N1 本地复习题库

已预先准备 **2026-10-17 至 2026-12-07，共52天，每天30题**。

- **360道不同题目**：150道读音、150道词汇填空、60道语法，覆盖150个词汇与30个语法点。
- **1,560次练习**：360次新题 + 1,200次固定间隔复习。不是1,560道互不相同的新题；新增读音与填空题可能共享例句。
- 原120题在本机Ollama生成后由Codex逐题复核；新增240题由当前Codex对话原创并复核，无新增Ollama请求。
- 用户无需审核。存在多个自然答案、错误接续或合法异读干扰项的4组草稿组合已废弃并改写。
- 内容为词汇/语法巩固，不含听力、长篇阅读或完整模拟卷；AI编辑仍可能漏错，未经实际N1难度标定。

计划见 `reports/study-plan.md`；完整每日题目和答案解析位于 `data/daily/YYYY-MM-DD.json`，主题单为 `data/study-plan.json`。全部已落盘，平时学习无需启动LLM或每日生成。

## 仓库位置与手机布局

本项目现保存于 `~/Documents/repo/chocomint/jlpt-n1-lab`；原 `~/Documents/personal/jlpt-n1-lab` 作为迁移时备份保留。今后请从新目录启动，学习记录写入新目录。

320、375、390像素手机视口已检查并修复布局；验证范围与截图见 [迁移和手机检查报告](reports/migration-mobile.md)。现已同时支持 Vercel/GitHub Pages 静态访问与本机 Python 服务；访问方式见下文。

公开Git包含题库、计划、原始生成响应与修订记录。SQLite学习记录、日志和会话检查点在本地完整保存，按 `.gitignore` 排除；克隆仓库后首次启动会创建自己的空数据库。

## 线上静态版（Vercel / GitHub Pages）

访问 [余白 N1 练习](https://mintbtw.vercel.app/jlpt-n1-lab/web/)。保留仓库目录结构即可，入口是 `jlpt-n1-lab/web/index.html`，CSS、脚本和静态题库均使用相对路径；无需运行Python、配置模型API或启用数据库服务。

静态版直接读取 `data/candidates.json` 与 `data/study-plan.json`。作答、收藏和疑问保存于当前站点的浏览器localStorage，**不会跨设备同步，也不会自动读取本机SQLite**。清除网站数据会删除浏览器记录，请定期点击“备份学习记录”导出JSON。浏览器拒绝存储或空间不足时会明确提示保存失败，不会假装保存成功。

本机 `python3 server.py` 保留原有SQLite模式，访问 `http://127.0.0.1:8765/` 时自动使用它。题库本身和每日安排相同，两种方式的学习记录分开。

## 开始练习

在这个目录运行：

```sh
python3 server.py
```

浏览器打开 <http://127.0.0.1:8765/>。学习和审核已生成的题目不需要启动模型，只有继续出题、模型检查时才需要 Ollama。网页只监听本机地址，无需账号；题库和学习记录保存在本地。关闭运行服务的终端会停止网页服务，数据仍保留。也可双击 `启动题库.command`。

1. 默认进入“日期练习”，选择日期后做当天30题；也可在“自由练习”查看全部360题。首日30道新题，此后每天7–8道新题加22–23道复习题，12月1日至7日只复习。完成数按日期、题号和内容版本去重，刷新不会丢失。
2. 每题显示 Codex（AI）的复核说明；展开“来源与生成记录”可查看核对资料。
3. “加入个人收藏”只保存你的个人标记，不代表专业审校。
4. 有疑问时可记录并点击“报告疑问，暂停本题”；本题暂时移出练习，可在“全部题目”恢复。
5. AI 复核用于知识点巩固，仍可能有错，题目未经真实 N1 难度标定。

最初 120 题已经逐题复核，44 题改过题干或选项，其余也整理了解析。详见 `reports/codex-review.md`。原稿和逐题记录均保留，没有伪造你的审核记录。

网页底部可以导出52天题单、全部题目、复核题库、个人收藏和学习记录。完整备份应包括 `data/`（尤其 `lab.sqlite`）以及 `reports/`；备份 SQLite 时先停止网页服务，避免漏掉 WAL 中的写入。

## 继续生成或重新生成

首次准备环境（本机已完成安装与模型下载）：

```sh
brew install ollama
OLLAMA_NO_CLOUD=1 OLLAMA_HOST=127.0.0.1:11434 ollama serve
```

另一个终端运行：

```sh
ollama pull qwen3.5:27b-q4_K_M
python3 lab.py generate
python3 lab.py blind-check --model qwen3.5:9b-q4_K_M
python3 lab.py export
```

这三个命令默认跳过已完成的工作，可以中断后继续。

```sh
# 仅生成前 3 个知识点（已有结果会跳过）
python3 lab.py generate --limit 3

# 用同一知识点生成新版本；原模型响应保留在 data/raw/
python3 lab.py generate --target 配慮 --force

# 对发生变化的题目重新盲答，再更新报告
python3 lab.py blind-check --model qwen3.5:9b-q4_K_M
python3 lab.py export

# 查看当前数量、检查状态与推理统计
python3 lab.py status
```

可用 `--model` 指定已下载的其他本地模型。题目重生成后内容哈希改变，旧审核与旧模型检查自动失效。`--force` 重新生成的是一整个知识点对应的两道题，并会把当前内容抽查、模型问题及你保存的审核笔记作为改写依据，要求更换语境。

## 生成与校验方法

- **底库**：固定版本的 OpenJLPT 数据；`data/sources/manifest.json` 记录提交 SHA、下载地址及 SHA-256。
- **知识点选择**：`data/targets.json`，含 50 个词汇、10 个语法点、中文考点和词汇干扰项。社区标签仅供参考，不代表完整 N1 考试范围。
- **出题**：词汇题先固定选项，再由模型写语境和逐项解析，减少近义词多解。语法题由模型写两个不同语境。读音正确项来自底库；干扰项采用另外整理的读音混淆表，随后由程序打乱顺序。
- **结构校验**：检查四个非空选项、去除空白后的重复项、答案范围、恰好一个填空、正确词与目标一致、读音与底库一致、重复题干等。
- **盲答**：仅对词汇填空和语法题向模型发送题型、题干、选项，隐藏目标知识点、答案、翻译、解析和出处，要求返回全部可成立选项的原文；程序把原文映射回编号，避免模型报错索引。与预设答案一致且日语自然才通过。
- **Codex 编辑复核**：逐题将四个选项代入完整句子，检查答案唯一性、自然度、中译与解析；有疑问的规则查阅词典和教学资料。复核结论与内容哈希绑定，改题后自动失效。用户不必审核。

本次试验由 27B 模型出题，读音正确性按底库核对；词汇填空和语法使用 9B 模型隐藏答案复答，少量初始检查使用 27B 自检。每题保留实际检查模型与方法。两者都属于 Qwen3.5 家族，可能共同出错，不能视为独立专家验证。读音底库可能没有列出全部合法异读；读音选项也可能偏简单。这些都是需要人工检查的内容。

`python3 scripts/watch_checks.py` 可在生成期间处理已完成的题目（需先下载 `qwen3.5:9b-q4_K_M`），最终完成 50 道读音词典核对与 70 道词汇/语法盲答。CLI `blind-check` 的默认模型仍是 27B；可用 `--model qwen3.5:9b-q4_K_M` 更改。

## 文件

| 文件 | 用途 |
|---|---|
| `data/targets.json` | 60 个知识点和对应参考材料 |
| `data/batches/` | 每个知识点对应的生成结果 |
| `data/raw/` | 原始请求、模型响应、耗时与 token 统计 |
| `data/audits/` | 词汇/语法盲答结果，另保留早期读音试验记录 |
| `data/candidates.json` | 含校验结果的全部候选题 |
| `data/reviewed.json` | 经 Codex 逐题复核的练习题库；`approved.json` 为个人收藏 |
| `data/revisions/` | 历次修订原稿，含整批复核前的 120 题 |
| `data/lab.sqlite` | 个人收藏、疑问笔记、答题记录 |
| `reports/pilot-report.md` | 当前试验进度和自动标记的问题 |
| `reports/summary.json` | 可供程序读取的统计 |
| `reports/experiment-notes.md` | 模型出错实例、方法调整和结果限制 |

## 验证代码

仅使用 Python 标准库，无需安装 Python 包或 Node 依赖。

```sh
python3 -m unittest discover -s tests -v
node --check web/app.js
node --test tests/storage.test.cjs
```

测试使用临时数据库，不会将测试题或测试审核结果写入你的题库。

## 来源和许可

底库来源：[OpenJLPT](https://github.com/evanclan/OpenJLPT)，包含 EDRDG 的 JMdict / KANJIDIC2、Jonathan Waller 的社区 JLPT 分级表和 Tatoeba 例句。具体归属、上游许可和数据版本见 `data/sources/OpenJLPT-NOTICE.md`、`OpenJLPT-LICENSE.txt` 与 `manifest.json`。

本项目分发的候选题及知识点数据按 **CC BY-SA 4.0** 提供，保留来源说明；不从付费题库抓取内容。自行导入其他材料时，需单独核对使用许可。模型采用其自身许可；本地运行器 Ollama 的许可与题库数据许可不同。
