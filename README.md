```
 ██████╗ ██████╗ ██╗   ██╗███╗   ██╗ ██████╗██╗██╗          ██████╗ ███████╗     █████╗ 
██╔════╝██╔═══██╗██║   ██║████╗  ██║██╔════╝██║██║         ██╔═══██╗██╔════╝    ██╔══██╗
██║     ██║   ██║██║   ██║██╔██╗ ██║██║     ██║██║         ██║   ██║█████╗      ╚█████╔╝
██║     ██║   ██║██║   ██║██║╚██╗██║██║     ██║██║         ██║   ██║██╔══╝      ██╔══██╗
╚██████╗╚██████╔╝╚██████╔╝██║ ╚████║╚██████╗██║███████╗    ╚██████╔╝██║         ╚█████╔╝
 ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝╚═╝╚══════╝     ╚═════╝ ╚═╝          ╚════╝ 
```

### 8 minds. 1 question. Infinite consequences.

---

> Drop 8 of history's greatest minds into a room. Ask a question. Watch them collide.

Musk argues with Sartre about free will. Feynman calls bullshit on Johnson's immortality quest. Kobe tells everyone to stop philosophizing and just *do*. Carlin laughs at all of them. And you? You're the one pulling the strings.

---

![Python](https://img.shields.io/badge/python-3.11+-blue?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Cost](https://img.shields.io/badge/cost-%240-brightgreen?style=flat-square)
[![Open in Kaggle](https://kaggle.com/static/images/open-in-kaggle.svg)](https://kaggle.com/)
![Stars](https://img.shields.io/github/stars/ksk5429/kzero?style=flat-square)

<!-- TODO: Add demo GIF -->

---

## What is this?

A multi-agent deliberation system where 8 AI personas — built from ~3,500 tokens of researched personality data each — argue existential questions using **any free OpenAI-compatible LLM**.

No paid API keys. No cloud dependencies. Just pure intellectual chaos.

## Features

- **K-ZERO Console** — Interactive god-mode. Inject variables mid-debate. Whisper to individual agents. Watch consequences ripple through the group.
- **8 deeply researched personas** — Not "be creative" prompts. Real cognitive biases, speech patterns, memory seeds, and clash dynamics sourced from primary texts.
- **Any free LLM API** — Groq, OpenRouter, Google AI Studio. Pick one, plug it in, run.
- **Post-simulation analysis** — LLM-powered transcript analysis extracts agreement maps, position tracking, emergent insights, and topic clusters.
- **Interactive Dash dashboard** — Network graphs, conflict heatmaps, position timelines, and key quotes. All in Plotly.
- **3 pre-built scenarios** — Meaning of life, AI alignment, death and legacy. Or write your own.
- **Shareable transcripts** — Every session saves to JSON. Replay, analyze, share.

---

## Quick Start

**1. Clone**

```bash
git clone https://github.com/ksk5429/kzero.git
cd kzero
```

**2. Install**

```bash
pip install -r requirements.txt
```

**3. Set your free API key**

Create a `.env` file:

```env
# Pick ONE. All are free, no credit card needed.
# --- Groq (recommended, fastest) ---
LLM_API_KEY=gsk_your_groq_key
LLM_BASE_URL=https://api.groq.com/openai/v1
COUNCIL_MODEL=llama-3.3-70b-versatile

# --- OpenRouter (most models) ---
# LLM_API_KEY=sk-or-your_key
# LLM_BASE_URL=https://openrouter.ai/api/v1
# COUNCIL_MODEL=meta-llama/llama-3.3-70b-instruct:free

# --- Google AI Studio (Gemini) ---
# LLM_API_KEY=your_google_key
# LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
# COUNCIL_MODEL=gemini-2.5-flash
```

**4. Run**

```bash
# Automated deliberation — sit back and watch
python -m runner.council_runner --scenario scenarios/scenario_01_meaning_of_life.json

# K-ZERO Console — you play god
python -m runner.demiurge --scenario scenarios/scenario_01_meaning_of_life.json
```

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

---

## K-ZERO Console

You are the demiurge. The council exists because you willed it.

```
K-ZERO > /all What is worth dying for?
```

Watch 8 agents respond in character, building on each other's arguments.

```
K-ZERO > /inject BREAKING: A message from the future confirms no one 
         will remember any of you in 200 years.
```

Watch the shockwave. Musk doubles down. Sartre shrugs. Kobe doesn't care. Carlin saw it coming.

```
K-ZERO > /ask feynman Does Bryan's immortality quest contradict everything 
         you believe about curiosity?
```

Pull one thread. Watch the whole tapestry shift.

### All Commands

| Command | What it does |
|---------|-------------|
| `/all <question>` | Pose a question — all 8 agents respond |
| `/ask <name> <text>` | Whisper to one agent directly |
| `/inject <text>` | God-mode variable injection — mid-debate plot twist |
| `/next` | Let the next round play out naturally |
| `/next <N>` | Run N rounds without intervention |
| `/who` | Show all members and their current stance |
| `/history` | Show recent transcript |
| `/synthesis` | Kevin synthesizes the discussion so far |
| `/end` | End session and save transcript |

---

## Visualization

After a simulation, run the analyzer and dashboard:

```bash
# Analyze the transcript
python -m runner.analyze transcripts/meaning_of_life_20260402.json

# Launch the interactive Dash dashboard
python -m runner.visualize analysis_result.json
```

The dashboard shows:

- **Network graph** — Who agrees with whom, weighted by interaction strength
- **Conflict heatmap** — Pairwise agreement/disagreement intensity
- **Position timeline** — How each agent's stance evolves across rounds
- **Key quotes** — Most impactful moments, auto-extracted
- **Emergent insights** — Ideas that no individual agent proposed, but the group produced

---

## Architecture

```
the_council/
├── runner/
│   ├── council_runner.py      # Automated deliberation engine
│   ├── demiurge.py            # K-ZERO Console (interactive god-mode)
│   ├── agent.py               # Agent class + LLM integration
│   ├── analyze.py             # Post-simulation transcript analysis
│   ├── visualize.py           # Plotly Dash dashboard
│   └── validate.py            # Character data validation
├── characters/
│   ├── musk/                  # ~3,500 tokens of personality data
│   │   ├── personality_matrix.json
│   │   ├── voice.md           # Speech patterns for system prompts
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
│   └── simulation_config.json
├── transcripts/               # Auto-saved session transcripts
├── profiles/
│   └── council_profiles.json
├── requirements.txt
└── .env                       # Your API key (not committed)
```

---

## How It Works

```
Character Data ──→ System Prompt ──→ LLM Call ──→ Transcript
     │                                              │
  voice.md                                    saved as JSON
  axioms.md                                         │
  clash_points.md                                   ▼
  memory_seeds.md                  Analyzer (LLM-powered) ──→ Dash Dashboard
  personality_matrix.json            agreement maps             network graph
                                     position tracking          heatmap
                                     emergent insights          timeline
```

Each agent's system prompt is assembled from ~3,500 tokens of character data: speech patterns, core beliefs, interaction dynamics, and formative memories. The LLM doesn't improvise a personality — it inhabits one.

---

## Scenarios

| # | Scenario | The Question | Spiciest Tension |
|---|----------|-------------|-----------------|
| 1 | **Meaning of Life** | What is the point of life? | Musk (extend consciousness) vs Carlin (failed experiment) |
| 2 | **AI Alignment** | Should we build god? | Musk (build it) vs Sartre (existential threat to freedom) |
| 3 | **Death and Legacy** | What survives us? | Johnson (don't die) vs Kobe (legacy through craft) |

Want a custom scenario? Create a JSON file:

```json
{
  "id": "your_scenario",
  "title": "Your Question",
  "opening_prompt": "The council is gathered to deliberate on...",
  "moderator_prompts": ["Kevin asks: ..."],
  "god_mode_injection": {
    "mid_discussion": "BREAKING: ...",
    "late_discussion": "BREAKING: ..."
  }
}
```

---

## Add Your Own Council

Each character is a folder under `characters/` with 5 files:

1. **`personality_matrix.json`** — Cognitive biases, knowledge domains, interaction weights
2. **`voice.md`** — How they talk. Sentence structure, vocabulary, verbal tics
3. **`axioms.md`** — 10 non-negotiable beliefs
4. **`clash_points.md`** — How they react to every other member
5. **`memory_seeds.md`** — Formative experiences the LLM can reference

Use primary sources. Biographies, interviews, their own writing. The richer the data, the more the agent sounds like *them* instead of a chatbot cosplaying.

---

## Free API Providers

No credit card needed. Seriously.

| Provider | Free Tier | Best Model | Signup |
|----------|-----------|-----------|--------|
| **Groq** | Very generous free tier | `llama-3.3-70b-versatile` | [console.groq.com](https://console.groq.com) |
| **OpenRouter** | Free models available | `meta-llama/llama-3.3-70b-instruct:free` | [openrouter.ai](https://openrouter.ai) |
| **Google AI Studio** | Free tier | `gemini-2.0-flash` | [aistudio.google.com](https://aistudio.google.com) |

---

## Contributing

1. Fork the repo
2. Create a branch (`git checkout -b feat/nietzsche-agent`)
3. Add your character, scenario, or feature
4. Test it runs with at least one free API
5. Open a PR

Character contributions are especially welcome. The world needs a council with Nietzsche, Ada Lovelace, or Marcus Aurelius in it.

---

## License

MIT. Do whatever you want. Build your own council. Ask your own questions. Break reality.

---

<p align="center">
<i>"The unexamined life is not worth living." — Socrates<br>
"Examine it with 8 agents and a free API." — K-ZERO</i>
</p>
