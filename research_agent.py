"""
Piggy Research Agent - Core Research Engine
Takes a topic, researches it deeply, reports by voice.
"""

import asyncio
import logging
import re
from typing import List, Callable, Optional

from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ResearchResult:
    """Research output"""
    topic: str
    summary: str
    key_findings: List[str]
    sources: List[str]
    recommendations: List[str]


def _to_chinese_digits(text: str) -> str:
    """
    Convert English numbers and symbols to a format that sounds natural in Chinese TTS.
    E.g. "Q4 2024" -> "第4季度2024年"
    E.g. "AI" -> "A I" (spell it out)
    E.g. "100%" -> "百分之百"
    E.g. "$5B" -> "50亿美元"
    """
    # Percentage
    text = re.sub(r'(\d+(?:\.\d+)?)\s*%', lambda m: f'{m.group(1)}百分之', text)

    # Billion/Million with $ or RMB prefix
    text = re.sub(r'\$\s*(\d+(?:\.\d+)?)\s*[Bb]', lambda m: f'{m.group(1)}亿美元', text)
    text = re.sub(r'(\d+(?:\.\d+)?)\s*[Bb]\s*美元', lambda m: f'{m.group(1)}亿美元', text)
    text = re.sub(r'RMB\s*(\d+(?:\.\d+)?)\s*[Bb]', lambda m: f'{m.group(1)}亿人民币', text)

    # Plain large numbers - add thousand/million/billion suffix
    def format_number(m):
        num = float(m.group(1).replace(',', ''))
        if num >= 1_000_000_000:
            return f'{num/1_000_000_000:.1f}十亿' if num >= 2_000_000_000 else f'{num/1_000_000_000:.1f}十亿'
        elif num >= 1_000_000:
            return f'{num/1_000_000:.1f}百万'
        elif num >= 10_000:
            return f'{num/10_000:.1f}万'
        return str(num)

    text = re.sub(r'\b(\d{1,3}(?:,\d{3})+(?:\.\d+)?)\b', format_number, text)
    text = re.sub(r'\b(\d+(?:\.\d+)?)\s*[Bb]\b', format_number, text)
    text = re.sub(r'\b(\d+(?:\.\d+)?)\s*[Mm]\b', lambda m: f'{float(m.group(1)):.0f}百万', text)

    # Quarter notation
    text = re.sub(r'[Qq](\d)\s*20(\d{2})', lambda m: f'20{m.group(2)}年第{m.group(1)}季度', text)
    text = re.sub(r'[Qq](\d)', lambda m: f'第{m.group(1)}季度', text)

    # Year alone
    text = re.sub(r'\b(20\d{2})\b', lambda m: f'{m.group(1)}年', text)

    # Spell out short acronyms that TTS would mangle
    acronyms = ['AI', 'LLM', 'NLP', 'GPT', 'API', 'SaaS', 'CEO', 'CFO', 'COO', 'IPO', 'GDP', 'USD', 'RMB', 'EU', 'UK', 'US', 'USA', 'FDA', 'SEC']
    for acr in sorted(acronyms, key=len, reverse=True):
        text = re.sub(rf'\b{acr}\b', ' '.join(acr), text, flags=re.IGNORECASE)

    # Ordinal numbers
    text = re.sub(r'\bNo\.?\s*(\d+)\b', lambda m: f'第{m.group(1)}条', text)
    text = re.sub(r'\b第(\d+)名\b', lambda m: f'第{m.group(1)}名', text)

    # Slash-separated -> Chinese "或者" or "每"
    text = re.sub(r'(\w+)/(\w+)', lambda m: f'{m.group(1)}或{m.group(2)}', text)

    return text


