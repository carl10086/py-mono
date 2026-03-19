"""编辑工具辅助函数。

提供差异计算和模糊匹配功能。
"""

from __future__ import annotations

import difflib
import unicodedata
from dataclasses import dataclass

__all__ = [
    "FuzzyMatchResult",
    "EditDiffResult",
    "detect_line_ending",
    "normalize_to_lf",
    "restore_line_endings",
    "normalize_for_fuzzy_match",
    "fuzzy_find_text",
    "strip_bom",
    "generate_diff_string",
]


@dataclass
class FuzzyMatchResult:
    """模糊匹配结果。

    Attributes:
        found: 是否找到匹配。
        index: 匹配起始索引。
        match_length: 匹配文本长度。
        used_fuzzy_match: 是否使用了模糊匹配（False表示精确匹配）。
        content_for_replacement: 用于替换操作的内容。

    """

    found: bool
    index: int
    match_length: int
    used_fuzzy_match: bool
    content_for_replacement: str


@dataclass
class EditDiffResult:
    """差异结果。

    Attributes:
        diff: 差异字符串（统一差异格式）。
        first_changed_line: 新文件中第一个变更的行号（如果有）。

    """

    diff: str
    first_changed_line: int | None = None


def detect_line_ending(content: str) -> str:
    """检测文件使用的换行符类型。

    Args:
        content: 文件内容。

    Returns:
        "\r\n" 或 "\n"。

    """
    crlf_idx = content.find("\r\n")
    lf_idx = content.find("\n")
    if lf_idx == -1:
        return "\n"
    if crlf_idx == -1:
        return "\n"
    return "\r\n" if crlf_idx < lf_idx else "\n"


