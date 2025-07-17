"""Simple data models for toddler-friendly Claude API."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class SimpleResponse:
    """Ultra-simple response object that contains everything a user needs."""
    
    text: str
    """The complete text response from Claude."""
    
    cost: float
    """How much this request cost in USD."""
    
    tokens_used: int
    """Total tokens consumed (input + output)."""
    
    model: str
    """Which model was used (e.g., 'claude-3-sonnet')."""
    
    success: bool
    """Whether the request was successful."""
    
    session_id: Optional[str] = None
    """Session ID for this conversation."""
    
    duration_seconds: float = 0.0
    """How long the request took in seconds."""
    
    thinking: Optional[str] = None
    """Claude's internal thinking process (if available)."""
    
    tool_uses: List[Dict[str, Any]] = field(default_factory=list)
    """Tools that Claude used during this response."""
    
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    """Results from the tools that Claude used."""
    
    def __str__(self) -> str:
        """Human-readable representation."""
        return f"SimpleResponse(text='{self.text}\n', cost=${self.cost:.4f}, tokens={self.tokens_used})"
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return self.__str__()


@dataclass
class SimpleMetrics:
    """Simple metrics display for real-time feedback."""
    
    total_cost: float
    """Total cost for this session."""
    
    total_tokens: int
    """Total tokens used in this session."""
    
    requests_count: int
    """Number of requests made in this session."""
    
    average_response_time: float
    """Average response time in seconds."""
    
    def __str__(self) -> str:
        """Human-readable metrics."""
        return (f"📊 Session Stats: ${self.total_cost:.4f} spent, "
                f"{self.total_tokens} tokens, {self.requests_count} requests, "
                f"{self.average_response_time:.1f}s avg response time")


@dataclass
class SimpleConfig:
    """Ultra-simple configuration with sensible defaults."""
    
    model: str = "sonnet"
    """Model to use: 'sonnet' (default), 'opus', or 'haiku'."""
    
    show_thinking: bool = False
    """Whether to show Claude's internal thinking process."""
    
    show_metrics: bool = True
    """Whether to show metrics after each response."""
    
    auto_continue: bool = False
    """Whether to continue previous conversations automatically."""
    
    max_retries: int = 3
    """Maximum number of retries on failure."""
    
    timeout_seconds: int = 300
    """Request timeout in seconds."""
    
    verbose: bool = False
    """Show detailed debug information."""
    
    system_prompt: Optional[str] = None
    """System prompt to append to all requests."""