"""Token usage accumulator for per-article LLM cost tracking."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TokenAccumulator:
    """Accumulates token counts across multiple LLM calls for a single article."""

    input_tokens: int = field(default=0)
    output_tokens: int = field(default=0)
    cache_read_tokens: int = field(default=0)
    cache_creation_tokens: int = field(default=0)

    def add_response(self, response: object) -> None:
        """Record token usage from an Anthropic SDK Message response."""
        usage = response.usage  # type: ignore[attr-defined]
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        self.cache_read_tokens += getattr(usage, "cache_read_input_tokens", 0)
        self.cache_creation_tokens += getattr(usage, "cache_creation_input_tokens", 0)

    @property
    def cost_usd(self) -> float:
        """Estimated cost in USD using Haiku/Sonnet blended pricing.

        Input: $1/MTok, cache_read: $0.10/MTok,
        cache_creation: $1.25/MTok, output: $5/MTok.
        """
        return (
            self.input_tokens * 1e-6
            + self.cache_read_tokens * 0.1e-6
            + self.cache_creation_tokens * 1.25e-6
            + self.output_tokens * 5e-6
        )
