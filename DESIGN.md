# DESIGN.md — PPTAgent 架构决策日志

## 架构图 + 数据流

```
输入 JSON
  { topic, brief, audience }
          │
          ▼
  ┌──────────────┐
  │  prompt.py   │  单次 LLM 流式调用
  │              │  claude-sonnet-5 / claude-haiku-4-5
  └──────┬───────┘
         │ raw_text (LLM 原始输出)
         ▼
  ┌──────────────┐
  │  parser.py   │  ① 正则提取 JSON 块
  │              │  ② json.loads()
  │              │  ③ Pydantic 校验 PresentationData
  │              │  ④ 失败 → 重试一次（附错误提示）
  │              │  ⑤ 仍失败 → 硬兜底（fallback_parse）
  └──────┬───────┘
         │ PresentationData (design_dna + slides[25-30])
         ▼
  ┌──────────────┐
  │ renderer.py  │  python-pptx 绘制，7 种布局
  │              │  所有颜色来自 design_dna
  └──────┬───────┘
         │
         ▼
   output.pptx
```

**关键设计选择：单次 LLM 调用生成一切**（叙事结构 + 设计参数 + 所有幻灯片内容）。

## 模型选型

| 模式 | 模型 | 定价（intro 至 2026-08-31） | 选择原因 |
|------|------|---------------------------|---------|
| Beauty | `claude-sonnet-5` | $2/$10 /MTok | 最新 Sonnet 系列，内容质量、创意叙事最强，成本在 $10 硬限内 |
| Tradeoff | `claude-haiku-4-5` | $1/$5 /MTok | 速度快（约 2-5× Sonnet），成本约为 1/3，适合批量/调试 |

**比较过的替代方案：**

- `claude-opus-4-8`：质量更高，但 $5/$25 /MTok，一次调用含 25 张幻灯片 JSON 大约 $0.15–0.3，接近甚至超出 $10 预算的 20%，风险较大；且 Sonnet 5 的内容质量在 PPT 场景已足够。
- GPT-4o：未选用。项目工具链已在 Anthropic 生态，切换引入不必要复杂度。
- 多次 LLM 调用（先生成大纲再逐张生成）：被否定，见"踩坑"章节。

## 风格一致性怎么保的

核心机制：**DesignDNA（设计基因对象）**

```python
class DesignDNA(BaseModel):
    bg_dark: str   # 深色背景（封面/结尾/引用页）
    bg_light: str  # 浅色背景（正文页）
    accent: str    # 强调色（所有装饰元素、要点前缀、分割线）
    text_dark: str # 深背景上的文字色
    text_light: str# 浅背景上的文字色
    font: str      # 全局字体
```

每个布局渲染函数的唯一颜色来源是 `DesignDNA`，**没有任何硬编码颜色**。DesignDNA 由 LLM 根据主题气质一次性生成（科技感→冷色调，温情→暖色调），之后所有幻灯片共享这一对象。

**结构层面的一致性保证：**

- 封面和结尾（cover/closing）使用相同的 `bg_dark` 背景 + accent 上下条 + 装饰侧面板，形成首尾呼应。
- 所有 bullets 页固定在左侧有 accent 色竖条、顶部有 bg_dark 标题栏。
- section 转场页统一用 accent 色全背景，让观众在视觉上感受到章节切换。
- 所有文字大小遵循固定层级：标题 30-46pt，正文 18-22pt，小字 16-18pt。

## 多样性怎么保的

多样性靠两个层面：

**1. 内容多样性（LLM 驱动）**

Prompt 要求 LLM 自行决定：
- `design_dna` 的颜色（主题气质决定色调，每次输出不同）
- 幻灯片布局的组合（7 种布局，LLM 按内容类型自主选择）
- 叙事结构（不同主题有不同的展开逻辑）

例如"Python 入门"偏教程感，大量 bullets 布局；"年度复盘"偏叙事感，更多 quote 和 stat 布局；"Rust 提案"偏说服风，stat + two_col 对比较多。

**2. 视觉多样性（设计基因变化）**

不同主题生成不同的颜色方案，renderer.py 用 `_blend()` 派生辅助色（侧面板颜色），使每套 PPT 整体感觉不同，而不是同一模板填空。

## 成本与时延实测

（待运行 5 套 demo 后填写实测数据）

| # | 主题 | 模式 | slides | 输入 token | 输出 token | 成本($) | 时延(s) |
|---|------|------|--------|-----------|-----------|---------|---------|
| 1 | Python 入门 | beauty | — | — | — | — | — |
| 1 | Python 入门 | tradeoff | — | — | — | — | — |
| 2 | 年度复盘 | beauty | — | — | — | — | — |
| 2 | 年度复盘 | tradeoff | — | — | — | — | — |
| 3 | 咖啡豆选购 | beauty | — | — | — | — | — |
| 3 | 咖啡豆选购 | tradeoff | — | — | — | — | — |
| 4 | Rust 提案 | beauty | — | — | — | — | — |
| 4 | Rust 提案 | tradeoff | — | — | — | — | — |
| 5 | 京都两日 | beauty | — | — | — | — | — |
| 5 | 京都两日 | tradeoff | — | — | — | — | — |

