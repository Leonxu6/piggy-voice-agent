"""
Piggy Research Agent - Core Research Engine
Takes a topic, researches it deeply, reports by voice.
"""

import asyncio
import logging
from typing import List
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
    
    async def research(self, topic: str, user_id: str = None) -> ResearchResult:
        """
        Main research pipeline.
        Takes a topic, returns comprehensive research results.
        """
        logger.info(f"Research started: {topic}")
        
        # Step 1: Execute searches
        results = await self.search.search(topic)
        logger.info(f"Found {len(results)} results")
        
        if not results:
            return ResearchResult(
                topic=topic,
                summary=f"关于「{topic}」没有找到相关信息。",
                key_findings=[],
                sources=[],
                recommendations=[]
            )
        
        # Step 2: Format for LLM
        search_text = self.search.format_results_for_llm(results, topic)
        
        # Step 3: LLM Analysis
        synthesis = await self._synthesize(topic, search_text)
        
        # Step 4: Parse results
        report = self._parse_report(topic, synthesis, results)
        
        # Step 5: Save to memory
        if user_id:
            self.memory.add_research(user_id, topic, report)
        
        logger.info(f"Research complete: {topic}")
        return report
    
    async def _synthesize(self, topic: str, search_results: str) -> str:
        """Use LLM to analyze and synthesize findings"""
        prompt = f"""你是研究助手。请分析以下关于「{topic}」的搜索结果，生成研究报告。

{search_results}

请生成完整的研究报告，包括：

1. **简要总结** (2-3句话)
   - 这个话题的核心要点是什么？

2. **关键发现** (3-5点)
   - 最重要的信息是什么？
   - 有什么新观点或趋势？

3. **来源分析**
   - 主要信息来源是哪些平台？
   - 信息质量如何？

4. **建议** (可选)
   - 如果有实用建议，列出1-3条

请用中文回答，格式清晰，便于语音朗读。"""
        
        return await self.llm.chat(prompt)
    
    def _parse_report(self, topic: str, synthesis: str, results: List) -> ResearchResult:
        """Parse LLM synthesis into structured report"""
        # Extract sources
        sources = []
        for r in results[:5]:
            if r.get('url'):
                sources.append(r['url'])
        
        # Parse findings from text
        findings = []
        recommendations = []
        
        lines = synthesis.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect sections
            if '关键发现' in line or '发现' in line:
                current_section = 'findings'
                continue
            elif '建议' in line:
                current_section = 'recommendations'
                continue
            elif '总结' in line or '核心' in line:
                current_section = 'summary'
                continue
            
            # Extract bullet points
            if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                content = line.lstrip('•- *').strip()
                if current_section == 'findings' and content:
                    findings.append(content)
                elif current_section == 'recommendations' and content:
                    recommendations.append(content)
        
        return ResearchResult(
            topic=topic,
            summary=synthesis[:500] if len(synthesis) > 500 else synthesis,
            key_findings=findings[:5],
            sources=sources,
            recommendations=recommendations[:3]
        )
    
    def format_for_voice(self, result: ResearchResult) -> str:
        """Format research result for voice output"""
        report = f"关于「{result.topic}」的研究报告。 "
        
        # Summary
        report += result.summary + " "
        
        # Key findings
        if result.key_findings:
            report += "关键发现："
            for i, finding in enumerate(result.key_findings, 1):
                report += f"第{i}点，{finding}。"
            report += " "
        
        # Recommendations
        if result.recommendations:
            report += "建议："
            for rec in result.recommendations:
                report += f"{rec}。"
        
        return report
