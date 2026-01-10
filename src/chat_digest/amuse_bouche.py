"""Synthesis engine for the 'Amuse-bouche' (Perfect BYTE) - highly dense legal artifacts."""

from __future__ import annotations

import textwrap
from typing import Dict, List, Optional
from .schemas import Message, Summary
from .patterns import Pattern

class AmuseBouche:
    """Represents a distilled 'Perfect BYTE' of a legal conversation."""
    
    def __init__(
        self,
        brief: str,
        patterns: List[Pattern],
        signals: Dict[str, List[str]],
        metadata: Dict[str, any]
    ):
        self.brief = brief
        self.patterns = patterns
        self.signals = signals
        self.metadata = metadata

    def to_markdown(self) -> str:
        """Render the Amuse-bouche as a high-density Markdown block."""
        
        # Aggregate patterns into tactical bullets
        pattern_bullets = []
        for p in self.patterns:
            if p.confidence > 0.8:  # High confidence only
                pattern_bullets.append(f"🚩 **{p.pattern_type.replace('_', ' ').title()}**: {p.description}")

        # Extract top decisions and constraints
        decisions = self.signals.get("decisions", [])[:3]
        constraints = self.signals.get("constraints", [])[:3]
        
        md = textwrap.dedent(f"""
        # 🧪 THE AMUSE-BOUCHE: Perfect BYTE Snapshot
        *Legal State Continuity Record | {self.metadata.get('date', 'Unknown Date')}*
        
        ## 🧠 CONTEXT BRIEF
        {self.brief}
        
        ## ⚖️ AGGREGATE PATTERNS (NON-CONFORMANCE)
        {chr(10).join(pattern_bullets) if pattern_bullets else "No systemic patterns detected yet."}
        
        ## 📜 CORE ARTIFACTS
        ### 🎯 Decisions
        {chr(10).join(['- ' + d for d in decisions]) if decisions else "- None identified."}
        
        ### 🛑 Constraints
        {chr(10).join(['- ' + c for c in constraints]) if constraints else "- None identified."}
        
        ## 🤖 AI CONTINUITY STRING (HOT-LOAD)
        > **State:** {self.metadata.get('status', 'Active Analysis')}
        > **Criticality:** {self.metadata.get('importance', 'Medium')}
        > **Key Actors:** {', '.join(self.metadata.get('actors', ['Unknown']))}
        """).strip()
        
        return md

def synthesize_byte(
    summary: Summary, 
    patterns: List[Pattern], 
    actors: List[str]
) -> AmuseBouche:
    """Synthesize raw components into a Perfect BYTE."""
    
    signals = {
        "decisions": summary.decisions,
        "actions": summary.actions,
        "constraints": summary.constraints,
    }
    
    metadata = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "actors": actors,
        "status": "Analyzing Patterns of Deception",
        "importance": "High (Strategic)" if any(p.confidence > 0.9 for p in patterns) else "Medium"
    }
    
    return AmuseBouche(
        brief=summary.brief,
        patterns=patterns,
        signals=signals,
        metadata=metadata
    )

from datetime import datetime
