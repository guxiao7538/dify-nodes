# 节点配置参考

本文按 DSL 类型逐个说明节点的用途、核心配置(DSL `data:` 载荷)、输出变量与易错点。节点外层 wrapper 与图结构见 `dsl-structure.md`。

- 只读当前方案涉及的小节。
- 配置片段展示的是 `data:` 内的核心字段,实际导出的节点还会有 `title`、`selected`、`desc` 等字段。
- 标注「以导出为准」的字段结构随 Dify 版本变化较快,生成 DSL 时若对方能提供目标实例导出的节点,优先照抄真实值。
- 本文使用 DSL 字段名,与界面措辞(如「查询变量」「Top K」)按语义对应;方案文档面向画布操作者,描述配置项应使用界面措辞。

## 界面名称与 DSL 类型对照

官方界面名称与 DSL `data.type` 存在差异,引用时以 DSL 类型为准:

| DSL `data.type` | 界面名称 | 分类 |
|---|---|---|
| `start` | 开始(用户输入 / 触发器) | 输入 |
| `trigger-schedule` | 定时触发器 | 触发(仅 workflow) |
| `trigger-webhook` | Webhook 触发器 | 触发(仅 workflow) |
| `trigger-plugin` | 插件触发器 | 触发(仅 workflow) |
| `llm` | LLM | 推理 |
| `knowledge-retrieval` | 知识检索 | RAG |
| `question-classifier` | 问题分类器 | 推理 |
| `parameter-extractor` | 参数提取器 | 推理 |
| `agent` / `agent-v2` | Agent | 推理 |
| `if-else` | 条件分支 | 逻辑 |
| `iteration` / `iteration-start` | 迭代 | 逻辑 |
| `loop` / `loop-start` / `loop-end` | 循环 / 退出循环 | 逻辑 |
| `variable-aggregator` | 变量聚合器 | 逻辑 |
| `assigner` / `variable-assigner` | 变量赋值 | 逻辑 |
| `list-operator` | 列表操作 | 逻辑 |
| `code` | 代码执行 | 处理 |
| `template-transform` | 模板转换 | 处理 |
| `http-request` | HTTP 请求 | 外部 |
| `tool` | 工具 | 外部 |
| `document-extractor` | 文档提取器 | 处理 |
| `end` | 输出(旧称「结束」) | 终端 |
| `answer` | 直接回复 | 终端 |
| `human-input` | 人工确认 / 人工介入 | 终端 |
| `knowledge-index` | 知识库写入 | 版本敏感 |
| `datasource` / `datasource-empty` | 数据源 | 版本敏感 |
| (wrapper `custom-note`) | 画布注释 | 辅助 |

---

## start

定义工作流的输入。`workflow` 模式在此声明输入字段;`advanced-chat` 模式下通常留空,用户消息走 `{{#sys.query#}}`,文件走 `{{#sys.files#}}`。

```yaml
variables:
  - label: "简历文件"
    variable: resume
    type: file              # text-input | paragraph | select | number | url | file | file-list | json | checkbox
    required: true
    max_length: 0           # 文本类字段可限制长度
    options: []             # 仅 select 需要
```

界面能力补充:短文本上限 256 字符;「隐藏并预填」与「必填」互斥,预填值经 URL 参数传入,不适合敏感内容。

**系统变量**(任何节点可引用):`{{#sys.query#}}`(用户消息,advanced-chat)、`{{#sys.files#}}`(上传文件)、`{{#sys.timestamp#}}`(运行开始时间)等。

## trigger-schedule(定时触发器)

仅 `workflow` 模式。每个工作流最多一个。

```yaml
mode: visual              # visual | cron
frequency: daily          # hourly | daily | weekly | monthly
timezone: Asia/Shanghai
visual_config:
  time: "09:00 AM"
cron_expression: ""       # mode: cron 时填标准 5 段 cron
```

cron 支持标准 5 段表达式及 `L`、`?`、`@daily` 等扩展;「日」与「星期」同时指定时按 OR 生效。官方导出会将调度配置重置,生产使用建议从导出复制。

**输出**:无业务输出,仅更新 `sys.timestamp`。

## trigger-webhook(Webhook 触发器)

仅 `workflow` 模式,通过 HTTP 请求自动启动工作流。

