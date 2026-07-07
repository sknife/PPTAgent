import json
import re
from typing import Literal

from pydantic import BaseModel, Field


class DesignDNA(BaseModel):
    bg_dark: str = "#16213E"
    bg_light: str = "#F8F9FA"
    accent: str = "#E94560"
    text_dark: str = "#FFFFFF"
    text_light: str = "#1A1A2E"
    font: str = "Calibri"


class Slide(BaseModel):
    layout: Literal["cover", "section", "bullets", "quote", "stat", "two_col", "closing"]
    title: str
    subtitle: str = ""
    bullets: list[str] = []
    quote: str = ""
    stat_value: str = ""
    stat_label: str = ""
    left: dict = {}
    right: dict = {}


class PresentationData(BaseModel):
    title: str
    design_dna: DesignDNA = Field(default_factory=DesignDNA)
    slides: list[Slide] = Field(min_length=20)


def _extract_json(raw_text: str) -> str:
    """Extract outermost JSON object from LLM output that may contain extra text."""
    # Strategy 1: strip markdown code fences
    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if code_block:
        return code_block.group(1)

    # Strategy 2: balanced-brace scan from first '{'
    start = raw_text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in LLM output")

    depth = 0
    in_string = False
    escape_next = False
    for i, char in enumerate(raw_text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if char == "\\" and in_string:
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return raw_text[start : i + 1]

    raise ValueError("Malformed JSON: unbalanced braces in LLM output")


def parse(raw_text: str) -> PresentationData:
    """Parse LLM output into PresentationData. Raises ValueError on any failure."""
    json_str = _extract_json(raw_text)
    data = json.loads(json_str)
    return PresentationData.model_validate(data)


def fallback_parse(topic: str, raw_text: str) -> PresentationData:
    """
    Hard fallback when all parse attempts fail.
    Splits raw_text into bullets pages around a default DesignDNA.
    """
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    slides: list[Slide] = []

    slides.append(Slide(layout="cover", title=topic, subtitle="AI Generated Presentation"))

    chunk_size = 4
    page = 1
    for i in range(0, len(lines), chunk_size):
        chunk = lines[i : i + chunk_size]
        slides.append(Slide(layout="bullets", title=f"内容 {page}", bullets=chunk))
        page += 1
        if len(slides) >= 29:
            break

    while len(slides) < 25:
        slides.append(Slide(layout="bullets", title="补充内容", bullets=["内容生成中"]))

    slides.append(Slide(layout="closing", title="谢谢", subtitle=topic))

    return PresentationData(title=topic, design_dna=DesignDNA(), slides=slides)
