# DSL 结构参考

Dify 把工作流应用导出为 DSL 文件(YAML)。本文说明自建或修改 DSL 时的结构规则。节点内部配置见 `node-schemas.md`,代码内容见 `code-node.md`。

## 顶层结构

```yaml
app:
  name: "应用名"
  description: "应用用途一句话"
  icon: "🤖"
  icon_type: emoji
  icon_background: "#FFEAD5"
  mode: workflow            # workflow | advanced-chat | chat | completion | agent-chat
  use_icon_as_answer_icon: false
kind: app
version: "0.6.0"            # 必须是字符串
dependencies: []            # 有插件依赖时列出,见下文
workflow:
  conversation_variables: []
  environment_variables: []
  features:
    file_upload:
      enabled: false
      image:
        enabled: false
        number_limits: 3
        transfer_methods: [local_file, remote_url]
      allowed_file_extensions: []
      allowed_file_types: []
      allowed_file_upload_methods: [local_file, remote_url]
      number_limits: 3
    opening_statement: ""
    retriever_resource:
      enabled: true
    sensitive_word_avoidance:
      enabled: false
    speech_to_text:
      enabled: false
    suggested_questions: []
    suggested_questions_after_answer:
      enabled: false
    text_to_speech:
      enabled: false
      language: ""
      voice: ""
  graph:
    nodes: []
    edges: []
    viewport:
      x: 0
      y: 0
      zoom: 0.8
```

## 应用模式

| mode | 用途 | 输入来源 | 终端节点 |
|---|---|---|---|
| `workflow` | 一次性自动执行(批量、定时、API) | start 变量 / 触发器 | `end` |
| `advanced-chat` | Chatflow 多轮对话 | `sys.query`、`sys.files`、会话变量 | `answer` |
| `chat` / `completion` / `agent-chat` | 旧式应用 | 顶层 `model_config` | — |

新应用只用 `workflow` 或 `advanced-chat`。旧式模式没有 `workflow.graph`,审查旧导出时不要把图结构规则套上去。

## 节点 wrapper

每个节点 = ReactFlow 风格的外壳 + `data` 载荷:

```yaml
- id: "1740000000001"       # 字符串,全局唯一,不复用
  type: custom
  position: { x: 300, y: 280 }
  positionAbsolute: { x: 300, y: 280 }
  width: 243
  height: 90
  selected: false
  sourcePosition: right
  targetPosition: left
  data:
    title: "内容清洗"
    type: code              # 真正的节点类型
    selected: false
```

- 外壳 `type` 一般为 `custom`;迭代/循环起点为 `custom-iteration-start` / `custom-loop-start`;注释为 `custom-note`。
- 节点 id 建议用纯数字字符串(如 `"1740000000001"`),与官方导出习惯一致;也可用语义字符串,保持唯一即可。

## 边

```yaml
- id: "1740000000001-source-1740000000002-target"
  source: "1740000000001"
  sourceHandle: source
  target: "1740000000002"
  targetHandle: target
  type: custom
  zIndex: 0
  selected: false
  data:
    sourceType: code        # 必须与 source 节点的 data.type 一致
    targetType: end         # 必须与 target 节点的 data.type 一致
    isInIteration: false
    isInLoop: false
```

`sourceHandle` 约定:

| 场景 | sourceHandle |
|---|---|
| 直线连接 | `source` |
| if-else 分支 | 对应 case 的 `id`(`"true"` / `"false"` / uuid) |
| 问题分类器分支 | 对应类别的 `id`(`"1"`、`"2"`…) |
| 迭代/循环内部 | `source`,且边带 `isInIteration` / `isInLoop` 与父节点标记 |

## 变量引用

两种形态,不要混用:

```text
选择器(结构化字段,数组形态):
  value_selector: ["节点id", "变量名"]
  ["sys", "query"]            系统变量
  ["conversation", "Memory"]  会话变量
  ["env", "API_KEY"]          环境变量

插值(字符串模板内):
  {{#节点id.变量名#}}
  {{#sys.query#}}
  {{#conversation.Memory#}}
  {{#env.API_KEY#}}
  {{#节点id.数组变量[0].字段#}}   数组元素取值
  {{#context#}}               LLM 节点提示词中引用 context 注入的检索结果
```

