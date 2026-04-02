---
title: K-ZERO Council of 8
emoji: "🎯"
colorFrom: red
colorTo: purple
sdk: docker
app_port: 7860
pinned: true
license: mit
short_description: "8 minds. 1 question. Infinite consequences."
---

```
 ██████╗ ██████╗ ██╗   ██╗███╗   ██╗ ██████╗██╗██╗          ██████╗ ███████╗     █████╗ 
██╔════╝██╔═══██╗██║   ██║████╗  ██║██╔════╝██║██║         ██╔═══██╗██╔════╝    ██╔══██╗
██║     ██║   ██║██║   ██║██╔██╗ ██║██║     ██║██║         ██║   ██║█████╗      ╚█████╔╝
██║     ██║   ██║██║   ██║██║╚██╗██║██║     ██║██║         ██║   ██║██╔══╝      ██╔══██╗
╚██████╗╚██████╔╝╚██████╔╝██║ ╚████║╚██████╗██║███████╗    ╚██████╔╝██║         ╚█████╔╝
 ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝╚═╝╚══════╝     ╚═════╝ ╚═╝          ╚════╝ 
```

### 8 minds. 1 question. Infinite consequences.

> Drop 8 of history's greatest minds into a room. Ask a question. Watch them collide. Then turn their collision into a book, a podcast, a probability distribution, and a Twitter thread.

