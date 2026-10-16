# Squirrel Analysis Skill

用于编写 [Squirrel](https://github.com/cracknuts-team/squirrel) 侧信道分析与轨迹预处理脚本的 Codex skill。技能会按任务读取对应的 API 文档和参考示例，再生成适配用户数据的 Python 脚本。

## 使用

将本仓库目录放入 Codex 的 skills 目录，以 `$squirrel-analysis` 调用；支持自动触发的环境也可直接描述 Squirrel 分析任务。运行生成的脚本仍需在 Python 环境中安装 Squirrel（发行包名 `cracknuts-squirrel`）及相应依赖。MIA 当前还需要 `pyitlib`。

## 内容

- [SKILL.md](SKILL.md)：任务路由和脚本编写要求。
- [API 索引](references/docs/api-index.md)：公开分析与预处理方法概览。
- [方法文档](references/docs/datasheet/)：各方法的详细说明。
- [使用说明](references/usage.md)：Squirrel 项目环境与通用示例。
- [参考示例](references/examples/)：从 Squirrel 验证流程整理的脚本，仅供理解调用方式；其中的路径和测试数据约定需要替换。

文档与示例是 Squirrel 项目的本地快照。若安装版本的 API 与文档不同，应以当前安装包的公开 API 为准。

## 来源与许可

本仓库包含源自 [cracknuts-team/squirrel](https://github.com/cracknuts-team/squirrel) 的文档和验证示例。原项目在 `pyproject.toml` 中声明 `Apache-2.0` 许可；本仓库按 [Apache License 2.0](LICENSE) 发布。
