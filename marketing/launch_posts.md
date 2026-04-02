# K-ZERO Launch Posts — Copy-Paste Ready

## 1. Hacker News (Show HN)

**Title:** Show HN: K-ZERO – Drop 8 geniuses into a room, ask a question, watch them collide

**URL:** https://github.com/ksk5429/kzero

**Text (post as comment immediately after submitting):**

I built a multi-agent debate simulator where Elon Musk, Feynman, Kobe Bryant, Steve Jobs, Sartre, George Carlin, Bryan Johnson, and a Korean PhD student argue about existential questions.

Each agent has ~3,500 tokens of personality data — speech patterns, cognitive biases, memories, and clash dynamics sourced from primary texts (Isaacson bios, autobiographies, philosophical works). They don't impersonate — they inhabit.

Three modes:
- Council Runner: automated simulation with god-mode injection
- K-ZERO Console: YOU are God — type anything, the council reacts
- Dialectic Evolution: Hegelian thesis/antithesis/synthesis/revision per round

It runs on Ollama (free, local, unlimited) or any OpenAI-compatible API (Groq, Gemini, OpenRouter — all free tier).

The output pipeline: simulation -> LLM analysis -> Quarto report (PDF) -> NotebookLM (podcast, quiz, study guide).

The insight that drove this: "The book is the translation layer between swarm intelligence and individual human understanding."

Live demo: https://huggingface.co/spaces/kyeongsun/kzero

---

## 2. Reddit r/LocalLLaMA

**Title:** I built a multi-agent philosophical debate system that runs entirely on Ollama — 8 geniuses argue about the meaning of life on your local machine

**Body:**

What started as a "what if MiroFish but for philosophy" project turned into a full deliberation engine.

**What it does:** Drop 8 AI agents (Musk, Feynman, Kobe, Jobs, Sartre, Carlin, Bryan Johnson, + moderator) into a room. Ask a question. Watch them argue.

**Why it's cool for this sub:**
- Runs 100% on Ollama with llama3 — no cloud, no API keys, no cost
- Each agent has ~3,500 tokens of curated personality (not "be creative" prompts)
- Includes a Hegelian dialectic mode where agents explicitly revise their positions each round
- Run 1000 simulations overnight, get a probability distribution of opinions
- Full Quarto report generation (PDF/HTML) + NotebookLM integration for podcasts

**The K-ZERO Console** lets you play God in real-time:
```
K-ZERO > /inject BREAKING: One of you will be erased from history. Choose who.
K-ZERO > /ask feynman Does Bryan's immortality quest make any sense?
K-ZERO > /mode oxford_debate
K-ZERO > /vote Should humanity pursue immortality?
```

GitHub: https://github.com/ksk5429/kzero
Live demo: https://huggingface.co/spaces/kyeongsun/kzero

MIT licensed. Would love feedback on the voice fidelity — do the agents actually sound like themselves?

---

## 3. Reddit r/artificial

**Title:** Multi-agent swarm intelligence for philosophical deliberation — 8 AI minds debate existential questions using Hegelian dialectic

**Body:**

Built a system where 8 AI agents with distinct philosophical personalities deliberate on questions like "What is the meaning of life?" and "Should humanity pursue immortality?"

The interesting part: agents don't just talk — they EVOLVE through a Hegelian cycle:
1. THESIS: state your position
2. ANTITHESIS: review everyone else, identify the strongest challenge
3. SYNTHESIS: reflect on the tension between your view and the best counter-argument
4. REVISION: produce an updated position

Over multiple rounds, positions genuinely shift. Run it 1000 times and you get a probability distribution that classifies questions as CONVERGENT (has an answer), CONTESTED (real fault lines), or GENUINELY OPEN (no convergence possible).

The core insight: "If a question converges across N runs, it has an answer. If it diverges, it's genuinely open."

GitHub: https://github.com/ksk5429/kzero
Paper-worthy? Thinking about writing this up.

---

## 4. Twitter/X Thread (use the generated thread, plus add these tweets)

**Pre-thread tweet (hook):**
I dropped Elon Musk, Richard Feynman, Kobe Bryant, Steve Jobs, Sartre, George Carlin, and Bryan Johnson into a room.

Then I asked: "What is the point of life?"

Then I played God.

Here's what happened. [thread]

**Post-thread tweet (CTA):**
The whole thing is open source and runs on your laptop via Ollama. Free.

github.com/ksk5429/kzero

Star it if you want to see the 1000-run probability distribution results.

---

## 5. Reddit r/ChatGPT or r/ClaudeAI

**Title:** I built a system where 8 AI agents argue about philosophy — each with 3,500 tokens of curated personality from real books

**Body:**

Not another chatbot wrapper. Each agent is built from primary sources:
- Musk: Isaacson biography (2023)
- Feynman: "Surely You're Joking" 
- Kobe: "The Mamba Mentality"
- Sartre: Being and Nothingness
- Carlin: Brain Droppings

They argue, clash, form alliances, and evolve their positions through a Hegelian dialectic.

The output isn't a chat log — it's a comprehensive report generated via Quarto, which you can feed into NotebookLM to get a podcast about the debate.

Works with any LLM: Ollama (local), Groq (free), Gemini (free).

[link]

---

## 6. LinkedIn Post

I built something unusual this week.

It's called K-ZERO — a multi-agent deliberation system where 8 AI personas (Elon Musk, Richard Feynman, Kobe Bryant, Steve Jobs, Jean-Paul Sartre, George Carlin, Bryan Johnson, and myself as moderator) debate existential questions.

Each agent has ~3,500 tokens of personality data sourced from primary texts. They don't just chat — they go through a Hegelian dialectic cycle: thesis, antithesis, synthesis, revision. Positions genuinely evolve.

The insight that drove this: "The book was always the translation layer between superior and inferior intelligence. Now we can generate that book from swarm intelligence."

The output pipeline: simulation -> analysis -> Quarto report -> NotebookLM podcast.

Open source, runs on free LLMs.

github.com/ksk5429/kzero

#AI #MultiAgent #SwarmIntelligence #Philosophy #OpenSource

---

## 7. Awesome Lists to Submit PRs To

- https://github.com/e2b-dev/awesome-ai-agents — "Awesome AI Agents"
- https://github.com/kyrolabs/awesome-langchain — if we add LangChain compatibility  
- https://github.com/f/awesome-chatgpt-prompts — for the character prompts
- https://github.com/Hannibal046/Awesome-LLM — "Awesome LLM"
- https://github.com/bradAGI/awesome-free-inference — we use free inference

---

## Timing Strategy

**Day 1 (today):**
- Post to HN (Show HN) — best time: 6-8 AM PST (Tuesday-Thursday)
- Post to r/LocalLLaMA — any time, they're always active
- Tweet the thread

**Day 2:**
- Post to r/artificial
- Post to r/ChatGPT
- LinkedIn post

**Day 3:**
- Submit PRs to awesome lists
- If HN took off, do a follow-up blog post

**Key rule:** Don't post to all subreddits the same day. Spread across 2-3 days. Reddit's algorithm penalizes accounts that spam multiple subs simultaneously.
