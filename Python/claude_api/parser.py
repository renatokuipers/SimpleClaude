"""Parser for Claude API JSON stream responses with streaming support."""

import json
from typing import List, Generator, Union, Optional, Dict, Any, AsyncGenerator
from .models import (
    SystemInit, AssistantResponse, UserResponse, ResultSummary, ClaudeResponse,
    AssistantMessage, UserMessage, TextContent, ThinkingContent, ToolUseContent,
    ToolResultContent, Usage, ExtendedUsage, ServerToolUse, StreamConfig
)


class ClaudeResponseParser:
    """Parses Claude API JSON stream responses."""
    
    def __init__(self):
        """Initialize the parser."""
        self.system_init: Optional[SystemInit] = None
        self.assistant_responses: List[AssistantResponse] = []
        self.user_responses: List[UserResponse] = []
        self.result_summary: Optional[ResultSummary] = None
        self.raw_lines: List[str] = []
        self.events: List[Dict[str, Any]] = []
    
    def parse_line(self, line: str) -> Optional[Union[SystemInit, AssistantResponse, UserResponse, ResultSummary]]:
        """Parse a single JSON line from the stream."""
        if not line.strip():
            return None
            
        try:
            data = json.loads(line)
            self.raw_lines.append(line)
            self.events.append(data)
            
            if data.get("type") == "system" and data.get("subtype") == "init":
                self.system_init = SystemInit(**data)
                return self.system_init
                
            elif data.get("type") == "assistant":
                # Parse assistant message with proper content types
                message_data = data.get("message", {})
                content_list = []
                
                for content in message_data.get("content", []):
                    content_type = content.get("type")
                    
                    if content_type == "text":
                        content_list.append(TextContent(**content))
                    elif content_type == "thinking":
                        content_list.append(ThinkingContent(**content))
                    elif content_type == "tool_use":
                        content_list.append(ToolUseContent(**content))
                    else:
                        # Skip unknown content types
                        print(f"Unknown content type: {content_type}")
                        continue
                
                # Create AssistantMessage with parsed content
                message_data["content"] = content_list
                assistant_msg = AssistantMessage(**message_data)
                
                # Create AssistantResponse
                response_data = {
                    "type": "assistant",
                    "message": assistant_msg,
                    "parent_tool_use_id": data.get("parent_tool_use_id"),
                    "session_id": data.get("session_id")
                }
                assistant_response = AssistantResponse(**response_data)
                self.assistant_responses.append(assistant_response)
                return assistant_response
                
            elif data.get("type") == "user":
                # Parse user message (tool results)
                message_data = data.get("message", {})
                content_list = []
                
                for content in message_data.get("content", []):
                    if content.get("type") == "tool_result":
                        # Handle case where content field is a list of content objects
                        content_field = content.get("content", "")
                        if isinstance(content_field, list):
                            # Extract text from content objects
                            text_parts = []
                            for content_obj in content_field:
                                if isinstance(content_obj, dict) and content_obj.get("type") == "text":
                                    text_parts.append(content_obj.get("text", ""))
                            content_text = "".join(text_parts)
                        else:
                            content_text = str(content_field)
                        
                        # Create ToolResultContent with extracted text
                        tool_result = ToolResultContent(
                            tool_use_id=content.get("tool_use_id", ""),
                            type="tool_result",
                            content=content_text,
                            is_error=content.get("is_error", False)
                        )
                        content_list.append(tool_result)
                
                # Create UserMessage with parsed content
                message_data["content"] = content_list
                user_msg = UserMessage(**message_data)
                
                # Create UserResponse
                response_data = {
                    "type": "user",
                    "message": user_msg,
                    "parent_tool_use_id": data.get("parent_tool_use_id"),
                    "session_id": data.get("session_id")
                }
                user_response = UserResponse(**response_data)
                self.user_responses.append(user_response)
                return user_response
                
            elif data.get("type") == "result":
                try:
                    self.result_summary = ResultSummary(**data)
                    return self.result_summary
                except Exception as validation_error:
                    print(f"Warning: Could not parse result summary: {validation_error}")
                    # Create a minimal result summary with available data
                    self.result_summary = ResultSummary(
                        type="result",
                        subtype=data.get("subtype", "unknown"),
                        is_error=data.get("is_error", True),
                        session_id=data.get("session_id", "")
                    )
                    return self.result_summary
                
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing line: {e}")
            return None
    
    def parse_stream(self, stream: str) -> ClaudeResponse:
        """Parse complete stream output into ClaudeResponse."""
        lines = stream.strip().split('\n')
        
        for line in lines:
            self.parse_line(line)
        
        return ClaudeResponse(
            system_init=self.system_init,
            assistant_responses=self.assistant_responses,
            user_responses=self.user_responses,
            result_summary=self.result_summary,
            raw_response=stream
        )
    
    def get_message_text(self) -> str:
        """Extract all assistant message text."""
        texts = []
        for response in self.assistant_responses:
            for content in response.message.content:
                if isinstance(content, TextContent):
                    texts.append(content.text)
        return "\n".join(texts)
    
    def get_tool_uses(self) -> List[ToolUseContent]:
        """Extract all tool uses from assistant messages."""
        tool_uses = []
        for response in self.assistant_responses:
            for content in response.message.content:
                if isinstance(content, ToolUseContent):
                    tool_uses.append(content)
        return tool_uses
    
    def get_thinking(self) -> List[str]:
        """Extract all thinking content."""
        thoughts = []
        for response in self.assistant_responses:
            for content in response.message.content:
                if isinstance(content, ThinkingContent):
                    thoughts.append(content.thinking)
        return thoughts
    
    def get_tool_results(self) -> List[ToolResultContent]:
        """Extract all tool results from user messages."""
        results = []
        for response in self.user_responses:
            for content in response.message.content:
                if isinstance(content, ToolResultContent):
                    results.append(content)
        return results
    
    def get_usage_summary(self) -> Optional[ExtendedUsage]:
        """Get usage summary from result."""
        if self.result_summary:
            return self.result_summary.usage
        return None
    
    def get_cost(self) -> Optional[float]:
        """Get total cost in USD."""
        if self.result_summary:
            return self.result_summary.total_cost_usd
        return None
    
    def was_successful(self) -> bool:
        """Check if the request was successful."""
        return (
            self.result_summary is not None 
            and not self.result_summary.is_error
            and self.result_summary.subtype == "success"
        )
    
    def get_event_stream(self) -> Generator[Dict[str, Any], None, None]:
        """Yield parsed events as they occurred."""
        for event in self.events:
            yield event


