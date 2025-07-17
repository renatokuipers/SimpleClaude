"""Simple Claude API - So easy, even toddlers can use it!

This module provides an ultra-simple interface to Claude that:
- Always streams responses in real-time
- Always shows metrics and costs
- Handles all errors gracefully
- Requires minimal configuration

Basic Usage:
    from simple_claude import SimpleClaudeAPI
    
    claude = SimpleClaudeAPI()
    response = claude.ask("What is Python?")
    print(f"Cost: ${response.cost}")

Even Simpler:
    from simple_claude import claude_say
    
    claude_say("Tell me a joke")  # Just prints the response
"""

from .simple_api import SimpleClaudeAPI, ask_claude_simple, claude_say
from .models import SimpleResponse, SimpleMetrics, SimpleConfig

# Version info
__version__ = "1.0.0"
__author__ = "Claude Genesys Team"
__description__ = "Ultra-simple Claude API wrapper for toddler-level programming"

# Main exports
__all__ = [
    "SimpleClaudeAPI",
    "ask_claude_simple", 
    "claude_say",
    "SimpleResponse",
    "SimpleMetrics", 
    "SimpleConfig"
]

# Convenience instance for ultra-simple usage
_default_claude = None

def claude(prompt: str, system_prompt: str = None) -> SimpleResponse:
    """Ultra-simple function - just ask Claude anything.
    
    Args:
        prompt: Your question or request
        system_prompt: Optional system prompt to set Claude's behavior
        
    Returns:
        SimpleResponse with Claude's answer
        
    Example:
        >>> from simple_claude import claude
        >>> response = claude("What is 2+2?")
        >>> print(response.text)
        
        >>> # With system prompt
        >>> response = claude("What is 2+2?", system_prompt="You are a math tutor.")
        >>> print(response.text)
    """
    global _default_claude
    if _default_claude is None:
        _default_claude = SimpleClaudeAPI()
    
    # Set system prompt if provided
    if system_prompt is not None:
        _default_claude.set_system_prompt(system_prompt)
    
    return _default_claude.ask(prompt)


def reset_claude():
    """Reset the default Claude instance."""
    global _default_claude
    _default_claude = None


# Show welcome message when module is imported
print("🤖 Simple Claude API loaded! Try: from simple_claude import claude; claude('Hello!')")