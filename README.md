# dify-nodes

Dify 工作流与 Chatflow 搭建技能(Agent Skill)。面向不熟悉 Dify 的使用者:通过需求沟通,产出一份**逐节点的搭建方案文档**——文字流程图、每个节点每个字段填什么、知识库 RAG 怎么接,照着在 Dify 画布上操作即可完成搭建;确认后可按需转换为**可直接导入 Dify 的 DSL 文件**,并经校验脚本把关。

## 两种交付物

1. **搭建方案文档**(默认):面向人的配置说明,不依赖导入功能,适合任何使用者照着做。
2. **DSL 文件**(可选):`version: "0.6.0"` 的可导入 YAML;涉及知识库、工具插件、模型供应商等租户相关字段时,用占位值并明确标注「导入后需手动补配」。

## 安装

- **方式一(推荐)**:复制下面这段话,发给你的 AI 助手(Claude Code、Codex、Qoder、CodeBuddy、WorkBuddy 等均可)即可完成安装。

```text
请帮我安装这个 Agent Skill:https://github.com/guxiao7538/dify-nodes
下载后放入你的技能目录,读取其中的 SKILL.md 并按其说明工作。
```

- **方式二(手动)**:从 [Releases](https://github.com/guxiao7538/dify-nodes/releases) 下载 zip,解压后把 `dify-nodes/` 目录放入所用 Agent 的技能目录,由 Agent 自动识别。

## 使用

对助手说:

- 「帮我做一个基于产品 FAQ 知识库的客服 Chatflow」→ 产出搭建方案文档
- 「按方案生成 DSL 文件」→ 产出可导入的 YAML 并自动校验
- 「这个 Dify 工作流的 DSL 有什么问题」→ 审查与修复

## 结构

```
SKILL.md                      工作流程与硬规则入口
references/node-schemas.md    全部 27 种节点的配置、输出变量、易错点
references/code-node.md       代码节点专项(沙箱限制、预装包、模板、常见坑)
references/dsl-structure.md   DSL 结构、变量引用、依赖、导入敏感字段
references/solution-template.md  方案文档模板(文字流程图规范)
scripts/validate_dsl.py       DSL 校验:结构、引用、代码节点静态检查
```

## 校验脚本

```bash
python3 scripts/validate_dsl.py <file.yml>
# 缺 PyYAML 时: pip install pyyaml
# 或 uv:        uv run --with pyyaml python3 scripts/validate_dsl.py <file.yml>
```

检查:节点/边结构、handle 一致性、变量引用、依赖格式、代码节点(`def main` 签名、参数名与输入变量一致、返回键与 `outputs` 一致、输出类型合法)。

## 版本

- 节点枚举与沙箱限制基线取自 Dify 官方源码与 docs.dify.ai(2026-09)。
- 变更语义化:`v0.x` 功能迭代,`v1.0` 前接口可能调整;升级看 git tag。

## License

MIT