![Python](https://img.shields.io/badge/python-3.11+-blue?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Cost](https://img.shields.io/badge/cost-%240-brightgreen?style=flat-square)
![Stars](https://img.shields.io/github/stars/ksk5429/kzero?style=flat-square)
[![Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97-Live%20Demo-yellow?style=flat-square)](https://huggingface.co/spaces/kyeongsun/kzero)

---

## Live Demo

**[https://kyeongsun-kzero.hf.space](https://huggingface.co/spaces/kyeongsun/kzero)** — no install, no API key, just go.

---

## Try It Now

| Method | Link | What You Get |
|--------|------|-------------|
| **Live Demo** | [kyeongsun-kzero.hf.space](https://huggingface.co/spaces/kyeongsun/kzero) | Interactive dashboard, zero setup |
| **Kaggle** | [Open in Kaggle](https://kaggle.com/) | Full simulation in your browser |
| **Local** | See Quick Start below | All 3 modes + full pipeline + god-mode |

---

## Quick Start

```bash
git clone https://github.com/ksk5429/kzero.git && cd kzero
pip install -r requirements.txt
```

Get a free API key from [console.groq.com](https://console.groq.com) or [ai.google.dev](https://aistudio.google.com/apikey) (no credit card), then:

```bash
# Create .env with your free key
echo 'LLM_API_KEY=your_key_here' > .env
echo 'LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/' >> .env
echo 'COUNCIL_MODEL=gemini-2.5-flash' >> .env
```

Three ways to run:

```bash
# 1. Council Runner — automated multi-agent deliberation
python -m runner.council_runner --rounds 5

# 2. K-ZERO Console — YOU are God, the council obeys
python -m runner.demiurge

# 3. Dialectic Evolution — Hegelian thesis/antithesis/synthesis
python -m runner.dialectic "Should humanity pursue immortality?" --rounds 5
```

---

## The Pipeline

One question in. Seven artifacts out.

```
  QUESTION
     |
     v
 +-----------+    +-----------+    +----------+    +----------+    +------------+
 | Simulate  | -> | Analyze   | -> | Report   | -> | Artifacts| -> | Distribute |
 | 8 agents  |    | LLM parse |    | Quarto   |    | NbookLM  |    | X thread   |
 | N rounds  |    | positions |    | HTML/PDF |    | podcast  |    | 280 chars  |
 +-----------+    +-----------+    +----------+    +----------+    +------------+
      |                |                |               |                |
  transcript.json  analysis.json   report.pdf     flashcards       thread.md
                                                  study guide
                                                  quiz, slides
                                                  mind map
                                                  briefing doc
```

```bash
# Full pipeline, start to finish
python -m runner.council_runner --rounds 5                          # Simulate
python -m runner.analyze transcripts/session_*.json                 # Analyze
python -m runner.predict "Is AI the next stage of evolution?" --runs 10  # Predict
python -m runner.report predictions/session_*.json --format all     # Report
python -m runner.artifacts reports/session_*.pdf --all              # Artifacts
python -m runner.thread transcripts/session_*.json                  # Twitter thread
python -m runner.visualize transcripts/session_*_analysis.json      # Dashboard
```

---

## Simulation Modes

Three engines, three philosophies.

### 1. Council Runner

Natural multi-agent conversation with god-mode injection. Set a scenario, choose a discussion mode, and let 8 agents argue while you inject plot twists mid-session.

```bash
python -m runner.council_runner --scenario scenarios/scenario_01_meaning_of_life.json --rounds 5
```

### 2. K-ZERO Console

Interactive REPL. You are the demiurge. Type anything and the council reacts. Whisper to one agent. Inject breaking news. Force a vote. Pull one thread and watch the whole tapestry shift.

```bash
python -m runner.demiurge --scenario scenarios/scenario_02_ai_alignment.json
```

### 3. Dialectic Evolution

Hegelian algorithm. No free-form conversation — each round follows a strict protocol:

```
THESIS      Agent states their position
     |
ANTITHESIS  Agent reviews ALL other positions, identifies challenges
     |
SYNTHESIS   Agent integrates what challenged them most
     |
REVISION    Agent produces a revised position (may shift, may hold)
```

Over N rounds, positions genuinely evolve. The output is not a transcript but a **thought evolution map** — showing how each mind changed and why.

```bash
python -m runner.dialectic "What is consciousness?" --rounds 5 --agents 4
```

---

## Discussion Modes

Every simulation can run in any of 8 modes. Switch mid-session with `/mode <name>`.

| Mode | Emoji | What Happens |
|------|-------|-------------|
| `philosophical_seminar` | :books: | Open exploration, Socratic depth, no winners |
| `oxford_debate` | :crossed_swords: | Formal adversarial debate, proposition vs opposition |
| `yes_no_vote` | :ballot_box_with_ballot: | Council votes YES or NO, majority wins |
| `multiple_choice` | :bar_chart: | Council picks from options, ranked results |
| `brainstorm` | :bulb: | No criticism allowed, pure ideation, wild ideas welcomed |
| `war_room` | :military_helmet: | Crisis scenario, time pressure, decisive action required |
| `socratic_dialogue` | :thinking: | Question-driven inquiry, no assertions, only questions |
| `delphi_method` | :crystal_ball: | Anonymous rounds, convergence tracking, expert consensus |

---

## The Council

| | Name | Role | MBTI | One-liner |
|---|------|------|------|-----------|
| :red_circle: | **Elon Musk** | The Builder | INTJ | "Consciousness must become multi-planetary or it dies." |
| :large_blue_circle: | **Richard Feynman** | The Curious One | ENTP | "I'd rather have questions that can't be answered than answers that can't be questioned." |
| :yellow_circle: | **Kobe Bryant** | Mamba Mentality | ENTJ | "Rest at the end, not in the middle." |
| :white_circle: | **Steve Jobs** | The Curator | ENTJ | "Real artists ship." |
| :purple_circle: | **Jean-Paul Sartre** | The Existentialist | INFJ | "Man is condemned to be free." |
| :green_circle: | **George Carlin** | The Satirist | INTP | "Think of how stupid the average person is. Half of them are stupider than that." |
| :diamond_shape_with_a_dot_inside: | **Bryan Johnson** | The Extreme Optimizer | INTJ | "Don't die." |
| :white_large_square: | **Kevin Kim** | The Moderator | INTJ | "The question behind the question is the real question." |

### Natural Alliances & Tensions

```
    MUSK ←——0.7——→ JOBS          Feynman ←—0.65—→ Carlin
      ↕                              ↕
   (0.6)                          (0.7) tension
      ↕                              ↕
    KOBE              SARTRE ←——0.65——→ KOBE
      ↕                              
   (0.5)             CARLIN ←—0.75—→ JOHNSON
      ↕
   JOHNSON           MUSK  ←——0.8——→ JOHNSON
```

Each persona is built from ~3,500 tokens of researched personality data — speech patterns, core axioms, clash dynamics, and formative memories sourced from primary texts. The LLM doesn't improvise a personality. It inhabits one.

---

## K-ZERO Console

You are the demiurge. The council exists because you willed it.

```
K-ZERO > What if humans could upload their consciousness to the cloud?
         (type anything — the council reacts)

K-ZERO > /ask feynman Does Bryan's immortality quest make any sense?
         (whisper to one agent)

K-ZERO > /inject BREAKING: A message from the future confirms no one
         will remember any of you in 200 years.
         (watch the shockwave)

K-ZERO > /mode war_room
         (switch to crisis mode)

K-ZERO > /vote Should humanity pursue immortality?
         (force YES/NO vote)

K-ZERO > /end
         (save transcript, get synthesis, exit)
```

### All Commands

| Command | What it does |
|---------|-------------|
| `(any text)` | Pose a question — all 8 agents respond |
| `/all <question>` | Same as above, explicit |
| `/ask <name> <text>` | Whisper to one agent directly |
| `/inject <text>` | God-mode variable injection — mid-debate plot twist |
| `/next` | Let the next round play out naturally |
| `/next <N>` | Run N rounds without intervention |
| `/mode <name>` | Switch discussion mode (see 8 modes above) |
| `/vote <question>` | Force YES/NO vote |
| `/who` | Show all members and their current stance |
| `/history` | Show recent transcript |
| `/synthesis` | Kevin synthesizes the discussion so far |
| `/end` | End session and save transcript |

---

## Dialectic Evolution

The Hegelian engine doesn't produce conversations. It produces **evolution maps**.

```bash
python -m runner.dialectic "Is free will an illusion?" --rounds 5
```

Each agent goes through 4 phases per round. Over 5 rounds, that's 20 introspective steps per agent. Positions genuinely shift. Alliances form and break. The output tracks:

- **Position trajectory** — Where each agent started vs where they ended
- **Key shifts** — The exact moment an argument changed someone's mind
- **Convergence score** — Did the council find common ground, or split further apart?
- **Strongest argument** — Which thesis survived the most scrutiny?

---

## Prediction Engine

Run the same question N times. If answers converge, it has an answer. If they diverge, it's genuinely open.

```bash
python -m runner.predict "Should humanity pursue immortality?" --runs 10 --rounds 3
```

Outputs:
- **Probability distribution** — What percentage of runs reached each conclusion
- **Convergence metric** — How stable is the answer across runs?
- **Minority reports** — The strongest dissenting positions
- **Confidence interval** — How much to trust the majority

The distribution reveals what no single run can: whether the question has a center of gravity or is fundamentally contested.

---

## Report Generation

Turn simulation results into polished Quarto reports — the translation layer between swarm intelligence and human understanding.

```bash
python -m runner.report predictions/immortality_20260402.json --format html
python -m runner.report predictions/immortality_20260402.json --format pdf
python -m runner.report predictions/immortality_20260402.json --format all   # HTML + PDF + DOCX
```

Reports include:
- Executive summary (LLM-generated)
- Position evolution charts (Plotly)
- Agreement/conflict maps
- Prediction distributions
- K-ZERO's divine recommendation

---

## NotebookLM Artifacts

The report is the seed. NotebookLM is the multiplier. One question becomes seven learning materials.

```bash
python -m runner.artifacts reports/immortality_20260402.pdf --all
```

| Artifact | What You Get |
|----------|-------------|
| `--podcast` | Audio Overview — two hosts discussing the council's deliberation |
| `--study-guide` | Structured study guide with key concepts and takeaways |
| `--quiz` | Multiple-choice quiz to test comprehension |
| `--flashcards` | Spaced-repetition flashcards for key arguments |
| `--slides` | Slide deck summarizing the deliberation |
| `--mind-map` | Visual mind map of connected ideas |
| `--briefing` | Executive briefing document |
| `--all` | Generate everything |

---

## Visualization

Interactive Plotly Dash dashboard showing everything that happened.

```bash
python -m runner.analyze transcripts/session_20260402.json
python -m runner.visualize transcripts/session_20260402_analysis.json
# Opens at http://localhost:8050
```

The dashboard shows:
- **Network graph** — Who agrees with whom, weighted by interaction strength
- **Conflict heatmap** — Pairwise agreement/disagreement intensity
- **Position timeline** — How each agent's stance evolves across rounds
- **Key quotes** — Most impactful moments, auto-extracted
- **Emergent insights** — Ideas no individual proposed, but the group produced
- **Chat log panel** — Full transcript with agent colors and round markers

---

## Architecture

14 Python modules. ~6,000 lines. Zero fluff.

```
the_council/
├── runner/
│   ├── agent.py               # Agent class, OpenAI-compatible, 4-key rotation
│   ├── council_runner.py      # Mode-aware automated simulation engine
│   ├── demiurge.py            # K-ZERO Console (interactive god-mode REPL)
│   ├── dialectic.py           # Hegelian dialectic evolution engine
│   ├── modes.py               # 8 discussion modes + voting engine
│   ├── evolution.py           # Opinion tracking + convergence/divergence detection
│   ├── predict.py             # Multi-run aggregation + probability distribution
│   ├── analyze.py             # LLM transcript analysis + JSON repair
│   ├── visualize.py           # Plotly Dash dashboard with chat log panel
│   ├── report.py              # Quarto report generator (HTML, PDF, DOCX)
│   ├── artifacts.py           # NotebookLM artifact pipeline
│   ├── thread.py              # Twitter/X thread generator
│   ├── validate.py            # Data integrity checker
│   └── __init__.py
├── characters/
│   ├── musk/                  # ~3,500 tokens of personality data each
│   │   ├── personality_matrix.json
│   │   ├── voice.md           # Speech patterns
│   │   ├── axioms.md          # 10 core beliefs
│   │   ├── clash_points.md    # Dynamics with every other member
│   │   └── memory_seeds.md    # Key life experiences
│   ├── feynman/
│   ├── kobe/
│   ├── jobs/
│   ├── sartre/
│   ├── carlin/
│   ├── johnson/
│   └── kevin/
├── scenarios/
│   ├── scenario_01_meaning_of_life.json
│   ├── scenario_02_ai_alignment.json
│   └── scenario_03_death_and_legacy.json
├── config/
│   └── discussion_modes.json  # 8 mode definitions
├── transcripts/               # Auto-saved session transcripts (JSON)
├── predictions/               # Multi-run prediction results
├── reports/                   # Generated Quarto reports
├── visualizations/            # Exported dashboard assets
├── dialectics/                # Dialectic evolution outputs
├── profiles/
│   └── council_profiles.json
├── requirements.txt
├── pyproject.toml
├── Dockerfile                 # HF Spaces deployment
├── app.py                     # Gradio app for HF Spaces
└── .env                       # Your API key (not committed)
```

---

## Free LLM Providers

No credit card needed. Seriously.

| Provider | Free Tier | Best Model | Signup |
|----------|-----------|-----------|--------|
| **Ollama** | Unlimited, local, free forever | `llama3.3:70b`, `qwen2.5:32b` | [ollama.com](https://ollama.com) |
| **Google AI Studio** | Generous free tier | `gemini-2.5-flash` | [aistudio.google.com](https://aistudio.google.com) |
| **Groq** | Very generous free tier | `llama-3.3-70b-versatile` | [console.groq.com](https://console.groq.com) |
| **OpenRouter** | Free models available | `meta-llama/llama-3.3-70b-instruct:free` | [openrouter.ai](https://openrouter.ai) |

```env
# Ollama (local, unlimited, recommended for heavy use)
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
COUNCIL_MODEL=llama3.3:70b

# Google AI Studio
LLM_API_KEY=your_google_key
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
COUNCIL_MODEL=gemini-2.5-flash

# Groq (fastest inference)
LLM_API_KEY=gsk_your_groq_key
LLM_BASE_URL=https://api.groq.com/openai/v1
COUNCIL_MODEL=llama-3.3-70b-versatile

# OpenRouter (most model variety)
LLM_API_KEY=sk-or-your_key
LLM_BASE_URL=https://openrouter.ai/api/v1
COUNCIL_MODEL=meta-llama/llama-3.3-70b-instruct:free
```

---

## Add Your Own Council

Each character is a folder under `characters/` with 5 files:

| File | Purpose |
|------|---------|
| `personality_matrix.json` | Cognitive biases, knowledge domains, interaction weights |
| `voice.md` | How they talk — sentence structure, vocabulary, verbal tics |
| `axioms.md` | 10 non-negotiable beliefs |
| `clash_points.md` | How they react to every other member |
| `memory_seeds.md` | Formative experiences the LLM can reference |

Use primary sources. Biographies, interviews, their own writing. The richer the data, the more the agent sounds like *them* instead of a chatbot cosplaying.

```bash
mkdir characters/nietzsche
# Create the 5 files above
# The system auto-discovers new character folders
```

---

## Philosophy

> "The book is the translation layer between swarm intelligence and individual human understanding."

K-ZERO doesn't answer questions. It generates **thought landscapes** — showing where 8 brilliant minds agree, where they clash, and where none of them have been yet.

The pipeline turns that landscape into something you can read, listen to, quiz yourself on, and share. One question becomes a book, a podcast, a probability distribution, and a Twitter thread.

The question was never "What is the answer?"

The question was always "What does the answer look like from 8 directions at once?"

---

## Contributing

1. Fork the repo
2. Create a branch (`git checkout -b feat/nietzsche-agent`)
3. Add your character, scenario, mode, or feature
4. Test it runs with at least one free API
5. Open a PR

Character contributions are especially welcome. The world needs a council with Nietzsche, Ada Lovelace, Marcus Aurelius, or Frida Kahlo in it.

---

## License

MIT. Do whatever you want. Build your own council. Ask your own questions. Break reality.

---

<p align="center">
<i>"The unexamined life is not worth living." — Socrates<br>
"Examine it with 8 agents, a Hegelian dialectic, and a free API." — K-ZERO</i>
</p>