```yaml
method: POST
content_type: application/json
headers: []
params: []
body: []                  # 定义从请求中提取的字段
async_mode: true
status_code: 200
response_body: ""
variables: []             # 提取结果以变量形式供下游引用
```

`webhook_url`、`webhook_debug_url` 在官方导出中会被清空,导入后由工作区重新生成,自建 DSL 留空即可。

## trigger-plugin(插件触发器)

仅 `workflow` 模式,由插件事件驱动。结构(`provider_id`、`event_name`、`event_parameters`、`output_schema` 等)高度依赖具体插件,`subscription_id` 在导出中被清空。**不要凭名称手写此节点**,一律从目标实例导出复制。

## llm

调用语言模型生成内容。

```yaml
model:
  provider: langgenius/tongyi/tongyi   # 与目标工作区导出的 provider 写法一致
  name: qwen-plus
  mode: chat
  completion_params:
    temperature: 0.3
prompt_template:
  - id: <uuid>               # 消息标识,自造且不重复即可
    role: system
    text: "你是资料整理助手。"
  - id: <uuid>
    role: user
    text: "总结以下内容:{{#start.input_text#}}"
context:
  enabled: false
  variable_selector: []    # 接知识检索时: ["<知识检索节点id>", "result"]
memory:                    # 仅 advanced-chat
  window:
    enabled: false           # 是否携带多轮对话历史
    size: 50                 # 携带的轮数上限,仅 enabled 为 true 时生效
vision:
  enabled: false
```

要点:

- 提示词中单条消息可切 Jinja2 模式,DSL 中该条消息带 `edition_type: jinja2`。
- 知识检索结果经 `context` 注入后,提示词里用 `{{#context#}}` 引用。
- 结构化输出(JSON Schema 约束)在界面配置,DSL 字段名随版本变化,建议从导出核对;依赖提示词约束 JSON 的方式对非原生 JSON 模型不可靠。
- 视觉模式下图片变量默认取 `{{#start.files#}}`(或用户输入文件字段)。

**输出**:`text`(string,回答正文);开启推理分离时另有 `reasoning_content`(string);启用结构化输出时为声明的结构字段。

## knowledge-retrieval(知识检索)

从 Dify 知识库检索相关分段,是 RAG 流程的核心节点。

```yaml
dataset_ids:
  - "<知识库 ID,租户相关>"
query_variable_selector: ["start", "query"]   # advanced-chat 下为 ["sys", "query"]
retrieval_mode: multiple          # single | multiple
multiple_retrieval_config:
  top_k: 4
  score_threshold: 0.5            # 预填值,仅 score_threshold_enabled 开启时生效
  reranking_enable: false         # 开启后需配置 reranking_model
  reranking_model:
    provider: ""
    model: ""
score_threshold_enabled: false
metadata_filtering_mode: disabled # disabled | basic | advanced
```

要点:

- `dataset_ids` 是目标租户的知识库 ID,自建 DSL 用占位值并列入「导入后需手动补配」清单。
- 检索模式:多路检索(multiple)可跨多个知识库;开启重排序(rerank)需要工作区已配置 rerank 模型。
- 结果接入 LLM 走 `context.variable_selector`,不要用普通变量直接塞提示词。

**输出**:`result`(array[object]),每个元素为一个分段对象,常用字段:`content`(分段正文)、`title`、`metadata`、`dataset_name`、`dataset_id`。

## question-classifier(问题分类器)

用 LLM 将输入语义分类并路由到不同分支。

```yaml
model:
  provider: langgenius/tongyi/tongyi
  name: qwen-plus
  mode: chat
  completion_params:
    temperature: 0
query_variable_selector: ["sys", "query"]
classes:
  - id: "1"
    name: "咨询产品信息"
  - id: "2"
    name: "投诉与售后"
instruction: "将用户问题分到最合适的类别。"
```

要点:

- `name`(类别描述)是给模型看的分类依据;界面上的「标题」另存于分类定义,输出为 `class_label`。分类准确性主要取决于 `name` 的措辞。
- 分支边的 `sourceHandle` 等于类别 `id`(如 `"1"`、`"2"`)。

**输出**:`class_name`(string,命中的类别描述)、`class_label`(string,命中的类别标题)。

## parameter-extractor(参数提取器)

