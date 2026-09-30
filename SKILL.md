---
name: dify-nodes
description: >
  Dify 工作流与 Chatflow 搭建助手。用于:搭建 Dify 应用、设计工作流节点、
  配置知识检索(RAG)、编写代码节点、生成或修改可导入 Dify 的 DSL YAML 文件、
  排查节点配置与 DSL 导入问题。先通过需求沟通产出面向人的逐节点搭建方案文档
  (文字流程图 + 每个字段的具体取值),可按需转换为可直接导入的 DSL 文件。
---

# Dify 工作流搭建

Dify 是开源的 LLM 应用开发平台。本技能覆盖从需求到落地的完整流程,交付两种产物:

1. **搭建方案文档**(默认交付物):面向人的逐节点配置说明,照着在 Dify 画布上操作即可完成搭建,不依赖导入功能。
2. **DSL 文件**(可选交付物):可导入 Dify 的 YAML 文件,由已确认的方案文档转换而来。

优先交付方案文档;仅在对方明确要求时才生成 DSL 文件。

## 工作流程

### 第 1 步:澄清需求

只澄清影响方案结构的问题,合并为一次提问;能从上下文推断的直接采用,并在方案文档中注明假设。

1. **应用模式**:`workflow`(自动执行,适合批量处理、定时任务、API 调用)还是 `advanced-chat`(Chatflow,多轮对话,适合助手、客服)。提及"聊天/助手/对话"用 advanced-chat,提及"自动处理/批量/流水线"用 workflow,拿不准才问。
2. **输入**:用户或调用方提供什么(文本、文件、图片、数字),从哪里来。
3. **输出**:最终要拿到什么结果、什么格式。
4. **外部依赖**:是否使用知识库(需已在 Dify 建好)、工具插件(需已安装)、模型供应商(需已配置)。这三类依赖决定节点配置与 DSL 的可导入性。
5. **仅 workflow 模式**:触发方式(手动、定时触发器、Webhook 触发器)。

### 第 2 步:产出搭建方案文档

- 撰写前必读 `references/solution-template.md`,严格按其模板与行文规范执行。
- 文件位置:使用者指定了目录则写入指定目录;未指定则写入当前工作目录。文件名 `dify-<应用名>-搭建方案.md`。
- 文档要求:流程图用文字图(不用 mermaid);每个节点的每个配置项给出具体取值,不写"设置一个合适的值";知识库、工具、模型等外部依赖在「前置准备」中列明,由使用者自行准备。
- 方案文档正文须正式、中性、面向任何读者,不出现对话式表述(如"根据你的要求""我已经")。

### 第 3 步:按需生成 DSL 文件

方案文档末尾的「导入说明」固定声明可生成 DSL 文件。仅当对方明确要求时才生成:

- 生成前必读 `references/dsl-structure.md`;节点字段细节读 `references/node-schemas.md`;涉及代码节点必读 `references/code-node.md`。
- 无外部依赖(仅使用开始、代码、模板、HTTP 请求、LLM 等通用节点):直接生成完整可导入文件。
- 有外部依赖:知识库 `dataset_ids`、工具 `plugin_unique_identifier`、模型 `provider` 路径均与具体 Dify 租户相关,不得虚构——用清晰的占位值并在说明中列出「导入后需手动补配」清单。对方提供了导出的 DSL 时,优先从中复制这些字段的真实值。
- `version` 固定为字符串 `"0.6.0"`,`kind: app`。文件名 `dify-<应用名>.yml`,与方案文档同目录。

### 第 4 步:校验与交付

- DSL 文件必须通过校验后才可交付:`python3 scripts/validate_dsl.py <文件路径>`。所有 ERROR 清零后才能交付;WARN 逐条判断,能修则修。
- 交付时说明:文件位置、校验结果、导入步骤(Dify 工作室 → 创建应用 → 导入 DSL)、需手动补配项清单(如有)。

## 硬规则速查

生成或修改 DSL 时最高频的错误,细节见 references:

1. 变量引用写 `{{#节点ID.变量名#}}`,系统变量写 `{{#sys.query#}}`——不是 `{{变量名}}`。
2. 代码节点是 Dify 沙箱硬校验:Python 必须 `def main(...) -> dict`,形参名与输入变量名一致,返回 dict 的键与 `outputs` 声明完全一致。
3. `workflow` 模式的终端节点用 `end`;`advanced-chat` 模式用 `answer`,两者不可混用。
4. 每条边的 `sourceType`/`targetType` 必须与两端节点的 `data.type` 一致。
5. `version`、节点 `id`、分支 `sourceHandle` 一律写成字符串。
6. 知识检索结果接入 LLM:配置 `context.variable_selector` 指向知识检索节点,提示词中以 `{{#context#}}` 引用。
7. 界面名称与 DSL 类型不同名:界面「输出」对应 DSL `end`,界面「变量赋值」对应 DSL `assigner`。以 `references/node-schemas.md` 的对照表为准。

## Reference 加载地图

按需读取,不要一次全部加载:

| 文件 | 何时读 |
|---|---|
| `references/solution-template.md` | 产出方案文档前(必读) |
| `references/node-schemas.md` | 配置任何节点前;文首有目录,只读所需小节 |
| `references/code-node.md` | 方案包含代码节点时(必读) |
| `references/dsl-structure.md` | 生成或修改 DSL 文件前(必读) |

## 运行环境

- 校验脚本依赖 PyYAML。缺库时 `pip install pyyaml`;uv 环境用 `uv run --with pyyaml python3 scripts/validate_dsl.py <文件>`。
