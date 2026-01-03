# Chronicle + chat-digest Integration Plan

## 🎯 The Perfect Match

**Chronicle**: Timeline tracking with legal workflow features
**chat-digest**: AI conversation intelligence and pattern detection

**Together**: Complete "Memory Amuse-bouche" system for long-term case tracking

---

## �� Current State Analysis

### Chronicle Strengths:
✅ Event timeline storage (SQLite)
✅ Legal workflow fields (actor, evidence_links, privileged_notes)
✅ CSV import/export
✅ Document attachments
✅ Full-text search
✅ Timeline visualization
✅ Voice transcription

### Chronicle Gaps (What chat-digest Solves):
❌ No chat conversation processing
❌ No pattern detection across time
❌ No contradiction tracking
❌ No importance scoring
❌ No aggregate impact analysis
❌ No "memory snapshot" generation

### chat-digest Strengths:
✅ Parses chat conversations
✅ Extracts decisions, actions, questions
✅ Temporal analysis (timeline + supersessions)
✅ Entity extraction (people, agreements)
✅ Importance scoring
✅ Code/quote preservation
✅ Multi-format output

### chat-digest Gaps (What Chronicle Solves):
❌ No persistent storage
❌ No visualization
❌ No legal workflow features
❌ No document management
❌ No export to PDF

---

## 🔄 Integration Architecture

```
Your Daily Workflow:
┌──────────────────────────────────────────────────────┐
│ 1. Chat with AI about case (daily diary)            │
│    Save as: daily-2026-01-03.md                      │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│ 2. chat-digest processes conversation                │
│    $ chat-digest daily-2026-01-03.md \               │
│        --chronicle-export events.csv                 │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│ 3. Chronicle imports events                          │
│    - Timeline updated automatically                  │
│    - Entities tracked                                │
│    - Evidence preserved                              │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│ 4. Generate "Amuse-bouche" snapshot                  │
│    $ chat-digest --from-chronicle case-123 \         │
│        --amuse-bouche snapshot.md                    │
│    Result: 16 months → 8K tokens                     │
└──────────────────────────────────────────────────────┘
```

---

## 📋 Data Format Mapping

### Chronicle Event Model:
```python
class Event:
    id: str
    title: str
    description: str
    date: datetime
    timeline: str              # Category/project
    actor: str                 # Who was responsible
    emotion: str
    tags: str
    evidence_links: str        # Supporting documents
    privileged_notes: str      # Attorney work product
    audio_file: str
    transcription_words: str
    summary: str
```

### chat-digest → Chronicle CSV Export:
```csv
title,description,date,timeline,actor,emotion,tags,evidence_links
"Opposing counsel missed deadline","Third violation of court order in 60 days","2026-01-03 14:30:00","Legal","Opposing Counsel","frustrated","violation,deadline,pattern",""
"Pattern detected","Promise-break cycle: avg 12 days","2026-01-03 14:35:00","Legal","System","analytical","pattern,analysis",""
```

### Mapping Strategy:
| chat-digest | Chronicle | Notes |
|-------------|-----------|-------|
| Message with decision tag | Event with actor | Extract who made decision |
| Message timestamp | Event date | Direct mapping |
| Importance score | Emotion | High score = "critical" |
| Extracted entities | Tags | Comma-separated |
| Code blocks/quotes | Evidence_links | Save as files, link |
| Supersessions | New event | "Contradiction detected" |
| Pattern detection | New event | "Pattern: promise-break" |

---

## 🚀 Implementation Phases

### Phase 1: Basic Export (IMMEDIATE)
**Goal**: Get chat conversations into Chronicle

**Implementation**:
```python
# In chat-digest/src/chat_digest/chronicle.py
def export_to_chronicle_csv(digest: ThreadDigest) -> str:
    """Export digest to Chronicle-compatible CSV"""
    events = []
    
    for msg in digest.messages:
        if msg.importance_score >= 7.0:  # Only important messages
            event = {
                'title': _extract_title(msg),
                'description': msg.content[:500],
                'date': msg.timestamp or datetime.now(),
                'timeline': 'Legal',  # or from config
                'actor': _extract_actor(msg),
                'emotion': _score_to_emotion(msg.importance_score),
                'tags': ','.join(msg.tags),
                'evidence_links': ''
            }
            events.append(event)
    
    return _to_csv(events)
```

**CLI**:
```bash
chat-digest daily-diary.md --chronicle-export events.csv
```

**Timeline**: 2-3 hours

---

### Phase 2: Pattern Events (NEXT)
**Goal**: Surface patterns as Chronicle events

**Implementation**:
```python
# Detect patterns and create events
patterns = detect_patterns(messages)

for pattern in patterns:
    event = {
        'title': f"Pattern: {pattern.type}",
        'description': pattern.description,
        'date': pattern.last_occurrence,
        'timeline': 'Analysis',
        'actor': 'System',
        'emotion': 'analytical',
        'tags': 'pattern,analysis,automated',
        'evidence_links': pattern.evidence_file
    }
```