用 LLM 从文本提取结构化参数,比让 LLM 自由输出再解析更稳。

```yaml
query: ["start", "input_text"]
parameters:
  - name: city
    type: string            # string | number | bool | array[...] | object
    description: "用户要查询的城市,无法判断时留空"
    required: false
reasoning_mode: prompt      # function_call | prompt
instruction: "从输入中提取目标城市。"
```

要点:

- 提取失败不会让节点报错,而是输出失败标志——下游务必用 `__is_success` 做条件分支。
- 参数定义支持「从工具导入」(按所接工具的参数 schema 生成)。

**输出**:每个参数名一个输出变量;内置 `__is_success`(string,`"1"` 成功 / `"0"` 失败)、`__reason`(string,失败原因)。

## agent

让模型按策略(函数调用 / ReAct)自主多轮调用工具。`agent-v2` 为新一代实现,输出与配置以导出为准。

```yaml
agent_strategy_name: function_calling
agent_strategy_provider_name: langgenius/agent/agent
agent_strategy_label: FunctionCalling
agent_parameters:
  model:
    type: constant
    value:
      provider: langgenius/tongyi/tongyi
      name: qwen-plus
      mode: chat
      completion_params:
        temperature: 0.3
  query:
    type: constant
    value: "{{#sys.query#}}"
  instruction:
    type: constant
    value: "需要查资料时调用搜索工具。"
  tools:
    type: constant
    value: []
max_iteration: 5
output_schema: null
```

要点:

- 工具参数分自动生成与手动固定两种;任务上下文中的变量以文本注入,超过约 2000 字符会被截断,长内容改为传文件;返回文件单件上限约 50MB。
- 依赖的模型与工具都会进入 `dependencies`。

**输出**:经典策略下为最终答案(`output` 或 `text`)、过程数据(`process_data`,JSON 轨迹)、执行计数等;字段随策略与版本变化,以导出为准。

## if-else(条件分支)

按条件路由流程,支持多分支(ELIF / ELSE)。

```yaml
cases:
  - id: "true"
    case_id: "true"
    logical_operator: and     # and | or
    conditions:
      - id: <uuid>
        variable_selector: ["start", "input_text"]
        comparison_operator: contains
        value: "合同"
        varType: string
  - id: "false"               # 多分支时此处为 uuid
    case_id: "false"
    logical_operator: and
    conditions: []
```

常用比较操作符:`contains`、`not contains`、`is`、`is not`、`empty`、`not empty`、`start with`、`end with`、`is`、`in`、`not in`,数值型支持 `=`、`≠`、`>`、`<`、`≥`、`≤`。

要点:分支边的 `sourceHandle` 必须等于对应 case 的 `id`;`varType` 要与被比较变量的实际类型一致,否则比较行为不符合预期。

**输出**:无输出变量,只产生分支路径。

## iteration(迭代)

对数组逐项执行同一段子流程,支持顺序或并行(并行上限 10)。

```yaml
iterator_selector: ["start", "file_list"]   # 必须是数组类型
output_selector: ["<子流程末节点id>", "output"]
output_type: array[string]
is_parallel: false
parallel_nums: 10
error_handle_mode: terminated   # terminated | continue-on-error | remove-abnormal-output
start_node_id: "<子流程起始节点id>"
```

要点:

- 输入必须是数组;迭代体内部引用当前元素 `{{#iteration.items#}}` 与序号 `{{#iteration.index#}}`(从 0 开始)。
- 子流程节点带 `isInIteration: true` 与 `iteration_id`,并由 wrapper 为 `custom-iteration-start` 的 `iteration-start` 辅助节点进入;相关边也带 `isInIteration` 标记,手写 DSL 时参照导出结构。
- 错误处理三选一:遇错终止 / 出错继续(失败项输出 null)/ 移除失败项。
- 迭代输出是数组,常接模板转换或代码节点 join 成文本。

**输出**:声明的数组(`output_type`);迭代体内可引用 `items`、`index`。

## loop(循环)

依据前一轮结果决定是否继续的渐进循环(与迭代的区别:迭代遍历既有数组,循环的每轮输入依赖上一轮)。