## 踩坑和取舍

### 取舍 1：单次调用 vs. 多次调用

**试过**：先用 LLM 生成大纲（1 次调用），再为每张幻灯片单独生成内容（25-30 次调用）。

**否定原因**：
- 成本大幅上升（25 次调用的 overhead token 是单次的 10-15 倍）
- 叙事连贯性更差——每次调用上下文有限，幻灯片之间容易重复或逻辑断裂
- 速度反而更慢（30 次串行调用 vs. 1 次并行流式）
- 单次调用让 LLM "全局视角"设计叙事，质量更优

**结论**：单次大调用（max_tokens=16000）是更优的架构。

### 取舍 2：python-pptx vs. Puppeteer/HTML 导出

**考虑过**：用 LLM 生成 HTML/CSS，Puppeteer 截图转 PDF，再封装成 pptx。

**否定原因**：
- 引入 Node.js 依赖，跨平台部署复杂
- PDF→PPTX 不是真正可编辑的 PowerPoint 文件
- 题目要求"标准 .pptx（PowerPoint/Keynote 能正常打开）"

**结论**：python-pptx 是最直接的选择，生成的文件完全可编辑。

### 踩坑 1：LLM 输出 markdown 代码块

LLM 有时会在 JSON 外包上 ` ```json ``` `，导致 `json.loads()` 直接失败。

**解决**：`parser.py` 的 `_extract_json()` 先检测 markdown 代码块，再做平衡括号扫描，两个策略互为兜底。

### 踩坑 2：python-pptx 透明度支持有限

计划在装饰矩形上使用半透明遮罩，但 python-pptx 的 solid fill 没有直接的 alpha 通道支持，需要操作底层 XML。

**解决**：改用 `_blend()` 函数在 Python 层混合颜色（accent × ratio + bg_dark × (1-ratio)），得到视觉上等价的"暗化 accent"装饰色，无需 XML 操作。

### 踩坑 3：Pydantic `min_length` 版本差异

Pydantic v1 和 v2 的 `Field(min_length=N)` 行为不同。v1 中 `min_length` 只对字符串有效；v2 对 list 类型也有效。`requirements.txt` 锁定 `pydantic>=2.0.0` 以确保行为一致。

## AI 协作复盘

### AI 提出、我采纳的决策

1. **DesignDNA 模式**：AI 建议把所有设计参数封装成一个 Pydantic 对象，由 LLM 生成，传给所有渲染函数。这个想法非常干净——我直接采纳了，它解决了风格一致性的核心问题。

2. **流式调用（streaming）**：AI 建议用 `client.messages.stream()` + `.get_final_message()` 代替普通 `messages.create()`，理由是避免大输出超时。这是正确的，我采纳了。

3. **平衡括号扫描（balanced brace scan）**：AI 建议在正则之外增加一个字符级扫描来提取 JSON，处理嵌套层级。这比纯正则更健壮，我采纳了。

### AI 提出、我推翻的决策

1. **多文件目录结构（10+ 文件，3 次 LLM 调用）**：AI 第一版方案有复杂的目录分层（`core/`、`models/`、`services/`）和三次 LLM 调用。我判断这对一个 72 小时的招聘题来说过度设计——维护成本高，演示成本高，无法在限定时间内打磨好。我推翻并要求重新设计为 4 个文件的极简方案。

2. **使用 Opus 4.8 作为 beauty 模型**：AI 默认建议用最新最强的 Opus 4.8（$5/$25 /MTok）。我推翻了，改用 Sonnet 5（$2/$10 /MTok intro），理由：PPT 内容生成是"创意写作 + 格式化"任务，不需要 Opus 级别的推理能力；成本降低约 60%，且 Sonnet 5 的输出质量在这个场景已足够。

### AI 跑偏、我把它拽回来的场景

1. **过于复杂的容错链**：AI 在初稿中设计了 5 层容错（包括"分段提取"、"逐字段修复"等），代码量超过 200 行。我认为这是过度工程——实际上 LLM 输出格式错误的概率在 5% 以下，三层（提取→重试→硬兜底）已经足够，拽回到了更简洁的实现。

2. **渲染器过于追求 "pixel-perfect"**：AI 尝试用复杂 XML 操作实现透明度、渐变等效果，代码变得难以维护。我把它拽回到"用纯几何形状和颜色混合实现视觉效果"的路线，更可靠也更易维护。

### 对 AI 输出的核验与兜底

- **模型 ID 核验**：AI 提供的模型 ID 通过 `/claude-api` skill 实时查询 Anthropic API 官方文档验证（`claude-sonnet-5`、`claude-haiku-4-5` 已确认）。
- **python-pptx API 核验**：AI 建议的 `shape.fill.transparency` 属性实际不可靠，我通过分析实现改为 `_blend()` 颜色混合方案。
- **Pydantic 版本核验**：AI 最初写的是 v1 风格（`validator` 装饰器），我检查后改为 v2 风格（`model_validator` / `Field(min_length=...)`）。
- **语法全局检查**：所有文件通过 `python -c "import ast; ast.parse()"` 静态语法检查后才视为完成。
