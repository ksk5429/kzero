"""
Opinion Evolution Engine — tracks how agent positions shift during deliberation.

MiroFish Principle: agents don't just talk, they EVOLVE. Each round, their
position on the question is extracted, scored, and tracked. The simulation
produces convergence/divergence metrics, not just transcripts.

Usage:
    tracker = EvolutionTracker(agents, question, client, model)
    tracker.extract_position(agent_name, response_text, round_num)
    tracker.get_convergence_report()
    tracker.get_prediction()
"""

import json
import os
import re
import time
from typing import Any


def _extract_json_safe(text: str) -> dict | None:
    """Try to parse JSON from LLM output, handling fences and truncation."""
    text = text.strip()
    # Strip markdown fences
    if "```" in text:
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    # Find first {
    start = text.find("{")
    if start == -1:
        return None
    end = text.rfind("}")
    if end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


class EvolutionTracker:
    """Tracks opinion evolution across rounds for all agents."""

    def __init__(self, agent_names: list[str], question: str, client: Any, model: str):
        self.agent_names = agent_names
        self.question = question
        self.client = client
        self.model = model

        # Position history: {agent_name: [(round, position_text, score)]}
        self.positions: dict[str, list[tuple[int, str, float]]] = {
            name: [] for name in agent_names
        }

        # Convergence history: [(round, variance)]
        self.convergence_history: list[tuple[int, float]] = []

    def extract_position(self, agent_name: str, response_text: str, round_num: int) -> dict:
        """
        After an agent speaks, extract their current position on the question.

        Returns:
            {"position": str, "score": float, "shifted": bool, "shift_reason": str}
        """
        prev_positions = self.positions.get(agent_name, [])
        prev_text = prev_positions[-1][1] if prev_positions else "No prior position"
        prev_score = prev_positions[-1][2] if prev_positions else 0.0

        prompt = f"""Analyze this agent's response and extract their CURRENT POSITION on the question.

QUESTION: {self.question}

AGENT ({agent_name}) JUST SAID:
{response_text[:1500]}

THEIR PREVIOUS POSITION: {prev_text}

Return JSON with exactly these fields:
- "position": One sentence summarizing their current stance (max 30 words)
- "score": Float from -1.0 (strongly against/negative) to +1.0 (strongly for/positive). 0.0 = neutral/undecided.
- "shifted": Boolean — did their position meaningfully change from the previous position?
- "shift_reason": If shifted, one sentence explaining why. If not shifted, null.
- "conviction": Float 0.0 to 1.0 — how strongly do they hold this position? (1.0 = absolute certainty)

Return ONLY valid JSON. No markdown fences."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                max_tokens=300,
                messages=[
                    {"role": "system", "content": "You are a precise deliberation analyst. Extract positions as structured data."},
                    {"role": "user", "content": prompt},
                ],
            )
            raw = response.choices[0].message.content or ""
            result = _extract_json_safe(raw)

            if result:
                position = result.get("position", "Unknown")
                score = float(result.get("score", 0.0))
                score = max(-1.0, min(1.0, score))  # Clamp
                shifted = result.get("shifted", False)
                shift_reason = result.get("shift_reason")
                conviction = float(result.get("conviction", 0.5))

                self.positions[agent_name].append((round_num, position, score))
                self._update_convergence(round_num)

                return {
                    "agent": agent_name,
                    "round": round_num,
                    "position": position,
                    "score": score,
                    "previous_score": prev_score,
                    "shifted": shifted,
                    "shift_reason": shift_reason,
                    "conviction": conviction,
                    "delta": abs(score - prev_score),
                }
        except Exception:
            pass

        # Fallback: lightweight keyword-based extraction (no LLM call)
        return self._extract_position_local(agent_name, response_text, round_num, prev_score)

    def _extract_position_local(self, agent_name: str, text: str, round_num: int, prev_score: float) -> dict:
        """Extract position using keyword analysis — no LLM call needed."""
        text_lower = text.lower()

        # Score based on sentiment keywords
        for_keywords = ["yes", "absolutely", "should", "must", "pursue", "essential",
                        "obviously", "of course", "agree", "support", "beneficial",
                        "necessary", "important", "worth", "embrace", "create",
                        "build", "advance", "progress", "opportunity"]
        against_keywords = ["no", "shouldn't", "dangerous", "risk", "wrong", "foolish",
                           "absurd", "meaningless", "pointless", "reject", "oppose",
                           "refuse", "never", "death is", "hubris", "arrogant",
                           "doomed", "failure", "destroy", "irrelevant"]

        for_count = sum(1 for kw in for_keywords if kw in text_lower)
        against_count = sum(1 for kw in against_keywords if kw in text_lower)

        total = for_count + against_count
        if total > 0:
            score = (for_count - against_count) / total
            score = max(-1.0, min(1.0, score))
        else:
            score = 0.0

        # Position = first sentence of their response (crude but fast)
        sentences = text.replace("\n", " ").split(".")
        position = sentences[0].strip()[:80] if sentences else "No clear position"

        shifted = abs(score - prev_score) > 0.2

        self.positions[agent_name].append((round_num, position, score))
        self._update_convergence(round_num)

        return {
            "agent": agent_name, "round": round_num,
            "position": position, "score": round(score, 2),
            "previous_score": prev_score, "shifted": shifted,
            "shift_reason": "Position shifted based on dialogue" if shifted else None,
            "conviction": min(1.0, total / 10), "delta": round(abs(score - prev_score), 2),
        }

    def _update_convergence(self, round_num: int):
        """Calculate current opinion variance (convergence metric)."""
        scores = []
        for name in self.agent_names:
            if self.positions[name]:
                scores.append(self.positions[name][-1][2])
        if len(scores) >= 2:
            mean = sum(scores) / len(scores)
            variance = sum((s - mean) ** 2 for s in scores) / len(scores)
            self.convergence_history.append((round_num, variance))

    def get_convergence_report(self) -> dict:
        """Get the full convergence analysis."""
        # Current scores
        current_scores = {}
        for name in self.agent_names:
            if self.positions[name]:
                current_scores[name] = {
                    "score": self.positions[name][-1][2],
                    "position": self.positions[name][-1][1],
                    "n_shifts": sum(
                        1 for i in range(1, len(self.positions[name]))
                        if abs(self.positions[name][i][2] - self.positions[name][i - 1][2]) > 0.15
                    ),
                }

        # Convergence trend
        if len(self.convergence_history) >= 2:
            first_var = self.convergence_history[0][1]
            last_var = self.convergence_history[-1][1]
            if last_var < first_var * 0.7:
                trend = "CONVERGING"
            elif last_var > first_var * 1.3:
                trend = "DIVERGING"
            else:
                trend = "STABLE"
        else:
            trend = "INSUFFICIENT_DATA"

        # Factions (cluster agents by score proximity)
        factions = self._detect_factions()

        # Most shifted agent
        max_shift_agent = None
        max_shift_delta = 0
        for name in self.agent_names:
            if len(self.positions[name]) >= 2:
                total_delta = abs(self.positions[name][-1][2] - self.positions[name][0][2])
                if total_delta > max_shift_delta:
                    max_shift_delta = total_delta
                    max_shift_agent = name

        return {
            "current_positions": current_scores,
            "convergence_trend": trend,
            "convergence_history": [
                {"round": r, "variance": round(v, 4)} for r, v in self.convergence_history
            ],
            "factions": factions,
            "most_shifted": {
                "agent": max_shift_agent,
                "total_delta": round(max_shift_delta, 3),
            } if max_shift_agent else None,
        }

    def _detect_factions(self, threshold: float = 0.3) -> list[dict]:
        """Detect opinion factions (clusters of agents with similar scores)."""
        scored_agents = []
        for name in self.agent_names:
            if self.positions[name]:
                scored_agents.append((name, self.positions[name][-1][2]))

        if not scored_agents:
            return []

        # Simple 1D clustering: sort by score, group adjacent agents within threshold
        scored_agents.sort(key=lambda x: x[1])
        factions = []
        current_faction = [scored_agents[0]]

        for i in range(1, len(scored_agents)):
            if abs(scored_agents[i][1] - current_faction[-1][1]) <= threshold:
                current_faction.append(scored_agents[i])
            else:
                factions.append(current_faction)
                current_faction = [scored_agents[i]]
        factions.append(current_faction)

        return [
            {
                "members": [name for name, _ in faction],
                "avg_score": round(sum(s for _, s in faction) / len(faction), 3),
                "label": "FOR" if sum(s for _, s in faction) / len(faction) > 0.2
                         else "AGAINST" if sum(s for _, s in faction) / len(faction) < -0.2
                         else "NEUTRAL",
            }
            for faction in factions
        ]

    def get_prediction(self) -> dict:
        """
        Generate a prediction based on current evolution state.

        Returns a structured prediction:
        - majority_position: where most agents landed
        - confidence: how certain the prediction is (based on convergence + conviction)
        - dissent: who disagrees and why
        """
        scores = []
        for name in self.agent_names:
            if self.positions[name]:
                scores.append((name, self.positions[name][-1][2], self.positions[name][-1][1]))

        if not scores:
            return {"prediction": "No data", "confidence": 0.0}

        avg_score = sum(s for _, s, _ in scores) / len(scores)

        # Majority
        for_count = sum(1 for _, s, _ in scores if s > 0.2)
        against_count = sum(1 for _, s, _ in scores if s < -0.2)
        neutral_count = len(scores) - for_count - against_count

        if for_count > against_count:
            majority = "FOR"
            majority_pct = for_count / len(scores)
        elif against_count > for_count:
            majority = "AGAINST"
            majority_pct = against_count / len(scores)
        else:
            majority = "SPLIT"
            majority_pct = 0.5

        # Convergence as confidence modifier
        if self.convergence_history:
            final_variance = self.convergence_history[-1][1]
            convergence_confidence = max(0, 1.0 - final_variance)
        else:
            convergence_confidence = 0.5

        confidence = majority_pct * 0.6 + convergence_confidence * 0.4

        # Dissenters
        dissenters = []
        for name, score, position in scores:
            if (majority == "FOR" and score < -0.2) or (majority == "AGAINST" and score > 0.2):
                dissenters.append({"agent": name, "score": score, "position": position})

        return {
            "question": self.question,
            "prediction": majority,
            "average_score": round(avg_score, 3),
            "for_count": for_count,
            "against_count": against_count,
            "neutral_count": neutral_count,
            "confidence": round(confidence, 3),
            "dissenters": dissenters,
            "n_rounds_tracked": len(self.convergence_history),
        }

    def format_status(self) -> str:
        """Format current evolution state for console display."""
        lines = []
        lines.append("OPINION EVOLUTION")
        lines.append("-" * 50)

        for name in self.agent_names:
            if not self.positions[name]:
                continue
            score = self.positions[name][-1][2]
            position = self.positions[name][-1][1]

            # Visual bar
            bar_pos = int((score + 1) * 15)  # 0-30 range
            bar = "." * 30
            bar = bar[:bar_pos] + "|" + bar[bar_pos + 1:]
            bar = f"AGAINST [{bar}] FOR"

            short = name.split()[0]
            n_shifts = sum(
                1 for i in range(1, len(self.positions[name]))
                if abs(self.positions[name][i][2] - self.positions[name][i - 1][2]) > 0.15
            )
            shift_marker = f" (shifted {n_shifts}x)" if n_shifts > 0 else ""

            lines.append(f"  {short:12} {score:+.2f} {bar}{shift_marker}")
            lines.append(f"               {position[:60]}")

        # Convergence
        if self.convergence_history:
            trend = self.get_convergence_report()["convergence_trend"]
            var = self.convergence_history[-1][1]
            lines.append("")
            lines.append(f"  Trend: {trend} (variance: {var:.4f})")

        # Prediction
        pred = self.get_prediction()
        lines.append(f"  Prediction: {pred['prediction']} (confidence: {pred['confidence']:.0%})")

        return "\n".join(lines)
