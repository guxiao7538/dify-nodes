# 代码节点专项

Dify 的代码节点在受限沙箱中运行,与本地手写脚本的关键差异在于:**入口函数签名由 Dify 约定,返回值由 Dify 校验,可用库受沙箱白名单限制**。本文是编写代码节点内容的完整规范。

## 入口函数约定

Dify 按输入变量名把值作为**位置参数**传入入口函数,要求入口函数返回一个 dict,dict 的键与节点 `outputs` 中声明的输出变量一一对应。运行前 Dify 会校验入口函数存在与返回结构,不符直接报错。

### Python

```python
def main(输入变量名1: str, 输入变量名2: float) -> dict:
    ...
    return {"输出变量名": 值}
```

- 函数名必须是 `main`,必须返回 `dict`。
- 形参名必须与节点输入变量的 `variable` 名**逐字一致**;形参数量与输入变量一致(不用的输入也建议保留形参)。
- 返回 dict 的键必须与 `outputs` 声明的键**完全一致**:多返回未声明的键、少返回声明的键都会校验失败。
- 建议给形参与返回值加类型注解,便于与 `outputs` 类型声明对照。

### JavaScript

```javascript
function main(输入变量名1, 输入变量名2) {
  return { 输出变量名: 值 }
}
```

- 函数名必须是 `main`,返回 object,键与 `outputs` 一致,规则同 Python。

## 类型映射

`outputs` 声明类型与运行时类型必须相符,常用对应关系:

| outputs 类型 | Python 返回 | JavaScript 返回 |
|---|---|---|
| `string` | `str` | `String` |
| `number` | `int` / `float` | `Number` |
| `object` | `dict` | `Object` |
| `array[string]` | `list[str]` | `Array<String>` |
| `array[number]` | `list[int/float]` | `Array<Number>` |
| `array[object]` | `list[dict]` | `Array<Object>` |

- 数字统一按 `number` 处理;返回整数时下游比较、拼接行为与浮点一致,但 JSON 序列化后整型无小数点。
- 需要 JSON 字符串时自己 `json.dumps()` 成 `string` 输出,不要指望 `object` 类型自动转字符串。

## 沙箱限制

| 项 | 限制 |
|---|---|
| 超时 | 默认 5 秒(worker_timeout),自托管实例可调 |
| 输出字符串 | 单个字符串 ≤ 400,000 字符 |
| 数值 | 整数 ≤ 19 位,小数 ≤ 20 位 |
| 嵌套深度 | 对象/数组嵌套 ≤ 5 层 |
| 网络 | 禁止出站请求(Cloud 版;自托管默认也关,`enable_network` 打开属例外) |
| 文件系统 | 禁止读写文件 |
| 子进程/系统命令 | 禁止 |

超限的表现是节点直接报错,不会截断——输出体积必须自行裁剪。

## 可用的库

**Python**(标准库全量可用:`json`、`re`、`math`、`datetime`、`random`、`hashlib`、`base64`、`urllib.parse` 等),镜像预装第三方包:`httpx`、`requests`、`jinja2`、`PySocks`。预装版本随 Dify 镜像变化,`import` 未预装的第三方包(如 pandas、numpy)会直接失败——**只依赖标准库,除非确认目标环境有该包**。

**JavaScript**:Node.js v20 运行时,仅标准内置对象与全局方法(`JSON`、`Math`、`Date`、`Array`、`Object` 等)。**没有 npm 包**,不能 `require`/`import` 任何第三方库。

## 代码模板

### Python(文本清洗)

```python
import json
import re

def main(raw_text: str, max_len: int) -> dict:
    text = re.sub(r"\s+", " ", (raw_text or "").strip())
    if len(text) > max_len:
        text = text[:max_len]
    return {"clean_text": text}
```

### Python(配合迭代节点)

迭代体内引用当前元素 `{{#iteration.items#}}` 与序号 `{{#iteration.index#}}`,典型写法:

```python
import json

def main(item: str, index: int) -> dict:
    data = json.loads(item)          # 元素是 JSON 字符串时先解析
    return {"output": f"{index + 1}. {data.get('title', '')}"}
```

### JavaScript(JSON 归一化)

```javascript
function main(raw_text) {
  let parsed = {}
  try {
    parsed = JSON.parse(raw_text)
  } catch (e) {
    parsed = { error: String(e) }
  }
  return { normalized: JSON.stringify(parsed) }
}
```

## 常见坑

1. **返回键与 `outputs` 不一致**——最高频错误。改了代码忘改 `outputs`(或反之)都会校验失败;两者必须同步修改。
2. **形参名与输入变量名不一致**——Dify 按变量名传参,名字对不上就是缺参数报错。
3. **`import` 了环境没有的包**——沙箱只有预装包,联网安装不可用。
4. **试图 `requests.get()` 联网**——沙箱禁网,HTTP 调用应改用 HTTP 请求节点。
5. **输出超限**——超长字符串、深嵌套对象直接报错;先裁剪、先扁平化。
6. **类型声明不符**——声明 `number` 却返回字符串 `"3"`,下游比较与排序会异常。
7. **异常未处理**——main 内抛未捕获异常即节点失败;对可能失败的外部数据先做防御性解析,错误信息放进输出变量供下游分支使用。
8. **复杂逻辑硬塞代码节点**——代码节点适合清洗、格式化、轻量转换;需要重试、认证、多步处理时应拆成 HTTP 请求节点 / 工具节点 / 子流程。