class StreamingResponseParser:
    """Parser for real-time streaming responses."""
    
    def __init__(self, config: Optional[StreamConfig] = None):
        """Initialize streaming parser."""
        self.config = config or StreamConfig()
        self.buffer = ""
        self.parser = ClaudeResponseParser()
    
    def parse_chunk(self, chunk: str) -> Generator[Union[SystemInit, AssistantResponse, UserResponse, ResultSummary, str], None, None]:
        """Parse a chunk of streaming data and yield events."""
        self.buffer += chunk
        
        while '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            
            if line.strip():
                if self.config.yield_raw:
                    # Yield raw JSON string
                    yield line
                else:
                    # Parse and yield structured event
                    event = self.parser.parse_line(line)
                    if event:
                        yield event
    
    def flush(self) -> Generator[Union[SystemInit, AssistantResponse, UserResponse, ResultSummary, str], None, None]:
        """Flush any remaining buffer content."""
        if self.buffer.strip():
            if self.config.yield_raw:
                yield self.buffer
            else:
                event = self.parser.parse_line(self.buffer)
                if event:
                    yield event
        self.buffer = ""
    
    def get_response(self) -> ClaudeResponse:
        """Get the complete parsed response."""
        return ClaudeResponse(
            system_init=self.parser.system_init,
            assistant_responses=self.parser.assistant_responses,
            user_responses=self.parser.user_responses,
            result_summary=self.parser.result_summary,
            raw_response="\n".join(self.parser.raw_lines)
        )


def parse_claude_stream(stream: str) -> ClaudeResponse:
    """Convenience function to parse Claude stream output."""
    parser = ClaudeResponseParser()
    return parser.parse_stream(stream)


def stream_parse_generator(stream: Generator[str, None, None], config: Optional[StreamConfig] = None) -> Generator[Union[SystemInit, AssistantResponse, UserResponse, ResultSummary, str], None, None]:
    """Parse a stream generator and yield events in real-time."""
    parser = StreamingResponseParser(config)
    
    for chunk in stream:
        yield from parser.parse_chunk(chunk)
    
    # Flush any remaining content
    yield from parser.flush()


async def async_stream_parse_generator(
    stream: AsyncGenerator[str, None], 
    config: Optional[StreamConfig] = None
) -> AsyncGenerator[Union[SystemInit, AssistantResponse, UserResponse, ResultSummary, str], None]:
    """Parse an async stream generator and yield events in real-time."""
    parser = StreamingResponseParser(config)
    
    async for chunk in stream:
        for event in parser.parse_chunk(chunk):
            yield event
    
    # Flush any remaining content
    for event in parser.flush():
        yield event