def normalize_to_lf(text: str) -> str:
    """将文本中的换行符标准化为LF。

    Args:
        text: 原始文本。

    Returns:
        标准化后的文本。

    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


def restore_line_endings(text: str, ending: str) -> str:
    """恢复换行符类型。

    Args:
        text: 使用LF的文本。
        ending: 目标换行符类型（"\r\n" 或 "\n"）。

    Returns:
        恢复换行符后的文本。

    """
    return text.replace("\n", ending) if ending == "\r\n" else text


def normalize_for_fuzzy_match(text: str) -> str:
    """标准化文本用于模糊匹配。

    应用渐进式转换：
    - 去除每行末尾的空白字符
    - 将智能引号转换为ASCII等效字符
    - 将Unicode破折号/连字符标准化为ASCII连字符
    - 将特殊Unicode空格标准化为普通空格

    Args:
        text: 原始文本。

    Returns:
        标准化后的文本。

    """
    # Unicode规范化
    normalized = unicodedata.normalize("NFKC", text)

    # 去除每行末尾的空白字符
    lines = normalized.split("\n")
    lines = [line.rstrip() for line in lines]
    normalized = "\n".join(lines)

    # 智能单引号 → '
    normalized = normalized.replace("\u2018", "'").replace("\u2019", "'")
    normalized = normalized.replace("\u201a", "'").replace("\u201b", "'")

    # 智能双引号 → "
    normalized = normalized.replace("\u201c", '"').replace("\u201d", '"')
    normalized = normalized.replace("\u201e", '"').replace("\u201f", '"')

    # 各种破折号/连字符 → -
    dashes = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"
    for dash in dashes:
        normalized = normalized.replace(dash, "-")

    # 特殊空格 → 普通空格
    special_spaces = "\u00a0\u202f\u205f\u3000"
    for space in special_spaces:
        normalized = normalized.replace(space, " ")
    # U+2002 到 U+200A 的各种空格
    for code in range(0x2002, 0x200B):
        normalized = normalized.replace(chr(code), " ")

    return normalized


def fuzzy_find_text(content: str, old_text: str) -> FuzzyMatchResult:
    """在内容中查找old_text，先尝试精确匹配，再尝试模糊匹配。

    当使用模糊匹配时，返回的content_for_replacement是内容的
    模糊规范化版本（去除了行尾空白，Unicode引号/破折号标准化为ASCII）。

    Args:
        content: 文件内容。
        old_text: 要查找的旧文本。

    Returns:
        匹配结果。

    """
    # 先尝试精确匹配
    exact_index = content.find(old_text)
    if exact_index != -1:
        return FuzzyMatchResult(
            found=True,
            index=exact_index,
            match_length=len(old_text),
            used_fuzzy_match=False,
            content_for_replacement=content,
        )

    # 尝试模糊匹配 - 在规范化空间中工作
    fuzzy_content = normalize_for_fuzzy_match(content)
    fuzzy_old_text = normalize_for_fuzzy_match(old_text)
    fuzzy_index = fuzzy_content.find(fuzzy_old_text)

    if fuzzy_index == -1:
        return FuzzyMatchResult(
            found=False,
            index=-1,
            match_length=0,
            used_fuzzy_match=False,
            content_for_replacement=content,
        )

    # 使用模糊匹配时，我们在规范化空间中进行替换操作
    return FuzzyMatchResult(
        found=True,
        index=fuzzy_index,
        match_length=len(fuzzy_old_text),
        used_fuzzy_match=True,
        content_for_replacement=fuzzy_content,
    )


def strip_bom(content: str) -> tuple[str, str]:
    """移除UTF-8 BOM（如果存在）。

    Args:
        content: 原始内容。

    Returns:
        (BOM字符串, 移除BOM后的文本)。

    """
    if content.startswith("\ufeff"):
        return "\ufeff", content[1:]
    return "", content


def generate_diff_string(
    old_content: str,
    new_content: str,
    context_lines: int = 4,
) -> EditDiffResult:
    """生成统一差异格式的字符串。

    Args:
        old_content: 旧内容。
        new_content: 新内容。
        context_lines: 上下文行数（默认4行）。

    Returns:
        差异结果。

    """
    old_lines = old_content.split("\n")
    new_lines = new_content.split("\n")

    # 使用difflib生成差异
    differ = difflib.Differ()
    diff = list(differ.compare(old_lines, new_lines))

    max_line_num = max(len(old_lines), len(new_lines))
    line_num_width = len(str(max_line_num))

    output: list[str] = []
    old_line_num = 1
    new_line_num = 1
    last_was_change = False
    first_changed_line: int | None = None

    i = 0
    while i < len(diff):
        line = diff[i]
        marker = line[0] if line else " "
        text = line[2:] if len(line) > 2 else ""

        if marker in ("+", "-"):
            # 记录第一个变更的行号
            if first_changed_line is None and marker == "+":
                first_changed_line = new_line_num

            # 显示变更
            if marker == "+":
                line_num = str(new_line_num).rjust(line_num_width)
                output.append(f"+{line_num} {text}")
                new_line_num += 1
            else:
                line_num = str(old_line_num).rjust(line_num_width)
                output.append(f"-{line_num} {text}")
                old_line_num += 1
            last_was_change = True

        elif marker == " ":
            # 上下文行 - 只显示变更前后的几行
            # 检查下一个是否是变更
            next_is_change = False
            if i + 1 < len(diff):
                next_marker = diff[i + 1][0] if diff[i + 1] else " "
                next_is_change = next_marker in ("+", "-")

            if last_was_change or next_is_change:
                # 收集连续上下文行
                context_start = i
                context_end = i
                while context_end < len(diff) and diff[context_end][0] == " ":
                    context_end += 1

                context_block = diff[context_start:context_end]

                # 决定显示哪些上下文行
                if not last_was_change and len(context_block) > context_lines:
                    # 只显示最后N行作为前导上下文
                    skip_count = len(context_block) - context_lines
                    context_block = context_block[-context_lines:]
                    if skip_count > 0:
                        output.append(f" {''.rjust(line_num_width)} ...")
                        old_line_num += skip_count
                        new_line_num += skip_count

                if not next_is_change and len(context_block) > context_lines:
                    # 只显示前N行作为尾随上下文
                    keep_count = context_lines
                    skip_count = len(context_block) - keep_count
                    context_block = context_block[:keep_count]

                for ctx_line in context_block:
                    ctx_text = ctx_line[2:] if len(ctx_line) > 2 else ""
                    line_num = str(old_line_num).rjust(line_num_width)
                    output.append(f" {line_num} {ctx_text}")
                    old_line_num += 1
                    new_line_num += 1

                if not next_is_change and len(context_block) > 0:
                    remaining = len(diff[context_start:context_end]) - len(context_block)
                    if remaining > 0:
                        output.append(f" {''.rjust(line_num_width)} ...")
                        old_line_num += remaining
                        new_line_num += remaining
            else:
                # 完全跳过这些上下文行
                old_line_num += 1
                new_line_num += 1

            last_was_change = False

        elif marker == "?":
            # 忽略差异标记行
            pass

        i += 1

    return EditDiffResult(diff="\n".join(output), first_changed_line=first_changed_line)
