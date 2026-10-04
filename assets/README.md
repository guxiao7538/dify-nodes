# Assets Specification / 资源文件规范

本目录用于存放 `dify-nodes` 的视觉资产（主视觉横幅、动图与演示截图）。当前预留占位规范如下：

## 1. 顶部主视觉横幅 (`hero-banner.png`)
- **文件路径**: `assets/hero-banner.png`
- **建议比例**: 1200 x 400 ~ 1200 x 480 (3:1 宽屏)
- **推荐内容**: 
  - 现代深色或科技蓝极客风格，融合 Dify 节点画布、工作流连接线、代码块高亮与自动化校验图标。
  - 主文案：`Dify Nodes • AI-Powered Visual Flow Architect`
- **生成建议 (Midjourney/DALL-E)**:
  > *Minimalist modern tech banner, AI workflow nodes connecting with glowing neon cyan and electric blue lines, schematic node canvas diagram, dark navy blue background, isometric futuristic interface, clean typography, 8k resolution, vector art style.*

---

## 2. 动图演练与效果演示 (`demo.gif`)
- **文件路径**: `assets/demo.gif`
- **建议比例**: 1280 x 720 (16:9)
- **推荐内容**: 
  - 录制终端中 Agent（如 Claude Code / ZCode）从自然语言需求对话，到自动生成逐节点规范文档、导出 `workflow.yml`，并触发 `scripts/validate_dsl.py` 静态校验全绿通过的流畅全过程。
- **制作工具建议**: [Terminalizer](https://terminalizer.com/) 或 [Asciinema](https://asciinema.org/) + [Gifski](https://gif.ski/)。
