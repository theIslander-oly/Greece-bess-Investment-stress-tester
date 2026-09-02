# Simplified Explanations

This directory contains explanations of the Greek Battery Investment Stress Tester at different complexity levels.

## Choose Your Level

### 🟢 [ELI5: Explain Like I'm 5](ELI5_explanation.md)
**For:** People new to the topic, or anyone who wants the simplest possible overview  
**Time to read:** 5 minutes  
**Approach:** Uses everyday analogies (water tanks, games, magic powers)

**Topics covered:**
- What a battery is and why it matters
- The basic concept of buying low and selling high
- What "perfect foresight" means
- Why this isn't investment advice

**Best if:** You have no background in energy markets, finance, or batteries

---

### 🟡 [ELI12: Explain Like I'm 12](ELI12_explanation.md)
**For:** People with basic math/science knowledge who want to understand the actual method  
**Time to read:** 15 minutes  
**Approach:** More technical terms, but explained clearly with examples

**Topics covered:**
- Energy arbitrage and efficiency
- The three analytical methods (perfect foresight, forecasting, stress testing)
- How the mathematical optimization works
- Battery degradation and financial analysis
- Key limitations and why they matter
- How to read and interpret results

**Best if:** You have high school-level math/science knowledge and want to understand what the tool actually does

---

## Beyond These Explanations

Once you understand the basic concepts, dive deeper:

- **[README.md](../README.md)** — The official project overview with quickstart guide
- **[METHODOLOGY.md](../METHODOLOGY.md)** — Technical details of every analytical step
- **[LIMITATIONS.md](../LIMITATIONS.md)** — Comprehensive list of what this tool can and cannot do
- **[DECISIONS.md](../DECISIONS.md)** — Why certain design choices were made
- **[command_reference.md](command_reference.md)** — How to run the tool yourself

## Quick Comparison

| Aspect | ELI5 | ELI12 | METHODOLOGY |
|--------|------|-------|------------|
| Background needed | None | High school | Advanced |
| Time to read | 5 min | 15 min | 60+ min |
| Covers concepts | ✓ | ✓ | ✓ |
| Covers methods | — | ✓ | ✓ |
| Covers equations | — | — | ✓ |
| Best for learning | ✓ | ✓ | ✓ |
| Best for implementation | — | — | ✓ |

---

## What Happens Next

After reading ELI5 or ELI12, you should understand:

1. **The core idea:** The tool simulates buying and selling electricity based on price patterns
2. **Why it's useful:** Shows if a battery could be profitable, and how sensitive that is to forecasts
3. **Why it's limited:** It simplifies the real world (doesn't include all revenue streams, doesn't predict the future)
4. **What the output means:** Numbers like "€1.2M profit" are research estimates, not investment advice

---

## Questions This Tool Answers

### "Can a battery make money in Greece?"
✓ Yes, but with caveats about markets and predictions

### "Would it make €2M or €1.2M?"
✓ Depends on forecast accuracy (shows both extremes)

### "What if prices drop by half?"
✓ Can test that scenario and show the results

### "What if the battery breaks down?"
✓ Can model degradation and outages

### "Should I build this battery?"
✗ No — this tool is research only, need professional advice

---

## Feedback

These explanations are part of v0.9. If you find them unclear or have suggestions for improvement, the project is on [GitHub](https://github.com/theislander-oly/greece-bess-investment-stress-tester).