```yaml
loop_count: 5                  # 最大次数
break_conditions:
  - id: <uuid>
    variable_selector: ["<循环体内节点id>", "done"]
    comparison_operator: is
    value: "true"
    varType: boolean
start_node_id: "<循环体起始节点id>"
loop_variables: []             # 循环变量:跨轮次持久累积,结构以导出为准
```

要点:

- 循环体由 `loop-start` 进入,中途退出用 `loop-end`(退出循环节点),子节点与边带 `isInLoop`、`loop_id` 标记。
- 修改循环变量须用变量赋值节点;终止条件与最大次数同时起效,先到者退出。
- 嵌套分支或多出口的循环体结构复杂,**从导出复制**比手写可靠。

**输出**:循环变量(声明的类型)。

## variable-aggregator(变量聚合器)

把多个互斥分支(同一时刻只有一个发生)的同类型输出汇成一个变量,常用于分支汇合后统一供 `end` / `answer` 引用。

```yaml
output_type: string            # 被聚合变量的共同类型
variables:
  - ["<分支A节点id>", "text"]
  - ["<分支B节点id>", "text"]
```

要点:被聚合变量必须同类型(string/number/object/boolean/array/file);「聚合分组」可在同一节点内开多组,组结构以导出为准。

**输出**:`output`(类型 = 被聚合变量类型)。

## assigner(变量赋值,界面:变量赋值)

写入**会话变量**(advanced-chat 的跨轮次持久变量,需先在应用的会话变量面板定义)。旧导出中类型名为 `variable-assigner`,两者等价,修改既有文件时保持原样。

```yaml
items:
  - variable_selector: ["conversation", "memory_summary"]
    input_type: variable
    value_selector: ["<llm节点id>", "text"]
    operation: over-write
```

`operation` 常见值:`over-write`(覆写)、`clear`(清除)、`set`(设置);数字变量支持四则类操作,数组支持追加、扩展、移除首尾。精确字符串以目标版本导出为准。

**输出**:无。

## list-operator(列表操作)

对数组筛选、排序、截取、取元素。输入限 `array[string]`、`array[number]`、`array[boolean]`、`array[file]`。

```yaml
var_type: array[file]
variable: ["sys", "files"]
filter_by:
  enabled: true
  conditions:
    - comparison_operator: in
      value: ["image"]         # 文件可按类型/MIME/扩展名/大小/名称/传输方式过滤
order_by:
  enabled: false
  key: asc                     # asc | desc
  value: ""
extract_by:
  enabled: true
  serial: first                # 取第 N 项 / first / last 等,结构以导出为准
```

**输出**:`result`(过滤排序后的数组)、`first_record`、`last_record`。在多文件场景常用它把文件列表收敛成单个文件再交给下游。

## code(代码执行)

在沙箱中运行 Python 或 JavaScript。**函数签名、返回值与沙箱限制是 Dify 硬校验,规范与模板见 `code-node.md`**,此处仅列 DSL 结构:

```yaml
code_language: python3         # python3 | javascript
code: |
  def main(text: str) -> dict:
      return {"result": text.strip()}
variables:
  - value_selector: ["start", "input_text"]
    variable: text             # 形参名,必须与 main 的参数名一致
outputs:
  result:
    type: string               # string | number | object | array[string] | array[number] | array[object]
```

**输出**:`outputs` 中声明的变量。

## template-transform(模板转换)

用 Jinja2 拼装文本,迭代结果的汇总输出最常用。

```yaml
variables:
  - variable: items
    value_selector: ["<迭代节点id>", "output"]
template: |
  {% for item in items %}
  - {{ item }}
  {% endfor %}
```

**输出**:`output`(string,上限 400,000 字符)。模板支持点号取属性、下标、过滤器、循环与条件。

## http-request(HTTP 请求)

调用外部 API。

```yaml
method: post                 # GET | HEAD | POST | PUT | PATCH | DELETE
url: "https://api.example.com/v1/parse"
headers: "Content-Type: application/json"
params: ""
body:
  type: json                 # json | form-data | x-www-form-urlencoded | raw-text | binary | none
  data:
    - id: body-file-id
      key: text
      type: string
      value: "{{#start.input_text#}}"
authorization:
  type: no-auth              # no-auth | api-key(basic / bearer / custom)
timeout:
  connect: 10
  read: 60
  write: 10
retry_config:
  retry_enabled: false       # 最多 10 次,间隔上限 5000ms
ssl_verify: true
```

