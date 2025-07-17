"""Claude API - A Python wrapper for Claude CLI with advanced features."""

from .api import ClaudeAPI, AsyncClaudeAPI, ask_claude, create_api_with_config
from .parser import (
    ClaudeResponseParser, parse_claude_stream, StreamingResponseParser,
    stream_parse_generator, async_stream_parse_generator
)
from .models import (
    # Response models
    ClaudeResponse,
    SystemInit,
    AssistantResponse,
    UserResponse,
    ResultSummary,
    Usage,
    ExtendedUsage,
    TextContent,
    ThinkingContent,
    ToolUseContent,
    ToolResultContent,
    AssistantMessage,
    UserMessage,
    
    # Configuration models
    APIConfig,
    RetryConfig,
    RateLimitConfig,
    StreamConfig,
    SessionConfig,
    CommandFlags,
    Session,
    RateLimitState,
    DebugConfig,
    InputFormat,
    ToolRestrictions,
    ClaudeModelConfig,
    DirectoryConfig,
    ConversationConfig
)

__version__ = "2.1.0"
__all__ = [
    # API classes
    "ClaudeAPI",
    "AsyncClaudeAPI",
    
    # Convenience functions
    "ask_claude",
    "create_api_with_config",
    
    # Parsers
    "ClaudeResponseParser",
    "parse_claude_stream",
    "StreamingResponseParser",
    "stream_parse_generator",
    "async_stream_parse_generator",
    
    # Response models
    "ClaudeResponse",
    "SystemInit",
    "AssistantResponse",
    "UserResponse",
    "ResultSummary",
    "Usage",
    "ExtendedUsage",
    "TextContent",
    "ThinkingContent",
    "ToolUseContent",
    "ToolResultContent",
    "AssistantMessage",
    "UserMessage",
    
    # Configuration models
    "APIConfig",
    "RetryConfig",
    "RateLimitConfig",
    "StreamConfig",
    "SessionConfig",
    "CommandFlags",
    "Session",
    "RateLimitState",
    "DebugConfig",
    "InputFormat",
    "ToolRestrictions",
    "ClaudeModelConfig",
    "DirectoryConfig",
    "ConversationConfig"
]