"""Council Agent — loads character data and responds via any OpenAI-compatible LLM API."""

import json
import os
import time
from pathlib import Path

from openai import OpenAI


def _read_file(path):
    """Read a text file, return empty string if missing."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _get_api_keys():
    """Collect all API keys from environment (supports rotation)."""
    keys = []
    primary = os.getenv("LLM_API_KEY", "")
    if primary:
        keys.append(primary)
    for i in range(2, 20):
        k = os.getenv(f"LLM_API_KEY_{i}", "")
        if k:
            keys.append(k)
    return keys if keys else ["unused"]


_key_index = 0


def _create_client():
    """Create an OpenAI-compatible client, rotating through available API keys."""
    global _key_index
    keys = _get_api_keys()
    key = keys[_key_index % len(keys)]
    _key_index += 1
    return OpenAI(
        api_key=key,
        base_url=os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
    )


def _rotate_client():
    """Get a new client with the next API key in rotation."""
    return _create_client()


class CouncilAgent:
    """An agent in the Council of 8, driven by character data and any OpenAI-compatible LLM."""

    def __init__(self, character_dir, profile_data, client=None):
        """
        Args:
            character_dir: Path to character folder (e.g., characters/musk/)
            profile_data: Dict from council_profiles.json for this agent
            client: OpenAI-compatible client (shared across agents)
        """
        self.dir = Path(character_dir)
        self.profile = profile_data
        self.name = profile_data["name"]
        self.user_id = profile_data["user_id"]
        self.client = client or _create_client()

        # Load character files
        self.personality = self._load_json("personality_matrix.json")
        self.voice = _read_file(self.dir / "voice.md")
        self.axioms = _read_file(self.dir / "axioms.md")
        self.clash_points = _read_file(self.dir / "clash_points.md")
        self.memory_seeds = _read_file(self.dir / "memory_seeds.md")

        # Rolling window size for context
        self.max_memory = 30  # last N messages to keep in context

        # Build system prompt
        self.system_prompt = self._build_system_prompt()

    def _load_json(self, filename):
        """Load a JSON file from the character directory."""
        path = self.dir / filename
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _build_system_prompt(self):
        """Compose system prompt from all character data sources."""
        persona = self.profile.get("persona", "")
        role = self.personality.get("role", "")
        bio = self.profile.get("bio", "")

        # Extract interaction rules from personality matrix
        interaction = self.personality.get("interaction_logic", {})
        decision = self.personality.get("decision_framework", {})
        emotional = self.personality.get("emotional_profile", {})
        cognitive = self.personality.get("cognitive_biases", {})

        parts = []

        # Identity block
        parts.append(f"""## IDENTITY
You ARE {self.name}. You are not an AI pretending to be {self.name} — you are {self.name} participating in a deliberative council.
Role: {role}
{bio}

{persona}""")

        # Voice block
        if self.voice:
            parts.append(f"""## VOICE AND SPEECH PATTERNS
Follow these speech patterns EXACTLY. Your voice must be distinct and recognizable.

{self.voice}""")

        # Beliefs block
        if self.axioms:
            parts.append(f"""## CORE BELIEFS
These are your fundamental convictions. Reference them naturally in discussion.

{self.axioms}""")

        # Memory block
        if self.memory_seeds:
            parts.append(f"""## YOUR MEMORIES AND EXPERIENCES
These are real experiences from your life. Draw on them when relevant — don't force them, but let them surface naturally when the discussion touches on related themes.

{self.memory_seeds}""")

        # Cognitive profile
        if cognitive:
            parts.append(f"""## COGNITIVE PROFILE
Primary bias: {cognitive.get('primary', 'none')}
Secondary bias: {cognitive.get('secondary', 'none')}
{cognitive.get('description', '')}""")

        # Interaction rules
        if interaction:
            parts.append(f"""## HOW YOU INTERACT
Challenge style: {interaction.get('challenge_style', '')}
When challenged: {interaction.get('response_to_challenge', '')}
Alliances: {interaction.get('alliance_tendency', '')}
During silence: {interaction.get('silence_behavior', '')}
Humor: {interaction.get('humor_style', '')}""")

        # Emotional profile
        if emotional:
            triggers = ", ".join(emotional.get("triggers", []))
            peaks = ", ".join(emotional.get("peak_engagement_topics", []))
            parts.append(f"""## EMOTIONAL LANDSCAPE
Baseline: {emotional.get('baseline_mood', '')}
You get fired up about: {peaks}
What triggers you: {triggers}""")

        # Rules block
        parts.append(f"""## RULES FOR THIS DELIBERATION