**Example Output**:
```csv
"Pattern: Promise-Break Cycle","Detected 23 instances over 16 months. Average 12 days from promise to violation. 98% confidence.","2026-01-03 15:00:00","Analysis","System","analytical","pattern,statistical",""
```

**Timeline**: 4-6 hours

---

### Phase 3: Contradiction Tracking (THEN)
**Goal**: Auto-detect and log contradictions

**Implementation**:
```python
# Enhanced supersession detection
contradictions = detect_contradictions(messages)

for contradiction in contradictions:
    event = {
        'title': f"Contradiction #{contradiction.id}",
        'description': f"Claim 1: {contradiction.claim1}\nClaim 2: {contradiction.claim2}",
        'date': contradiction.date2,
        'timeline': 'Evidence',
        'actor': contradiction.actor,
        'emotion': 'suspicious',
        'tags': 'contradiction,evidence,lie',
        'evidence_links': contradiction.proof
    }
```

**Timeline**: 6-8 hours

---

### Phase 4: Amuse-bouche Generator (FINAL)
**Goal**: Generate complete memory snapshot from Chronicle data

**Implementation**:
```bash
# Query Chronicle database, generate compressed snapshot
chat-digest --from-chronicle \
  --timeline "Legal" \
  --date-range "2024-01-01:2026-01-03" \
  --amuse-bouche snapshot.md
```

**Output Format**:
```markdown
# Case Memory Snapshot (16 months → 8,432 tokens)

## Quick Facts
- Duration: 16 months (Jan 2024 - Jan 2026)
- Total events: 347
- Critical violations: 47
- Patterns detected: 8
- Contradictions: 23

## Timeline (Top 30 Events)
[Chronological list with importance scores]

## Patterns Detected
1. **Promise-Break Cycle** (98% confidence)
   - Frequency: 23 instances
   - Average delay: 12 days
   - Trend: Escalating

2. **Friday Violations** (67% of incidents)
   - Statistical significance: p < 0.01
   - Suggests intentional timing

## Contradictions (Proven)
[List of conflicting statements with evidence]

## Aggregate Impact
[Cumulative analysis with visualizations]

## Most Damaging Evidence
[Top 10 items ranked by importance]

## Current State & Recommendations
[Where we are, what to do next]
```

**Timeline**: 8-12 hours

---

## 🎯 Quick Win: Minimal Viable Integration

**What**: Get your chat conversations into Chronicle TODAY

**How**:
1. Add `chronicle.py` to chat-digest
2. Implement basic CSV export
3. Test with one day's conversation
4. Import to Chronicle
5. Verify timeline appears correctly

**Code**:
```python
# chat-digest/src/chat_digest/chronicle.py
import csv
from datetime import datetime
from typing import List
from .schemas import ThreadDigest, Message

def export_to_chronicle(digest: ThreadDigest, output_path: str):
    """Export digest to Chronicle CSV format"""
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'title', 'description', 'date', 'timeline', 
            'actor', 'emotion', 'tags', 'evidence_links'
        ])
        writer.writeheader()
        
        for msg in digest.messages:
            if 'decision' in msg.tags or 'action' in msg.tags:
                writer.writerow({
                    'title': msg.content[:50] + '...',
                    'description': msg.content,
                    'date': msg.timestamp or datetime.now().isoformat(),
                    'timeline': 'Legal',
                    'actor': msg.role.title(),
                    'emotion': 'focused',
                    'tags': ','.join(msg.tags),
                    'evidence_links': ''
                })
```

**Test**:
```bash
chat-digest daily-diary.md --chronicle-export test.csv
# Import test.csv into Chronicle
# Verify events appear on timeline
```

**Time**: 1 hour

---

## 📊 Success Metrics

### Integration Success:
- ✅ Chat conversations auto-import to Chronicle
- ✅ Patterns visible on timeline
- ✅ Contradictions tracked as events
- ✅ Importance scoring preserved
- ✅ Evidence links maintained

### Amuse-bouche Success:
- ✅ 16 months compressed to <10K tokens
- ✅ 95%+ critical information preserved
- ✅ Patterns clearly highlighted
- ✅ Contradictions proven with evidence
- ✅ Aggregate impact quantified
- ✅ Load into any AI instantly

---

## 🎬 Next Steps

**Immediate** (Tonight):
1. Create `chronicle.py` module in chat-digest
2. Implement basic CSV export
3. Test with one conversation
4. Import to Chronicle
5. Verify it works

**This Week**:
1. Add pattern detection events
2. Enhance actor extraction
3. Improve title generation
4. Add evidence file export

**This Month**:
1. Contradiction tracking
2. Amuse-bouche generator
3. Chronicle database query
4. Complete integration

---

## 💡 The Vision Realized

**Before**:
- Chat conversations lost after context window fills
- Manual timeline entry in Chronicle
- Patterns invisible
- Contradictions missed
- No way to "snapshot" 16 months

**After**:
- Daily chats auto-populate Chronicle
- Patterns detected automatically
- Contradictions flagged with evidence
- "Amuse-bouche" snapshot in one command
- Any AI can load complete case context instantly

**"A perfect meal in a bite"** - 16 months of legal case compressed into an exquisite, complete, actionable memory snapshot.

Let's build it! 🚀
