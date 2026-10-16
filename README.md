# Squirrel Analysis Skill

用于编写 [Squirrel](https://github.com/cracknuts-team/squirrel) 侧信道分析与轨迹预处理脚本的通用 Agent Skill。支持 `SKILL.md` 的 Agent 可以直接加载；其他能够读取本地文件的 Agent 也可以按本文手动使用。技能会按任务读取对应的 API 文档和参考示例，再生成适配用户数据的 Python 脚本。

## 如何使用

1. 克隆或下载**整个仓库目录**，保留 `SKILL.md` 与 `references/` 的相对位置。
2. 如果 Agent 支持自动发现 Skills，将目录命名为 `squirrel-analysis` 并放入该 Agent 的技能目录。例如，OpenCode 可使用项目内的 `.opencode/skills/squirrel-analysis/` 或 `.agents/skills/squirrel-analysis/`；其他 Agent 按各自的技能目录规则放置。
3. 向 Agent 描述任务、数据格式和目标。例如：

   > 使用 squirrel-analysis 技能，为我的 Zarr 轨迹编写 CPA 分析脚本。轨迹和明文分别位于 `/0/0/traces` 与 `/0/0/plaintext`，输出每个密钥字节的最佳猜测和分数。

如果 Agent 没有 Skill 自动发现功能，直接提供 `SKILL.md` 的路径，并要求它先读取该文件，再按其中的链接读取相关 API 文档和示例。不同 Agent 的显式调用命令可能不同，无需依赖 `$squirrel-analysis` 这一特定写法。

运行生成的脚本仍需在 Python 环境中安装 Squirrel（发行包名 `cracknuts-squirrel`）及相应依赖。MIA 当前还需要 `pyitlib`。`agents/openai.yaml` 仅提供 OpenAI 产品的界面信息，其他 Agent 可忽略。

## 内容

- [SKILL.md](SKILL.md)：任务路由和脚本编写要求。
- [API 索引](references/docs/api-index.md)：公开分析与预处理方法概览。
- [方法文档](references/docs/datasheet/)：各方法的详细说明。
- [使用说明](references/usage.md)：Squirrel 项目环境与通用示例。
- [参考示例](references/examples/)：从 Squirrel 验证流程整理的脚本，仅供理解调用方式；其中的路径和测试数据约定需要替换。

若安装版本的 API 与文档不同，应以当前安装包的公开 API 为准。

## 来源与许可

本仓库包含源自 [cracknuts-team/squirrel](https://github.com/cracknuts-team/squirrel) 的文档和验证示例。原项目在 `pyproject.toml` 中声明 `Apache-2.0` 许可；本仓库按 [Apache License 2.0](LICENSE) 发布。