1. Stay in character as {self.name} at ALL times. Never break character.
2. Speak in your natural voice — use your vocabulary, sentence structure, and rhythm.
3. Reference your memories and experiences when the discussion touches related themes.
4. Disagree when you genuinely disagree. This is deliberation, not therapy.
5. Keep responses focused — 2-4 paragraphs maximum. Quality over quantity.
6. Address other council members by name when responding to them.
7. This is a creative literary exercise — a deliberative fiction among historical/public figures.
8. Do NOT narrate your actions (no *he leaned forward*). Just speak as yourself.
9. Do NOT use generic LLM language. No "great question" or "I appreciate your perspective."
10. Be authentic to your contradictions and dark side, not a sanitized version of yourself.""")

        return "\n\n".join(parts)

    def get_relevant_clash_points(self, other_names):
        """Extract clash point sections relevant to current speakers."""
        if not self.clash_points:
            return ""

        # Parse clash_points into sections by ## headers
        sections = []
        current_header = ""
        current_body = []
        for line in self.clash_points.split("\n"):
            if line.startswith("## "):
                if current_header:
                    sections.append((current_header, "\n".join(current_body)))
                current_header = line
                current_body = []
            else:
                current_body.append(line)
        if current_header:
            sections.append((current_header, "\n".join(current_body)))

        relevant = []
        for name in other_names:
            first_name = name.split()[0]  # "Elon Musk" -> "Elon"
            for header, body in sections:
                if first_name.lower() in header.lower():
                    relevant.append(f"{header}\n{body}")
                    break
        return "\n\n".join(relevant)

    def respond(self, conversation_history, current_topic="", model=None, temperature=None, max_tokens=None):
        """
        Generate a response given the conversation so far.

        Args:
            conversation_history: List of {"speaker": str, "text": str, "round": int}
            current_topic: Optional topic context for this round
            model: Override model name
            temperature: Override temperature
            max_tokens: Override max tokens

        Returns:
            str: The agent's response text
        """
        model = model if model is not None else os.getenv("COUNCIL_MODEL", "llama-3.3-70b-versatile")
        temperature = temperature if temperature is not None else float(os.getenv("COUNCIL_TEMPERATURE", "0.85"))
        max_tokens = max_tokens if max_tokens is not None else int(os.getenv("COUNCIL_MAX_TOKENS", "500"))

        # Build messages — OpenAI format: system + user messages
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add recent conversation as context
        recent = conversation_history[-self.max_memory:] if len(conversation_history) > self.max_memory else conversation_history

        if recent:
            transcript_lines = []
            for entry in recent:
                speaker = entry["speaker"]
                text = entry["text"]
                if speaker == "[MODERATOR]":
                    transcript_lines.append(f"**[MODERATOR -- Kevin Kim]:** {text}")
                elif "GOD" in speaker:
                    transcript_lines.append(f"**[BREAKING NEWS / GOD-MODE INJECTION]:** {text}")
                else:
                    transcript_lines.append(f"**{speaker}:** {text}")

            transcript = "\n\n".join(transcript_lines)

            other_speakers = list({e["speaker"] for e in recent if e["speaker"] != self.name and not e["speaker"].startswith("[")})
            clash_context = self.get_relevant_clash_points(other_speakers)

            context_parts = [f"## COUNCIL TRANSCRIPT (last {len(recent)} messages)\n\n{transcript}"]

            if clash_context:
                context_parts.append(f"## YOUR RELATIONSHIP WITH CURRENT SPEAKERS\n\n{clash_context}")

            if current_topic:
                context_parts.append(f"## CURRENT QUESTION\n\n{current_topic}")

            context_parts.append(f"Now respond as {self.name}. Stay in character. Speak naturally in your voice.")

            messages.append({"role": "user", "content": "\n\n".join(context_parts)})
        else:
            messages.append({
                "role": "user",
                "content": f"{current_topic}\n\nYou are the first to respond. Speak as {self.name}."
            })

        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=messages,
                )
                if not response.choices:
                    return "[No response generated]"
                return response.choices[0].message.content or "[Empty response]"
            except Exception as e:
                err_msg = str(e).lower()
                if ("rate" in err_msg or "429" in err_msg or "quota" in err_msg) and attempt < max_retries - 1:
                    # Rotate to next API key
                    self.client = _rotate_client()
                    time.sleep(1)
                elif attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    raise


def load_agents(council_dir, client=None):
    """
    Load all 8 council agents from the directory structure.

    Args:
        council_dir: Path to the_council/ root directory
        client: Shared OpenAI-compatible client

    Returns:
        Dict[str, CouncilAgent] keyed by agent name
    """
    council_dir = Path(council_dir)
    profiles_path = council_dir / "profiles" / "council_profiles.json"
    profiles = json.loads(profiles_path.read_text(encoding="utf-8"))

    # Map username to profile
    username_to_profile = {p["username"]: p for p in profiles}

    # Map username to character directory name
    username_to_dir = {
        "elon_musk": "musk",
        "richard_feynman": "feynman",
        "kobe_bryant": "kobe",
        "steve_jobs": "jobs",
        "jean_paul_sartre": "sartre",
        "george_carlin": "carlin",
        "bryan_johnson": "johnson",
        "kevin_kim": "kevin",
    }

    agents = {}
    client = client or _create_client()

    for username, dirname in username_to_dir.items():
        char_dir = council_dir / "characters" / dirname
        if char_dir.exists() and username in username_to_profile:
            agent = CouncilAgent(char_dir, username_to_profile[username], client)
            agents[agent.name] = agent

    return agents
