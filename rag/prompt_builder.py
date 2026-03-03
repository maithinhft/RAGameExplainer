"""
Prompt Builder — Construct context-augmented prompts for the LLM.

Takes search results and the user's question, then builds a structured
prompt that gives the LLM relevant game data as context.
"""

from __future__ import annotations

from rag.search import SearchResult


# System prompt for the League of Legends expert
SYSTEM_PROMPT = """Bạn là một chuyên gia League of Legends với kiến thức sâu rộng về game.
Hãy trả lời câu hỏi dựa trên dữ liệu game được cung cấp bên dưới.

Quy tắc:
1. Ưu tiên sử dụng dữ liệu được cung cấp để trả lời chính xác.
2. Nếu dữ liệu không đủ, hãy bổ sung từ kiến thức của bạn nhưng ghi rõ phần nào là từ dữ liệu, phần nào là nhận định.
3. Trả lời bằng tiếng Việt, rõ ràng và dễ hiểu.
4. Khi nói về stats, items, hay abilities, hãy cung cấp con số cụ thể nếu có.
5. Giải thích lý do đằng sau meta/build nếu được hỏi."""


def build_prompt(
    question: str,
    results: list[SearchResult],
    max_context_length: int = 4000,
) -> str:
    """Build a context-augmented prompt from search results.

    Args:
        question: The user's original question.
        results: Ranked search results from the search engine.
        max_context_length: Maximum character length for context block.

    Returns:
        Full prompt string ready to send to the LLM.
    """
    # Build context from search results
    context_parts: list[str] = []
    current_length = 0

    for i, result in enumerate(results, 1):
        doc = result.document

        # Format context block
        block = (
            f"[{i}. {doc.category.upper()}: {doc.title}] "
            f"(relevance: {result.score:.2f})\n"
            f"{doc.content}"
        )

        # Check length limit
        if current_length + len(block) > max_context_length:
            # Truncate last block if needed
            remaining = max_context_length - current_length
            if remaining > 200:
                context_parts.append(block[:remaining] + "\n...(truncated)")
            break

        context_parts.append(block)
        current_length += len(block)

    context_text = "\n\n---\n\n".join(context_parts) if context_parts else "(Không tìm thấy dữ liệu liên quan)"

    # Assemble final prompt
    prompt = f"""{SYSTEM_PROMPT}

═══════════════════════════════════════
DỮ LIỆU GAME LIÊN QUAN
═══════════════════════════════════════

{context_text}

═══════════════════════════════════════
CÂU HỎI CỦA NGƯỜI DÙNG
═══════════════════════════════════════

{question}

Hãy trả lời chi tiết và chính xác dựa trên dữ liệu ở trên:"""

    return prompt


def build_prompt_compact(
    question: str,
    results: list[SearchResult],
    max_context_length: int = 2000,
) -> str:
    """Build a shorter prompt for models with limited context windows.

    Uses only titles and key stats, not full document content.
    """
    context_parts: list[str] = []

    for result in results[:3]:  # Top 3 only
        doc = result.document
        # Use first 300 chars of content
        short_content = doc.content[:300].strip()
        if len(doc.content) > 300:
            short_content += "..."
        context_parts.append(f"• {doc.title}: {short_content}")

    context_text = "\n\n".join(context_parts) if context_parts else "(Không có dữ liệu)"

    return f"""{SYSTEM_PROMPT}

DỮ LIỆU:
{context_text}

CÂU HỎI: {question}

TRẢ LỜI:"""
