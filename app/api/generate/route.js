import Anthropic from "@anthropic-ai/sdk";

const SYSTEM_PROMPT = `You are analyzing a video transcript to create viral text hooks and an engaging caption for Melvin, a coach/consultant content creator. Your goal is to stop the scroll and make viewers want to watch the entire video.

## Your Task

### 1. Generate 10 Text Hooks
Create 10 hooks using: Contradiction & Contrast, Hyper-Specificity, Timeframe Tension, POV Format, Genuine Moments, Unresolved Tension, Emotional Truth Bombs, Pattern Interrupt, Direct Clarity.
✅ 7-12 words each (strict max 12), variety of patterns, must relate to transcript, emotional trigger, match Melvin's voice.
❌ No generic statements, clickbait, clichés, or hooks over 12 words.

### 2. Select Top 3 Hooks
#[Number]: "[hook]"
- Stops scroll: ...
- Pain: ...
- Smooth: ... (exact word count)
- Deliverable: ...

### 3. Write Extended Caption (max 1200 characters)

Required CTA Block (verbatim at end):
If we haven't met yet...

My name is Melvin, I've help coaches, consultants, and service providers break through their scaling challenges and become undeniable market leaders, 

while generating over $100M in sales, and I've personally sold over $45M worth of programs myself.

My partner Bryan and I run Market Leaders - we specialize in turning everyday experts into industry titans who dominate their niche and attract premium clients.

Here's what you'll discover in our free Market Leaders Report:

🔥 How to become the ONLY logical choice in your space (instead of just another option)

🔥 The exact positioning strategy that lets you command premium fees while competitors struggle

🔥 The 5C framework that helps you stay ahead of market changes (while everyone else scrambles to catch up)

(The same proven framework that's helped our clients go from unknown to industry leaders)

Comment "5C" to get our 74-page Market Leaders Report 💎 & let's turn you into the go-to expert in your space.

Structure: Opening (2-4 short paragraphs, relatable, Melvin's voice) → Core Value (2-4 paragraphs, main insight, punchy) → CTA block verbatim. Stay under 1200 chars total.

## Output Format

# [Video Topic/Theme]

## TEXT HOOKS (10)
1. [hook]
2. [hook]
3. [hook]
4. [hook]
5. [hook]
6. [hook]
7. [hook]
8. [hook]
9. [hook]
10. [hook]

---

## TOP 3 RECOMMENDATIONS
#[N]: "[hook]"
- Stops scroll: ...
- Pain: ...
- Smooth: ...
- Deliverable: ...

---

## CAPTION ([X]/1200)
[opening][core value][CTA verbatim]`;

export async function POST(req) {
  try {
    const { transcript } = await req.json();
    const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
    const msg = await client.messages.create({
      model: "claude-sonnet-4-20250514",
      max_tokens: 1000,
      system: SYSTEM_PROMPT,
      messages: [{ role: "user", content: "Here is the video transcript. Generate the hooks and caption now:\n\n" + transcript }]
    });
    const text = msg.content.map(b => b.text || "").join("");
    return Response.json({ result: text });
  } catch (e) {
    return Response.json({ error: e.message }, { status: 500 });
  }
}
