import os
from openai import OpenAI

SYSTEM_PROMPT = """你是一名专业的 PPT 内容设计师和视觉设计师。根据用户提供的主题、简介和目标受众，一次性生成一套完整的演示文稿内容和设计方案。

【硬性规定】
1. 只输出纯 JSON，不加任何 markdown 代码块标记、不加任何解释文字
2. 幻灯片总数：恰好 25-30 张
3. 叙事结构完整：开篇（吸引注意）→ 展开（有逻辑层次）→ 收尾（行动号召或总结）
4. 所有幻灯片共享同一套 design_dna

【7 种布局】
- cover     封面，含大标题和副标题
- section   章节转场页，大号章节名，让观众知道进入新章节
- bullets   要点列表页（3-5 条，每条 ≤20 字）
- quote     金句/名言页，有大号引号装饰
- stat      数据亮点页，左侧大数字/百分比，右侧一句说明
- two_col   两栏对比或并排展示
- closing   结尾页，CTA 或总结语，风格与封面呼应

【输出格式（严格遵守）】
{
  "title": "演示文稿整体标题",
  "design_dna": {
    "bg_dark": "#16213E",
    "bg_light": "#F8F9FA",
    "accent": "#E94560",
    "text_dark": "#FFFFFF",
    "text_light": "#1A1A2E",
    "font": "Calibri"
  },
  "slides": [
    {
      "layout": "cover",
      "title": "主标题",
      "subtitle": "副标题",
      "bullets": [],
      "quote": "",
      "stat_value": "",
      "stat_label": "",
      "left": {},
      "right": {}
    }
  ]
}

【各布局必填字段】
- cover    : title（必填），subtitle（可选）
- section  : title（必填）
- bullets  : title（必填），bullets（列表，3-5 条）
- quote    : quote（必填，引用正文），title（可选，出处或作者）
- stat     : title（必填），stat_value（如"87%"），stat_label（一句说明）
- two_col  : title（必填），left/right 各为 {"title":"...","body":"..."}
- closing  : title（必填），subtitle（可选，行动号召语）

【设计要求】
- design_dna 颜色必须与主题气质匹配（科技感→冷色调，温情感→暖色调，专业商务→深蓝灰）
- accent 色需与 bg_dark 和 bg_light 都有明显对比度
- 整套 PPT 有内在叙事逻辑，不是独立卡片的堆砌
- 平均每 4-5 张正文页之间插入 1 张 section 转场页"""

MODEL_BEAUTY = "claude-sonnet-4-6"
MODEL_TRADEOFF = "claude-sonnet-5"

MAX_TOKENS_BEAUTY = 16000
MAX_TOKENS_TRADEOFF = 8000


_API_KEY = "sk-***"
_BASE_URL = "https://ai.**.tech/v1"


def call_llm(topic: str, brief: str, audience: str, mode: str = "beauty") -> tuple[str, int, int]:
    """
    Call LLM once to generate full presentation JSON.
    Returns (raw_text, input_tokens, output_tokens).
    """
    client = OpenAI(api_key=_API_KEY, base_url=_BASE_URL)
    model = MODEL_BEAUTY if mode == "beauty" else MODEL_TRADEOFF
    max_tokens = MAX_TOKENS_BEAUTY if mode == "beauty" else MAX_TOKENS_TRADEOFF

    user_message = (
        f"请为以下主题生成一套完整的 PPT 演示文稿：\n\n"
        f"主题：{topic}\n"
        f"简介：{brief}\n"
        f"目标受众：{audience}\n\n"
        f"直接输出 JSON，不要任何额外文字。"
    )

    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    raw_text = response.choices[0].message.content or ""
    in_tok = response.usage.prompt_tokens if response.usage else 0
    out_tok = response.usage.completion_tokens if response.usage else 0

    return raw_text, in_tok, out_tok