`value_selector` 必须是两元素数组;`["sys.query"]` 这类点号合并写法在旧导出中存在,新文件不要用。

## 工作流变量

会话变量(advanced-chat 跨轮次状态):

```yaml
conversation_variables:
  - id: <uuid>
    name: memory_summary
    value: ""
    value_type: string       # string | number | boolean | object | array[...] | file
    selector: [conversation, memory_summary]
    description: ""
```

环境变量(只读常量,适合放非密钥配置;密钥用 Dify 的环境变量功能存,不进 DSL 明文):

```yaml
environment_variables:
  - id: <uuid>
    name: BASE_URL
    value: "https://api.example.com"
    value_type: string
    selector: [env, BASE_URL]
    description: ""
```

## dependencies

凡节点依赖插件(LlamaProvider、工具、Agent 策略、数据源),都在顶层 `dependencies` 列出。三种类型:

```yaml
- current_identifier: null
  type: marketplace
  value:
    marketplace_plugin_unique_identifier: "langgenius/tongyi:0.1.36@<哈希>"
- current_identifier: null
  type: package
  value:
    plugin_unique_identifier: "author/plugin:0.0.1@<哈希>"
- current_identifier: null
  type: github
  value:
    repo: author/plugin-repo
    version: 0.0.1
    package: plugin-package-name
    github_plugin_unique_identifier: "author/plugin:0.0.1@<哈希>"
```

依赖来源:LLM / 问题分类器 / 参数提取器的 `model.provider`、工具节点的 `provider_id`、知识检索的 rerank / embedding 模型、Agent 节点的策略与工具。插件标识含版本哈希,**只能从目标工作区导出或插件市场复制,不得手造**;纯内置节点(start/code/template/http 等)与无插件的流程 `dependencies: []` 即可。用到模型/工具插件但拿不到版本哈希时,同样留空 `dependencies: []`,把插件列进交付说明的「导入后需手动补配」清单——Dify 导入时会按节点中的 provider 提示安装依赖。

## DSL 节点类型全集

`data.type` 合法值(超出此集合的写法无法通过校验):

```text
start  end  answer  llm  knowledge-retrieval  question-classifier  if-else
code  template-transform  http-request  variable-assigner  variable-aggregator
tool  parameter-extractor  iteration  iteration-start  assigner  agent  agent-v2
loop  loop-start  loop-end  human-input  datasource  datasource-empty
knowledge-index  trigger-schedule  trigger-webhook  trigger-plugin
```

辅助类型:`iteration-start`、`loop-start`、`loop-end`、`datasource-empty` 由官方导出生成,内部结构以导出为准;`start-placeholder` 仅出现在占位场景。

## 导入敏感字段(与租户环境相关)

以下字段换个工作区就失效,**自建 DSL 用占位值并列入「导入后需手动补配」清单,绝不虚构**:

| 字段 | 位置 | 处理 |
|---|---|---|
| `dataset_ids` | knowledge-retrieval、knowledge-index | 占位 `"replace-me"`,导入后重选知识库 |
| `provider` | 各模型配置 | 与目标工作区已配供应商写法一致,无法确认时占位 |
| `plugin_unique_identifier` | dependencies、tool 节点 | 从导出/市场复制 |
| `credential_id` | tool / agent 工具 | 导出时会剥离,自建不写 |
| `webhook_url` / `subscription_id` | 触发器节点 | 留空,导入后自动生成 |
| `dataset_ids` 加密 | 知识检索 | 部分部署下导出加密、导入解密,照抄导出即可 |

工具节点导出中的 `paramSchemas`、`params`、`is_team_authorization` 冗长但无害,复制导出时原样保留。

## 版本兼容

- 新文件一律 `version: "0.6.0"`(字符串)。导入时:Dify 对旧版本容忍(可能带警告升级),对超出自身支持的新版本会拒绝或要求确认。
- 旧公开样本(0.1–0.5)可用于理解历史写法,不作为新文件的依据。
