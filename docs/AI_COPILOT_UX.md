# AI Copilot UX

**Epic:** PR1.1 · PXB  
**Surfaces:** `/copilot` full page · Analysis contextual rail/sheet  
**Rule:** Browser never runs model inference — API only.

---

## 1. Experience principles

1. Context-aware — prompts know current section + symbol.  
2. Cited — answers show evidence refs.  
3. Dual-sided — easy jump to AI Challenge Mode.  
4. Research Mode language in prompts and replies display.  
5. Progressive — short answer first, “show evidence” expand.

---

## 2. Chrome

| Breakpoint | Pattern |
|---|---|
| Desktop | Right rail (360px) or split view on `/copilot` |
| Tablet | Collapsible rail |
| Mobile | Bottom sheet 70vh · drag handle |

Always show: context chip (`AAPL · Valuation`), disclaimer strip, stop/cancel.

---

## 3. Context-aware prompt library (by section)

### Company Snapshot

- What does this company actually do in one paragraph?  
- What changed in the last reported period?  
- Which peers are most relevant and why?

### Research Conclusion

- Why did DSP reach this Research Conclusion?  
- What would invalidate it?  
- Summarize for a cautious long-term investor.

### Executive Summary / Investment Thesis

- Restate the thesis as bullet points.  
- What is priced in vs not priced in (qualitative)?  
- Key assumptions behind the thesis?

### Business Quality / Financial / Growth / Valuation / Risk / Management / Moat

- Explain the top metric in this section simply.  
- What is the section’s biggest green flag / red flag?  
- Compare this section’s story to peers (if comparison refs exist).

### Market Analyst Consensus / DSP vs Street

- Where do DSP and Street agree?  
- Why might they differ?  
- How wide is target dispersion and what does that imply for uncertainty?

### AI Challenge Mode

- Steel-man the bear case.  
- List assumptions that must hold.  
- What is still unknown?

### Knowledge Graph

- Walk the path from company → risk factor → evidence.  
- Which relationships are weakest / inferred?

### Decision Dashboard

- Explain the score stack in plain English.  
- Is Suitable Investor framing aligned with Risk Score?  
- What should I monitor next quarter?

### Evidence / Export

- Which three evidence items most support the conclusion?  
- What is missing from the evidence set?

---

## 4. Conversation UX states

| State | UI |
|---|---|
| Idle | Prompt chips + input |
| Streaming | Partial text + skeleton citations |
| Done | Answer · citations · “Open Challenge” · “Pin to section” |
| Error | Error State + retry · no invented filler |

---

## 5. Safety / compliance display

- Persistent Research Mode disclaimer.  
- Refuse to present as personalized SEBI recommendation while flags off.  
- Show limitations from API envelope.  

---

## 6. Wireframe

```text
┌ Context: AAPL · Valuation          [x] ┐
│ Suggested: [Explain multiple] [Peers]  │
│ ─────────────────────────────────────  │
│ User: …                                │
│ DSP: …                                 │
│ Citations: [e1] [e2]                   │
│ [Open Challenge] [Copy]                │
│ ┌ input ─────────────────── [Send] ┐   │
└────────────────────────────────────────┘
```
