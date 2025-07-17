"""Main Claude API module with advanced features including streaming, sessions, retry, and rate limiting."""

import subprocess
import asyncio
import json
import time
import pickle
from typing import Optional, Dict, Any, List, Generator, Union, AsyncGenerator
from pathlib import Path
from datetime import datetime
import shlex

from .parser import (
    ClaudeResponseParser, parse_claude_stream, StreamingResponseParser,
    stream_parse_generator, async_stream_parse_generator
)
from .models import (
    ClaudeResponse, APIConfig, Session, RateLimitState, RetryConfig,
    RateLimitConfig, StreamConfig, SessionConfig, CommandFlags,
    SystemInit, AssistantResponse, UserResponse, ResultSummary,
    DebugConfig, InputFormat, ToolRestrictions, ClaudeModelConfig,
    DirectoryConfig, ConversationConfig, SystemPromptConfig
)


class ClaudeAPI:
    """Advanced API for interacting with Claude command line interface."""
    
    def __init__(self, config: Optional[APIConfig] = None):
        """Initialize Claude API with configuration.
        
        Args:
            config: API configuration object
        """
        self.config = config or APIConfig()
        self.session = Session() if self.config.session.maintain_context else None
        self.rate_limiter = RateLimitState() if self.config.rate_limit.enabled else None
        
        # Build base command
        self.base_command = [
            "claude", "-p", "--dangerously-skip-permissions",
            "--output-format", "stream-json", "--verbose"
        ]
    
    def _build_command(self, prompt: str) -> List[str]:
        """Build complete command with custom flags."""
        command = self.base_command.copy()
        
        # Add debug flag
        if self.config.debug.enabled:
            command.append("--debug")
        
        # Add input format (only if not default)
        if self.config.input_format.format != "text":
            command.extend(["--input-format", self.config.input_format.format])
        
        # Add model configuration
        if self.config.claude_model_config.model:
            command.extend(["--model", self.config.claude_model_config.model])
        
        if self.config.claude_model_config.fallback_model:
            command.extend(["--fallback-model", self.config.claude_model_config.fallback_model])
        
        # Add tool restrictions
        if self.config.tool_restrictions.allowed_tools:
            # Join tools with spaces as Claude CLI expects
            tools_str = " ".join(self.config.tool_restrictions.allowed_tools)
            command.extend(["--allowedTools", tools_str])
        
        if self.config.tool_restrictions.disallowed_tools:
            # Join tools with spaces as Claude CLI expects
            tools_str = " ".join(self.config.tool_restrictions.disallowed_tools)
            command.extend(["--disallowedTools", tools_str])
        
        # Add conversation flags
        if self.config.conversation_config.continue_last:
            command.append("--continue")
        elif self.config.conversation_config.resume_session_id:
            command.extend(["--resume", self.config.conversation_config.resume_session_id])
        
        # Add system prompt
        if self.config.system_prompt_config.system_prompt:
            command.extend(["--append-system-prompt", self.config.system_prompt_config.system_prompt])
        
        # Add additional directories
        if self.config.directory_config.additional_dirs:
            # Add each directory as a separate argument
            command.append("--add-dir")
            command.extend(self.config.directory_config.additional_dirs)
        
        # Add any additional custom flags
        if self.config.command_flags.custom_flags:
            for flag, value in self.config.command_flags.custom_flags.items():
                if flag in self.config.command_flags.allowed_flags:
                    # Skip flags we've already handled above
                    if flag not in ["-d", "--debug", "--input-format", "--model", 
                                   "--fallback-model", "--allowedTools", "--disallowedTools",
                                   "-c", "--continue", "-r", "--resume", "--add-dir", 
                                   "--append-system-prompt"]:
                        if value:
                            command.extend([flag, value])
                        else:
                            command.append(flag)
        
        # Add prompt last
        command.append(prompt)
        return command
    
    def _check_rate_limit(self):
        """Check and enforce rate limits."""
        if not self.rate_limiter or not self.config.rate_limit.enabled:
            return
            
        should_delay, delay_seconds = self.rate_limiter.should_delay(self.config.rate_limit)
        if should_delay:
            time.sleep(delay_seconds)
    
    def _should_retry(self, error: Exception) -> bool:
        """Check if error should trigger a retry."""
        error_type = type(error).__name__
        return error_type in self.config.retry.retry_on
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        delay = min(
            self.config.retry.initial_delay * (self.config.retry.exponential_base ** attempt),
            self.config.retry.max_delay
        )
        return delay
    
    def execute(self, prompt: str, timeout: Optional[int] = None) -> ClaudeResponse:
        """Execute a Claude command with retry logic and rate limiting.
        
        Args:
            prompt: The prompt to send to Claude
            timeout: Command timeout in seconds
            
        Returns:
            ClaudeResponse object containing parsed response data
        """
        timeout = timeout or self.config.default_timeout
        command = self._build_command(prompt)
        
        last_error = None
        for attempt in range(self.config.retry.max_retries + 1):
            try:
                # Check rate limit
                self._check_rate_limit()
                
                # Execute command
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=True
                )
                
                # Record successful request
                if self.rate_limiter:
                    self.rate_limiter.record_request()
                
                # Parse response
                response = parse_claude_stream(result.stdout)
                
                # Update session if enabled
                if self.session and response.system_init:
                    self.session.session_id = response.system_init.session_id
                    for resp in response.assistant_responses:
                        self.session.add_response(resp)
                    for resp in response.user_responses:
                        self.session.add_response(resp)
                    if response.result_summary:
                        self.session.total_cost += response.result_summary.total_cost_usd
                
                # Save session if configured
                if self.session and self.config.session.auto_save and self.config.session.persist_to_file:
                    self.save_session()
                
                return response
                
            except subprocess.TimeoutExpired as e:
                last_error = TimeoutError(f"Claude command timed out after {timeout} seconds")
                if self._should_retry(last_error) and attempt < self.config.retry.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    time.sleep(delay)
                    continue
                raise last_error from e
                
            except subprocess.CalledProcessError as e:
                last_error = RuntimeError(f"Claude command failed: {e.stderr}")
                if self._should_retry(last_error) and attempt < self.config.retry.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    time.sleep(delay)
                    continue
                raise last_error from e
            
            except Exception as e:
                if self._should_retry(e) and attempt < self.config.retry.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    time.sleep(delay)
                    continue
                raise
        
        # Should never reach here
        raise last_error if last_error else RuntimeError("Unexpected error in retry logic")
    
    def execute_stream(self, prompt: str, timeout: Optional[int] = None) -> Generator[Union[SystemInit, AssistantResponse, UserResponse, ResultSummary, str], None, None]:
        """Execute Claude command and stream responses in real-time.
        
        Args:
            prompt: The prompt to send to Claude
            timeout: Command timeout in seconds
            
        Yields:
            Parsed events or raw JSON strings based on config
        """
        timeout = timeout or self.config.default_timeout
        command = self._build_command(prompt)
        
        # Check rate limit
        self._check_rate_limit()
        
        # Create process
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0  # Unbuffered for full output capture
        )
        
        # Record request
        if self.rate_limiter:
            self.rate_limiter.record_request()
        
        # Create streaming parser
        stream_parser = StreamingResponseParser(self.config.streaming)
        
        try:
            # Set timeout
            start_time = time.time()
            
            # Read output line by line
            while True:
                if timeout and (time.time() - start_time) > timeout:
                    process.kill()
                    raise TimeoutError(f"Claude command timed out after {timeout} seconds")
                
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                    
                if line:
                    # Parse and yield events
                    for event in stream_parser.parse_chunk(line):
                        yield event
                        
                        # Update session if it's a response
                        if self.session and isinstance(event, (AssistantResponse, UserResponse)):
                            self.session.add_response(event)
            
            # Check for errors
            if process.returncode != 0:
                stderr = process.stderr.read()
                raise RuntimeError(f"Claude command failed: {stderr}")
            
            # Flush remaining content
            yield from stream_parser.flush()
            
            # Get final response for session update
            if self.session:
                response = stream_parser.get_response()
                if response.result_summary:
                    self.session.total_cost += response.result_summary.total_cost_usd
                
                # Save session if configured
                if self.config.session.auto_save and self.config.session.persist_to_file:
                    self.save_session()
                    
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    
    def ask(self, prompt: str, timeout: Optional[int] = None) -> str:
        """Simple method to get text response from Claude.
        
        Args:
            prompt: The prompt to send to Claude
            timeout: Command timeout in seconds
            
        Returns:
            The text response from Claude
        """
        response = self.execute(prompt, timeout)
        parser = ClaudeResponseParser()
        parser.assistant_responses = response.assistant_responses
        return parser.get_message_text()
    
    def execute_with_metrics(self, prompt: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Execute command and return response with metrics.
        
        Args:
            prompt: The prompt to send to Claude
            timeout: Command timeout in seconds
            
        Returns:
            Dictionary containing response text, usage metrics, and cost
        """
        response = self.execute(prompt, timeout)
        parser = ClaudeResponseParser()
        parser.assistant_responses = response.assistant_responses
        parser.result_summary = response.result_summary
        
        return {
            "text": parser.get_message_text(),
            "successful": parser.was_successful(),
            "usage": parser.get_usage_summary().model_dump() if parser.get_usage_summary() else None,
            "cost_usd": parser.get_cost(),
            "duration_ms": response.result_summary.duration_ms if response.result_summary else None,
            "model": response.assistant_response.message.model if response.assistant_response else None,
            "session_id": self.session.session_id if self.session else None,
            "total_session_cost": self.session.total_cost if self.session else None
        }
    
    def set_custom_flags(self, flags: Dict[str, str]):
        """Set custom command flags.
        
        Args:
            flags: Dictionary of flag names and values
        """
        self.config.command_flags.custom_flags = flags
    
    def set_debug(self, enabled: bool = True):
        """Enable or disable debug mode.
        
        Args:
            enabled: Whether to enable debug mode
        """
        self.config.debug.enabled = enabled
    
    def set_model(self, model: str, fallback_model: Optional[str] = None):
        """Set the model to use.
        
        Args:
            model: Model name or alias (e.g., 'sonnet', 'opus', or full name)
            fallback_model: Optional fallback model when primary is overloaded
        """
        self.config.claude_model_config.model = model
        if fallback_model:
            self.config.claude_model_config.fallback_model = fallback_model
    
    def set_tool_restrictions(self, allowed_tools: Optional[List[str]] = None, 
                            disallowed_tools: Optional[List[str]] = None):
        """Set tool restrictions.
        
        Args:
            allowed_tools: List of allowed tool patterns (e.g., ["Bash(git:*)", "Edit"])
            disallowed_tools: List of disallowed tool patterns
        """
        if allowed_tools is not None:
            self.config.tool_restrictions.allowed_tools = allowed_tools
        if disallowed_tools is not None:
            self.config.tool_restrictions.disallowed_tools = disallowed_tools
    
    def add_directories(self, directories: List[str]):
        """Add additional directories for tool access.
        
        Args:
            directories: List of directory paths to allow access to
        """
        self.config.directory_config.additional_dirs.extend(directories)
    
    def continue_conversation(self):
        """Continue the most recent conversation."""
        self.config.conversation_config.continue_last = True
        self.config.conversation_config.resume_session_id = None
    
    def resume_conversation(self, session_id: str):
        """Resume a specific conversation.
        
        Args:
            session_id: The session ID to resume
        """
        self.config.conversation_config.continue_last = False
        self.config.conversation_config.resume_session_id = session_id
    
    def set_system_prompt(self, system_prompt: str):
        """Set the system prompt to be appended to all requests.
        
        Args:
            system_prompt: The system prompt text to append
        """
        self.config.system_prompt_config.system_prompt = system_prompt
    
    def get_session(self) -> Optional[Session]:
        """Get current session."""
        return self.session
    
    def clear_session(self):
        """Clear session history."""
        if self.session:
            self.session.clear_history()
    
    def save_session(self, path: Optional[str] = None):
        """Save session to file.
        
        Args:
            path: File path to save session (uses config path if not provided)
        """
        if not self.session:
            return
            
        save_path = path or self.config.session.persist_to_file
        if save_path:
            with open(save_path, 'wb') as f:
                pickle.dump(self.session, f)
    
    def load_session(self, path: str):
        """Load session from file.
        
        Args:
            path: File path to load session from
        """
        with open(path, 'rb') as f:
            self.session = pickle.load(f)
    
    def get_rate_limit_status(self) -> Optional[Dict[str, Any]]:
        """Get current rate limit status."""
        if not self.rate_limiter:
            return None
            
        return {
            "requests_this_minute": self.rate_limiter.requests_this_minute,
            "requests_this_hour": self.rate_limiter.requests_this_hour,
            "minute_limit": self.config.rate_limit.requests_per_minute,
            "hour_limit": self.config.rate_limit.requests_per_hour,
            "next_minute_reset": self.rate_limiter.minute_reset_time,
            "next_hour_reset": self.rate_limiter.hour_reset_time
        }


class AsyncClaudeAPI(ClaudeAPI):
    """Asynchronous version of Claude API with all advanced features."""
    
    def __init__(self, config: Optional[APIConfig] = None):
        """Initialize Async Claude API with configuration.
        
        Args:
            config: API configuration object
        """
        super().__init__(config)
    
    async def execute_async(self, prompt: str, timeout: Optional[int] = None) -> ClaudeResponse:
        """Execute Claude command asynchronously with retry logic.
        
        Args:
            prompt: The prompt to send to Claude
            timeout: Command timeout in seconds
            
        Returns:
            ClaudeResponse object containing parsed response data
        """
        timeout = timeout or self.config.default_timeout
        command = self._build_command(prompt)
        
        last_error = None
        for attempt in range(self.config.retry.max_retries + 1):
            try:
                # Check rate limit
                if self.rate_limiter:
                    await asyncio.get_event_loop().run_in_executor(None, self._check_rate_limit)
                
                # Create subprocess
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # Wait for completion with timeout
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                if process.returncode != 0:
                    raise RuntimeError(f"Claude command failed: {stderr.decode()}")
                
                # Record successful request
                if self.rate_limiter:
                    self.rate_limiter.record_request()
                
                # Parse response
                response = parse_claude_stream(stdout.decode())
                
                # Update session
                if self.session and response.system_init:
                    self.session.session_id = response.system_init.session_id
                    for resp in response.assistant_responses:
                        self.session.add_response(resp)
                    for resp in response.user_responses:
                        self.session.add_response(resp)
                    if response.result_summary:
                        self.session.total_cost += response.result_summary.total_cost_usd
                
                # Save session if configured
                if self.session and self.config.session.auto_save and self.config.session.persist_to_file:
                    await asyncio.get_event_loop().run_in_executor(None, self.save_session)
                
                return response
                
            except asyncio.TimeoutError as e:
                if process:
                    process.kill()
                    await process.wait()
                    
                last_error = TimeoutError(f"Claude command timed out after {timeout} seconds")
                if self._should_retry(last_error) and attempt < self.config.retry.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    await asyncio.sleep(delay)
                    continue
                raise last_error from e
                
            except Exception as e:
                if self._should_retry(e) and attempt < self.config.retry.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    await asyncio.sleep(delay)
                    continue
                raise
        
        raise last_error if last_error else RuntimeError("Unexpected error in retry logic")
    
    async def execute_stream_async(self, prompt: str, timeout: Optional[int] = None) -> AsyncGenerator[Union[SystemInit, AssistantResponse, UserResponse, ResultSummary, str], None]:
        """Execute Claude command and stream responses asynchronously.
        
        Args:
            prompt: The prompt to send to Claude
            timeout: Command timeout in seconds
            
        Yields:
            Parsed events or raw JSON strings based on config
        """
        timeout = timeout or self.config.default_timeout
        command = self._build_command(prompt)
        
        # Check rate limit
        if self.rate_limiter:
            await asyncio.get_event_loop().run_in_executor(None, self._check_rate_limit)
        
        # Create subprocess
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Record request
        if self.rate_limiter:
            self.rate_limiter.record_request()
        
        # Create streaming parser
        stream_parser = StreamingResponseParser(self.config.streaming)
        
        try:
            # Set timeout
            start_time = asyncio.get_event_loop().time()
            
            # Read output asynchronously
            while True:
                if timeout and (asyncio.get_event_loop().time() - start_time) > timeout:
                    process.kill()
                    await process.wait()
                    raise TimeoutError(f"Claude command timed out after {timeout} seconds")
                
                try:
                    line = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=1.0  # Check timeout every second
                    )
                except asyncio.TimeoutError:
                    if process.returncode is not None:
                        break
                    continue
                
                if not line and process.returncode is not None:
                    break
                    
                if line:
                    # Parse and yield events
                    for event in stream_parser.parse_chunk(line.decode()):
                        yield event
                        
                        # Update session if it's a response
                        if self.session and isinstance(event, (AssistantResponse, UserResponse)):
                            self.session.add_response(event)
            
            # Check for errors
            if process.returncode != 0:
                stderr = await process.stderr.read()
                raise RuntimeError(f"Claude command failed: {stderr.decode()}")
            
            # Flush remaining content
            for event in stream_parser.flush():
                yield event
            
            # Get final response for session update
            if self.session:
                response = stream_parser.get_response()
                if response.result_summary:
                    self.session.total_cost += response.result_summary.total_cost_usd
                
                # Save session if configured
                if self.config.session.auto_save and self.config.session.persist_to_file:
                    await asyncio.get_event_loop().run_in_executor(None, self.save_session)
                    
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()
    
    async def ask_async(self, prompt: str, timeout: Optional[int] = None) -> str:
        """Asynchronously get text response from Claude.
        
        Args:
            prompt: The prompt to send to Claude
            timeout: Command timeout in seconds
            
        Returns:
            The text response from Claude
        """
        response = await self.execute_async(prompt, timeout)
        parser = ClaudeResponseParser()
        parser.assistant_responses = response.assistant_responses
        return parser.get_message_text()


# Convenience functions
def ask_claude(prompt: str, config: Optional[APIConfig] = None) -> str:
    """Quick function to ask Claude a question.
    
    Args:
        prompt: The prompt to send to Claude
        config: Optional API configuration
        
    Returns:
        The text response from Claude
    """
    api = ClaudeAPI(config)
    return api.ask(prompt)


def create_api_with_config(**kwargs) -> ClaudeAPI:
    """Create API with custom configuration.
    
    Args:
        **kwargs: Configuration parameters
        
    Returns:
        Configured ClaudeAPI instance
    """
    config = APIConfig(**kwargs)
    return ClaudeAPI(config)