class ResearchAgent:
    """
    Core research agent that:
    1. Plans research approach
    2. Executes multi-source search
    3. Synthesizes findings via LLM
    4. Generates voice report
    """

    def __init__(self, llm_client, search_engine, memory):
        self.llm = llm_client
        self.search = search_engine
        self.memory = memory

    async def research(
        self,
        topic: str,
        user_id: str = None,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> ResearchResult:
        """
        Main research pipeline with progress reporting.
        Takes a topic, returns comprehensive research results.
        """
        logger.info(f"Research started: {topic}")

        # Helper to send status
        async def status(msg: str):
            if status_callback:
                await status_callback(msg)

        # Step 1: Multi-source search with progress
        await status(f"🔍 正在搜索 {topic}...")
        results = await self.search.search(topic, status_callback=lambda m: asyncio.create_task(status(m)))
        logger.info(f"Found {len(results)} results")

        if not results:
            await status("⚠️ 未找到相关信息，换个话题试试？")
            return ResearchResult(
                topic=topic,
                summary=f"关于「{topic}」没有找到相关信息。",
                key_findings=[],
                sources=[],
                recommendations=[]
            )

        # Group by source for status
        by_source: dict = {}
        for r in results:
            by_source.setdefault(r.get('source', 'Unknown'), []).append(r)
        source_summary = '、'.join([f"{k}({len(v)}条)" for k, v in by_source.items()])
        await status(f"✅ 找到 {len(results)} 条结果（{source_summary}）")

        # Step 2: LLM Analysis with progress
        await status("🧠 正在分析信息...")
        search_text = self.search.format_results_for_llm(results, topic)

        # Step 3: Get user's memory context if available
        memory_context = ""
        if user_id:
            history = self.memory.get_conversation(user_id)
            research_file = self.memory.storage_dir / f"{user_id}_research.json"
            if research_file.exists():
                try:
                    import json
                    with open(research_file, 'r', encoding='utf-8') as f:
                        recent = json.load(f)
                        if recent and len(recent) > 0:
                            last = recent[-1]
                            memory_context = f"\n\n【用户历史研究记录】\n最近研究过：「{last.get('topic', '')}」\n摘要：{last.get('summary', '')[:200]}\n"
                except Exception:
                    pass

        synthesis = await self._synthesize(topic, search_text, memory_context)
        await status("✅ 分析完成，正在生成报告...")

        # Step 4: Parse results
        report = self._parse_report(topic, synthesis, results)

        # Step 5: Save to memory
        if user_id:
            self.memory.add_research(user_id, topic, report)

        logger.info(f"Research complete: {topic}")
        return report

    async def _synthesize(self, topic: str, search_results: str, memory_context: str = "") -> str:
        """Use LLM to analyze and synthesize findings"""
        prompt = f"""你是专业的研究分析师。请分析以下关于「{topic}」的搜索结果，生成结构化研究报告。

{search_results}
{memory_context}

请生成完整的研究报告，要求：

1. **简要总结**（2-3句话，中文）
   - 这个话题的核心要点是什么？
   - 当前整体态势如何？

2. **关键发现**（3-5条，中文）
   - 最重要的信息是什么？
   - 有什么新观点或趋势？
   - 每条尽量包含具体数据或来源

3. **来源说明**
   - 主要信息来源是哪些平台？
   - 各来源的信息权重（权威/一般/需验证）

4. **实用建议**（1-3条）
   - 基于这些发现，有什么具体可操作的建议？

请用中文回答，格式清晰，便于语音朗读。
报告中的数字、英文请用自然的中文表达，例如："Q4"说"第四季度"，"AI"说"A I"，"$5B"说"50亿美元"。"""

        return await self.llm.chat(prompt)

    def _parse_report(self, topic: str, synthesis: str, results: List) -> ResearchResult:
        """Parse LLM synthesis into structured report"""
        # Extract top sources
        sources = []
        for r in results[:8]:
            url = r.get('url', '')
            if url and url not in sources:
                sources.append(url)

        # Parse findings/recommendations from text
        findings = []
        recommendations = []
        summary_parts = []

        lines = synthesis.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect sections
            lower = line.lower()
            if '总结' in line or '核心' in line or ('简要' in line and '总结' in line):
                current_section = 'summary'
                continue
            elif '关键发现' in line or '发现' in line or '要点' in line:
                current_section = 'findings'
                continue
            elif '建议' in line:
                current_section = 'recommendations'
                continue
            elif '来源' in line and '平台' in line:
                current_section = 'sources'
                continue

            # Extract bullet points
            if line.startswith('•') or line.startswith('-') or line.startswith('*') or re.match(r'^\d+[.、]', line):
                content = re.sub(r'^[•\-*]\s*', '', line)
                content = re.sub(r'^\d+[.、]\s*', '', content).strip()
                if not content:
                    continue
                if current_section == 'findings':
                    findings.append(content)
                elif current_section == 'recommendations':
                    recommendations.append(content)

        # If summary parsing failed, use first paragraph
        if not summary_parts:
            paras = synthesis.split('\n\n')
            for para in paras:
                para = para.strip()
                if len(para) > 50 and not para.startswith('•') and not re.match(r'^\d+[.、]', para):
                    summary_parts.append(para)
                    break

        summary = ' '.join(summary_parts) if summary_parts else synthesis[:300]

        return ResearchResult(
            topic=topic,
            summary=summary,
            key_findings=findings[:5],
            sources=sources,
            recommendations=recommendations[:3]
        )

    def format_for_voice(self, result: ResearchResult) -> str:
        """
        Format research result for voice/TTS output.
        Makes numbers, acronyms, and symbols TTS-friendly.
        """
        report_parts = []

        # Opening
        report_parts.append(f"关于「{result.topic}」的研究报告。")

        # Summary
        summary_clean = _to_chinese_digits(result.summary)
        report_parts.append(summary_clean)

        # Key findings
        if result.key_findings:
            report_parts.append("以下是关键发现：")
            for i, finding in enumerate(result.key_findings, 1):
                finding_clean = _to_chinese_digits(finding)
                # Truncate if too long (TTS can't handle very long strings)
                if len(finding_clean) > 150:
                    finding_clean = finding_clean[:145] + "..."
                report_parts.append(f"第{i}点，{finding_clean}。")
            report_parts.append("关键发现播报完毕。")

        # Recommendations
        if result.recommendations:
            report_parts.append("以下是实用建议：")
            for rec in result.recommendations:
                rec_clean = _to_chinese_digits(rec)
                if len(rec_clean) > 150:
                    rec_clean = rec_clean[:145] + "..."
                report_parts.append(rec_clean + "。")
            report_parts.append("建议播报完毕。")

        # Assemble (respect 500-char TTS limit)
        full_text = ' '.join(report_parts)
        if len(full_text) <= 490:
            return full_text

        # Truncate intelligently
        return full_text[:485] + "。报告结束。"
