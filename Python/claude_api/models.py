"""Data models for Claude API responses and configuration."""

from typing import List, Optional, Dict, Any, Literal, Union
from datetime import datetime
from pydantic import BaseModel, Field


class Usage(BaseModel):
    """Token usage information."""
    input_tokens: int
    cache_creation_input_tokens: Optional[int] = None
    cache_read_input_tokens: Optional[int] = None
    output_tokens: int
    service_tier: Optional[str] = None


class ServerToolUse(BaseModel):
    """Server tool usage information."""
    web_search_requests: int = 0


class ExtendedUsage(Usage):
    """Extended usage information including server tools."""
    server_tool_use: Optional[ServerToolUse] = None


class ThinkingContent(BaseModel):
    """Thinking content for Claude's reasoning."""
    type: Literal["thinking"]
    thinking: str
    signature: Optional[str] = None


class TextContent(BaseModel):
    """Text content in messages."""
    type: Literal["text"]
    text: str


class ToolUseContent(BaseModel):
    """Tool use content in messages."""
    type: Literal["tool_use"]
    id: str
    name: str
    input: Dict[str, Any]


class ToolResultContent(BaseModel):
    """Tool result content in user messages."""
    tool_use_id: str
    type: Literal["tool_result"]
    content: str
    is_error: Optional[bool] = False


MessageContent = Union[TextContent, ThinkingContent, ToolUseContent]
UserContent = Union[ToolResultContent]


class AssistantMessage(BaseModel):
    """Assistant message structure."""
    id: str
    type: Literal["message"]
    role: Literal["assistant"]
    model: str
    content: List[MessageContent]
    stop_reason: Optional[str] = None
    stop_sequence: Optional[str] = None
    usage: Usage


class UserMessage(BaseModel):
    """User message structure (typically tool results)."""
    role: Literal["user"]
    content: List[UserContent]


class SystemInit(BaseModel):
    """System initialization response."""
    type: Literal["system"]
    subtype: Literal["init"]
    cwd: str
    session_id: str
    tools: List[str]
    mcp_servers: List[Any] = Field(default_factory=list)
    model: str
    permissionMode: str
    apiKeySource: str


class AssistantResponse(BaseModel):
    """Assistant response wrapper."""
    type: Literal["assistant"]
    message: AssistantMessage
    parent_tool_use_id: Optional[str] = None
    session_id: str


class UserResponse(BaseModel):
    """User response wrapper (tool results)."""
    type: Literal["user"]
    message: UserMessage
    parent_tool_use_id: Optional[str] = None
    session_id: str


class ResultSummary(BaseModel):
    """Result summary with metrics."""
    type: Literal["result"]
    subtype: str  # Allow any subtype string (success, error, error_during_execution, etc.)
    is_error: bool = False
    duration_ms: int = 0
    duration_api_ms: int = 0
    num_turns: int = 0
    result: str = ""  # Make optional with default
    session_id: str = ""
    total_cost_usd: float = 0.0
    usage: Optional[ExtendedUsage] = None  # Make optional


class ClaudeResponse(BaseModel):
    """Complete Claude API response."""
    system_init: Optional[SystemInit] = None
    assistant_responses: List[AssistantResponse] = Field(default_factory=list)
    user_responses: List[UserResponse] = Field(default_factory=list)
    result_summary: Optional[ResultSummary] = None
    raw_response: str = ""
    
    @property
    def assistant_response(self) -> Optional[AssistantResponse]:
        """Get the first assistant response for backward compatibility."""
        return self.assistant_responses[0] if self.assistant_responses else None
    
    def get_all_events(self) -> List[Union[SystemInit, AssistantResponse, UserResponse, ResultSummary]]:
        """Get all events in order."""
        events = []
        if self.system_init:
            events.append(self.system_init)
        events.extend(self.assistant_responses)
        events.extend(self.user_responses)
        if self.result_summary:
            events.append(self.result_summary)
        return events


# New models for advanced features

class RetryConfig(BaseModel):
    """Configuration for retry logic."""
    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    retry_on: List[str] = Field(default_factory=lambda: ["TimeoutError", "ConnectionError"])


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10  # Allow short bursts
    enabled: bool = True


class StreamConfig(BaseModel):
    """Configuration for streaming responses."""
    buffer_size: int = 65536  # Increased buffer size for full response capture
    timeout_between_chunks: float = 30.0  # seconds
    yield_raw: bool = False  # If True, yield raw JSON strings


class SessionConfig(BaseModel):
    """Configuration for session management."""
    maintain_context: bool = True
    max_history_size: int = 100  # Max messages to keep
    persist_to_file: Optional[str] = None  # Path to save session
    auto_save: bool = True


class DebugConfig(BaseModel):
    """Configuration for debug mode."""
    enabled: bool = False


class InputFormat(BaseModel):
    """Configuration for input format."""
    format: Literal["text", "stream-json"] = "text"