要点:响应为二进制时内容进入 `files`;可配置错误重试与错误分支(默认值 / 错误路由 / 替代模型),对外部调用节点建议显式配置。

**输出**:`body`(string)、`status_code`(number)、`headers`(object)、`files`(array[file])。

## tool(工具)

调用已安装的工具插件、API 工具、工作流工具或 MCP 工具。

```yaml
provider_id: langgenius/firecrawl/firecrawl
provider_name: langgenius/firecrawl/firecrawl
provider_type: builtin        # builtin | api | workflow | mcp
plugin_id: langgenius/firecrawl
plugin_unique_identifier: "<版本哈希,租户相关>"
tool_name: scrape
tool_label: "单页面抓取"
tool_description: "抓取网页内容"
tool_node_version: "2"
tool_configurations:
  formats:
    type: constant
    value: markdown
tool_parameters:
  url:
    type: mixed               # constant | mixed | variable
    value: "https://example.com/?q={{#sys.query#}}"
```

要点:

- 五个身份字段缺一不可:`provider_id`、`provider_name`、`provider_type`、`tool_name`、`tool_parameters`。`plugin_id`、`plugin_unique_identifier`、`tool_node_version`、`paramSchemas`、`params` 在较新导出中常见但非必需,**从导出复制并保留**,不得凭名称虚构。
- 每个工具的参数 schema 不同,手写新工具节点前先拿到该工具在目标工作区的真实形态(最小导出)。

**输出**:取决于具体工具,常见 `text`、`files`、`json`、`images` 等不确定时从工具详情或导出确认。

## document-extractor(文档提取器)

把文档文件转成文本。

```yaml
variable_selector: ["sys", "files"]
is_array_file: false          # 输入是文件列表时为 true
```

支持格式:txt、md、html、docx/doc、odt、pdf(文本型)、xls/xlsx/csv(转 Markdown 表格)、ppt/pptx、eml、msg、epub、vtt、json、yaml、properties。扫描版 PDF 无法提取文字。

**输出**:`text`——单文件为 string,文件列表为 array[string]。

## end(输出节点)

`workflow` 模式的终端节点,声明最终输出。界面新名称为「输出」,DSL 类型仍为 `end`。

```yaml
outputs:
  - variable: summary         # 变量名 = API 返回 outputs 的键名
    value_selector: ["<llm节点id>", "text"]
```

要点:输出变量名全局唯一(多个 end 节点间也不可重复,重名以后者覆盖);将工作流发布为工具时,变量名不能用保留字 `text`、`files`、`json`。

## answer(直接回复)

`advanced-chat` 模式的终端节点,向用户流式回复。

```yaml
answer: "检索结果如下:{{#knowledge_retrieval.result#}}"
variables: []                 # 需要流式输出的中间变量可列在此处
```

要点:多分支流程每个分支可各接一个 answer;answer 内可直接引用变量插值,支持图文混合输出。

## human-input(人工确认)

流程暂停等待人工填写表单后继续。

```yaml
variables:
  - label: "补充说明"
    variable: remark
    type: paragraph           # 表单支持:段落(选填)、下拉选项、单文件、文件列表(必填)
    required: false
    options: []
```

要点:提交渠道为 Web 应用或邮件;文件上限图片 10MB、文档 15MB、音频 50MB、视频 100MB、列表最多 10 项;超时默认 3 天,超时分支未接线则工作流直接结束。版本敏感,**生产 DSL 从导出复制**。

**输出**:表单字段同名变量;内置 `__rendered_content`(渲染后的表单内容)、`__action_id`、`__action_value`。

## knowledge-index(知识库写入)

把分段文本写入指定知识库。版本敏感,结构随部署形态变化,从导出复制;核心字段:`dataset_id`、`index_chunk_variable_selector`、`keyword_number`、`retrieval_model`。

## datasource(数据源)

从 Notion 等数据源拉取内容,插件驱动。`provider_id`、`datasource_name` 等字段高度插件化,**从导出复制**。

## custom-note(画布注释)

非执行节点,wrapper `type: custom-note`,`data.type` 可为空字符串,承载 `text`、`theme`、`width`、`height` 等排版字段。用于在画布上给人留说明,校验时不得当作可执行节点处理。