class ToolRestrictions(BaseModel):
    """Configuration for tool restrictions."""
    allowed_tools: Optional[List[str]] = None  # e.g., ["Bash(git:*)", "Edit"]
    disallowed_tools: Optional[List[str]] = None  # e.g., ["Bash(git:*)", "Edit"]


class ClaudeModelConfig(BaseModel):
    """Configuration for model selection."""
    model: Optional[str] = "sonnet"  # Default to 'sonnet', also accepts 'opus' or full name
    fallback_model: Optional[str] = None  # For automatic fallback when overloaded


class DirectoryConfig(BaseModel):
    """Configuration for additional directories."""
    additional_dirs: List[str] = Field(default_factory=list)  # Additional directories to allow access


class ConversationConfig(BaseModel):
    """Configuration for conversation continuation/resumption."""
    continue_last: bool = False  # -c, --continue flag
    resume_session_id: Optional[str] = None  # -r, --resume [sessionId]


class SystemPromptConfig(BaseModel):
    """Configuration for system prompt."""
    system_prompt: Optional[str] = None  # --append-system-prompt


class CommandFlags(BaseModel):
    """Custom command flags configuration."""
    allowed_flags: List[str] = Field(default_factory=lambda: [
        "--temperature", "--max-tokens", "--stop-sequence",
        "-d", "--debug", "--input-format", "--allowedTools",
        "--disallowedTools", "-c", "--continue", "-r", "--resume",
        "--model", "--fallback-model", "--add-dir", "--append-system-prompt"
    ])
    custom_flags: Dict[str, str] = Field(default_factory=dict)
    override_defaults: bool = False


class Session(BaseModel):
    """Session state for maintaining context."""
    session_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    message_history: List[Union[AssistantResponse, UserResponse]] = Field(default_factory=list)
    total_tokens: int = 0
    total_cost: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_response(self, response: Union[AssistantResponse, UserResponse]):
        """Add a response to session history."""
        self.message_history.append(response)
        self.last_activity = datetime.now()
        
        # Update token count if assistant response
        if isinstance(response, AssistantResponse) and response.message.usage:
            self.total_tokens += (
                response.message.usage.input_tokens + 
                response.message.usage.output_tokens
            )
    
    def get_context(self, max_messages: Optional[int] = None) -> List[Union[AssistantResponse, UserResponse]]:
        """Get recent context from history."""
        if max_messages:
            return self.message_history[-max_messages:]
        return self.message_history
    
    def clear_history(self):
        """Clear message history but keep session metadata."""
        self.message_history.clear()
        self.total_tokens = 0
        self.total_cost = 0.0


class RateLimitState(BaseModel):
    """State for rate limiting."""
    requests_this_minute: int = 0
    requests_this_hour: int = 0
    minute_reset_time: datetime = Field(default_factory=datetime.now)
    hour_reset_time: datetime = Field(default_factory=datetime.now)
    last_request_time: Optional[datetime] = None
    
    def should_delay(self, config: RateLimitConfig) -> tuple[bool, float]:
        """Check if request should be delayed and return delay in seconds."""
        now = datetime.now()
        
        # Reset counters if needed
        if (now - self.minute_reset_time).total_seconds() >= 60:
            self.requests_this_minute = 0
            self.minute_reset_time = now
            
        if (now - self.hour_reset_time).total_seconds() >= 3600:
            self.requests_this_hour = 0
            self.hour_reset_time = now
        
        # Check limits
        if self.requests_this_minute >= config.requests_per_minute:
            delay = 60 - (now - self.minute_reset_time).total_seconds()
            return True, max(0, delay)
            
        if self.requests_this_hour >= config.requests_per_hour:
            delay = 3600 - (now - self.hour_reset_time).total_seconds()
            return True, max(0, delay)
            
        return False, 0
    
    def record_request(self):
        """Record a request was made."""
        self.requests_this_minute += 1
        self.requests_this_hour += 1
        self.last_request_time = datetime.now()


class APIConfig(BaseModel):
    """Complete API configuration."""
    retry: RetryConfig = Field(default_factory=RetryConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    streaming: StreamConfig = Field(default_factory=StreamConfig)
    session: SessionConfig = Field(default_factory=SessionConfig)
    command_flags: CommandFlags = Field(default_factory=CommandFlags)
    debug: DebugConfig = Field(default_factory=DebugConfig)
    input_format: InputFormat = Field(default_factory=InputFormat)
    tool_restrictions: ToolRestrictions = Field(default_factory=ToolRestrictions)
    claude_model_config: ClaudeModelConfig = Field(default_factory=ClaudeModelConfig)
    directory_config: DirectoryConfig = Field(default_factory=DirectoryConfig)
    conversation_config: ConversationConfig = Field(default_factory=ConversationConfig)
    system_prompt_config: SystemPromptConfig = Field(default_factory=SystemPromptConfig)
    verbose: bool = True
    default_timeout: int = 300