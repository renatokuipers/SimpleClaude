"""Ultra-simple Claude API wrapper that even toddlers can use."""

import time
import sys
from typing import Optional, Callable, List
from datetime import datetime

# Rich library for beautiful, color-coded terminal output
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from rich import print as rprint
from rich.rule import Rule

try:
    from ..claude_api.api import ClaudeAPI, AsyncClaudeAPI
    from ..claude_api.models import (
        APIConfig, SessionConfig, RateLimitConfig, RetryConfig, 
        StreamConfig, DebugConfig, ClaudeModelConfig, AssistantResponse, 
        UserResponse, SystemInit, ResultSummary, TextContent, ThinkingContent,
        ToolUseContent, ToolResultContent, SystemPromptConfig
    )
except ImportError:
    # Handle case when running directly or from different directory
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from claude_api.api import ClaudeAPI, AsyncClaudeAPI
    from claude_api.models import (
        APIConfig, SessionConfig, RateLimitConfig, RetryConfig, 
        StreamConfig, DebugConfig, ClaudeModelConfig, AssistantResponse, 
        UserResponse, SystemInit, ResultSummary, TextContent, ThinkingContent,
        ToolUseContent, ToolResultContent, SystemPromptConfig
    )
try:
    from .models import SimpleResponse, SimpleMetrics, SimpleConfig
except ImportError:
    # Handle case when running directly
    from models import SimpleResponse, SimpleMetrics, SimpleConfig


class SimpleClaudeAPI:
    """Ultra-simple Claude API that's foolproof and always streams with metrics."""
    
    def __init__(self, config: Optional[SimpleConfig] = None):
        """Initialize the simple Claude API.
        
        Args:
            config: Optional simple configuration. Uses sensible defaults if not provided.
        """
        self.config = config or SimpleConfig()
        self.session_metrics = SimpleMetrics(
            total_cost=0.0,
            total_tokens=0,
            requests_count=0,
            average_response_time=0.0
        )
        self._response_times: List[float] = []
        
        # Configure the underlying Claude API with sensible defaults
        api_config = APIConfig(
            session=SessionConfig(
                maintain_context=True,
                max_history_size=50,
                auto_save=True
            ),
            rate_limit=RateLimitConfig(
                requests_per_minute=30,
                requests_per_hour=500,
                enabled=True
            ),
            retry=RetryConfig(
                max_retries=self.config.max_retries,
                initial_delay=1.0,
                max_delay=10.0,
                retry_on=["TimeoutError", "ConnectionError", "RuntimeError"]
            ),
            streaming=StreamConfig(
                buffer_size=65536,  # Increased buffer size for full response capture
                timeout_between_chunks=30.0,
                yield_raw=False
            ),
            debug=DebugConfig(enabled=self.config.verbose),
            claude_model_config=ClaudeModelConfig(
                model=self.config.model,
                fallback_model="haiku" if self.config.model != "haiku" else "sonnet"  # Smart fallback
            ),
            system_prompt_config=SystemPromptConfig(
                system_prompt=self.config.system_prompt
            ),
            default_timeout=self.config.timeout_seconds
        )
        
        # Handle conversation continuation
        if self.config.auto_continue:
            api_config.conversation_config.continue_last = True
        
        self.claude_api = ClaudeAPI(api_config)
        
        # Initialize rich console for color-coded output
        self.console = Console()
        
        # Welcome message
        if not self.config.verbose:
            self.console.print("\n")
            self.console.print(Panel.fit(
                "🤖 [bold green]Simple Claude API ready![/bold green] Just call .ask() to start chatting.",
                border_style="green"
            ))
            self.console.print("")
    
    def ask(self, 
            prompt: str, 
            callback: Optional[Callable[[str], None]] = None,
            show_thinking: Optional[bool] = None) -> SimpleResponse:
        """Ask Claude a question with automatic streaming and metrics.
        
        Args:
            prompt: Your question or request to Claude
            callback: Optional function to handle streaming text (gets called with each chunk)
            show_thinking: Whether to show Claude's thinking process (overrides config)
            
        Returns:
            SimpleResponse with the complete answer and metrics
            
        Example:
            >>> claude = SimpleClaudeAPI()
            >>> response = claude.ask("What is Python?")
            >>> print(f"Cost: ${response.cost}")
        """
        if not prompt or not prompt.strip():
            self.console.print("\n")
            self.console.print("[bold red]❌ Error: Please provide a non-empty prompt![/bold red]")
            self.console.print("")
            return SimpleResponse(
                text="Error: Empty prompt provided",
                cost=0.0,
                tokens_used=0,
                model="none",
                success=False,
                tool_uses=[],
                tool_results=[]
            )
        
        self.console.print("\n")
        self.console.print(Rule("[bold blue]New Claude Request[/bold blue]", style="blue"))
        self.console.print(f"[bold cyan]🤔 Asking Claude:[/bold cyan] [white]{prompt}[/white]")
        self.console.print("[yellow]💭 Thinking and responding...[/yellow]")
        self.console.print("")
        
        start_time = time.time()
        response_text_parts = []
        thinking_parts = []
        tool_uses = []
        tool_results = []
        
        # Variables to capture metrics from streaming
        cost = 0.0
        tokens = 0
        model = "unknown"
        success = True
        session_id = None
        
        # Use custom callback or default console output with rich formatting
        def stream_handler(text: str):
            response_text_parts.append(text)
            if callback:
                callback(text)
            else:
                self.console.print(f"[green]{text}[/green]", end='', highlight=False)
        
        try:
            # Stream the response
            for event in self.claude_api.execute_stream(prompt):
                if isinstance(event, AssistantResponse):
                    # Capture model name from assistant response
                    model = event.message.model
                    for content in event.message.content:
                        if isinstance(content, TextContent):
                            stream_handler(content.text)
                        elif isinstance(content, ThinkingContent):
                            thinking_parts.append(content.thinking)
                            if show_thinking or (show_thinking is None and self.config.show_thinking):
                                self.console.print("\n")
                                self.console.print(Panel(
                                    f"[italic cyan]{content.thinking}[/italic cyan]",
                                    title="[bold yellow]💭 Claude's Thinking[/bold yellow]",
                                    border_style="yellow",
                                    expand=False
                                ))
                                self.console.print("")
                        elif isinstance(content, ToolUseContent):
                            # Capture tool use
                            tool_use_dict = {
                                "id": content.id,
                                "name": content.name,
                                "input": content.input
                            }
                            tool_uses.append(tool_use_dict)
                            
                            # Display tool use in real-time
                            self.console.print("\n")
                            self.console.print(Panel(
                                f"[bold magenta]🔧 Using Tool:[/bold magenta] [white]{content.name}[/white]\n"
                                f"[dim]Input: {str(content.input)}[/dim]",
                                title="[bold magenta]Tool Use[/bold magenta]",
                                border_style="magenta",
                                expand=False
                            ))
                            self.console.print("")
                elif isinstance(event, UserResponse):
                    # Capture tool results from user messages
                    for content in event.message.content:
                        if isinstance(content, ToolResultContent):
                            tool_result_dict = {
                                "tool_use_id": content.tool_use_id,
                                "content": content.content,
                                "is_error": content.is_error
                            }
                            tool_results.append(tool_result_dict)
                            
                            # Display tool result in real-time
                            result_style = "red" if content.is_error else "green"
                            result_icon = "❌" if content.is_error else "✅"
                            
                            self.console.print("\n")
                            self.console.print(Panel(
                                f"[bold {result_style}]{result_icon} Tool Result[/bold {result_style}]\n"
                                f"[dim]{str(content.content)}[/dim]",
                                title=f"[bold {result_style}]Tool Response[/bold {result_style}]",
                                border_style=result_style,
                                expand=False
                            ))
                            self.console.print("")
                elif isinstance(event, SystemInit):
                    # Capture session ID from system initialization
                    session_id = event.session_id
                elif isinstance(event, ResultSummary):
                    # Capture metrics from streaming response
                    cost = event.total_cost_usd
                    if event.usage:
                        tokens = event.usage.input_tokens + event.usage.output_tokens
                    success = not event.is_error
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Process response
            complete_text = ''.join(response_text_parts)
            thinking_text = '\n'.join(thinking_parts) if thinking_parts else None
            
            # Try to get model info from the streaming events
            # Note: If model wasn't captured from streaming, we keep "unknown"
            
            # Update session metrics
            self.session_metrics.total_cost += cost
            self.session_metrics.total_tokens += tokens
            self.session_metrics.requests_count += 1
            self._response_times.append(duration)
            self.session_metrics.average_response_time = sum(self._response_times) / len(self._response_times)
            
            # Create response object
            simple_response = SimpleResponse(
                text=complete_text,
                cost=cost,
                tokens_used=tokens,
                model=model,
                success=success,
                session_id=session_id,
                duration_seconds=duration,
                thinking=thinking_text,
                tool_uses=tool_uses,
                tool_results=tool_results
            )
            
            # Show metrics if enabled
            if self.config.show_metrics:
                self.console.print("\n")
                self.console.print(Rule("[bold green]Response Complete[/bold green]", style="green"))
                
                # Create metrics panel
                metrics_text = (
                    f"[bold green]✅ Response completed in {duration:.1f}s[/bold green]\n"
                    f"[yellow]💰 Cost:[/yellow] [white]${cost:.4f}[/white] | "
                    f"[cyan]🎯 Tokens:[/cyan] [white]{tokens}[/white] | "
                    f"[magenta]🤖 Model:[/magenta] [white]{model}[/white]\n\n"
                    f"[bold blue]📊 Session Stats:[/bold blue]\n"
                    f"[white]💵 Total Cost: ${self.session_metrics.total_cost:.4f}[/white]\n"
                    f"[white]🎯 Total Tokens: {self.session_metrics.total_tokens}[/white]\n"
                    f"[white]📨 Requests: {self.session_metrics.requests_count}[/white]\n"
                    f"[white]⏱️  Avg Response Time: {self.session_metrics.average_response_time:.1f}s[/white]"
                )
                
                self.console.print(Panel(
                    metrics_text,
                    title="[bold blue]📊 Metrics & Performance[/bold blue]",
                    border_style="blue",
                    expand=False
                ))
                self.console.print("")
            
            return simple_response
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            self.console.print("\n")
            self.console.print(Panel(
                f"[bold red]❌ Something went wrong:[/bold red] [white]{str(e)}[/white]\n\n"
                f"[yellow]🔄 Don't worry, this happens sometimes. Try again![/yellow]",
                title="[bold red]Error[/bold red]",
                border_style="red",
                expand=False
            ))
            self.console.print("")
            
            # Return error response
            return SimpleResponse(
                text=f"Error: {str(e)}",
                cost=0.0,
                tokens_used=0,
                model="unknown",
                success=False,
                duration_seconds=duration,
                tool_uses=[],
                tool_results=[]
            )
    
    def chat(self, prompts: List[str]) -> List[SimpleResponse]:
        """Have a multi-turn conversation with Claude.
        
        Args:
            prompts: List of prompts to ask in sequence
            
        Returns:
            List of SimpleResponse objects
        """
        responses = []
        self.console.print("\n")
        self.console.print(Panel.fit(
            f"[bold cyan]🗣️ Starting conversation with {len(prompts)} messages...[/bold cyan]",
            border_style="cyan"
        ))
        self.console.print("")
        
        for i, prompt in enumerate(prompts, 1):
            self.console.print("\n")
            self.console.print(Rule(f"[bold purple]💬 Message {i}/{len(prompts)}[/bold purple]", style="purple"))
            response = self.ask(prompt)
            responses.append(response)
            
            if not response.success:
                self.console.print(f"[bold red]❌ Stopping conversation due to error in message {i}[/bold red]")
                break
        
        self.console.print("\n")
        self.console.print(Panel.fit(
            f"[bold green]🎉 Conversation completed! {len(responses)} responses received.[/bold green]",
            border_style="green"
        ))
        self.console.print("")
        return responses
    
    def get_metrics(self) -> SimpleMetrics:
        """Get current session metrics.
        
        Returns:
            SimpleMetrics object with current statistics
        """
        return self.session_metrics
    
    def reset_metrics(self):
        """Reset session metrics to zero."""
        self.session_metrics = SimpleMetrics(
            total_cost=0.0,
            total_tokens=0,
            requests_count=0,
            average_response_time=0.0
        )
        self._response_times.clear()
        self.console.print("[bold green]📊 Session metrics reset![/bold green]")
    
    def change_model(self, model: str):
        """Change the Claude model.
        
        Args:
            model: Model name ('sonnet', 'opus', 'haiku', or full model name)
        """
        self.config.model = model
        fallback = "haiku" if model != "haiku" else "sonnet"
        self.claude_api.set_model(model, fallback)
        self.console.print(f"[bold cyan]🤖 Switched to model:[/bold cyan] [white]{model}[/white] [dim](fallback: {fallback})[/dim]")
    
    def enable_thinking(self, enabled: bool = True):
        """Enable or disable showing Claude's thinking process.
        
        Args:
            enabled: Whether to show thinking
        """
        self.config.show_thinking = enabled
        status = "enabled" if enabled else "disabled"
        self.console.print(f"[bold yellow]🧠 Thinking display {status}[/bold yellow]")
    
    def enable_metrics(self, enabled: bool = True):
        """Enable or disable metrics display.
        
        Args:
            enabled: Whether to show metrics
        """
        self.config.show_metrics = enabled
        status = "enabled" if enabled else "disabled"
        self.console.print(f"[bold blue]📊 Metrics display {status}[/bold blue]")
    
    def set_system_prompt(self, system_prompt: Optional[str] = None):
        """Set or clear the system prompt that gets appended to all requests.
        
        Args:
            system_prompt: The system prompt text to append to all requests, or None to clear
        """
        self.config.system_prompt = system_prompt
        self.claude_api.set_system_prompt(system_prompt)
        
        if system_prompt:
            self.console.print(f"[bold green]📝 System prompt set:[/bold green] [white]{system_prompt}[/white]")
        else:
            self.console.print("[bold green]📝 System prompt cleared[/bold green]")
    
    def help(self):
        """Show help information."""
        help_text = """
🤖 Simple Claude API Help

Basic Usage:
  claude = SimpleClaudeAPI()
  response = claude.ask("Your question here")

Methods:
  .ask(prompt, callback=None)     - Ask a question (with streaming)
  .chat([prompt1, prompt2, ...])  - Multi-turn conversation
  .get_metrics()                  - View session statistics
  .reset_metrics()                - Reset statistics
  .change_model(model)            - Switch models
  .enable_thinking(True/False)    - Show/hide thinking
  .enable_metrics(True/False)     - Show/hide metrics
  .set_system_prompt(prompt)      - Set system prompt for all requests
  .help()                         - Show this help

Examples:
  # Basic usage
  claude.ask("What is Python?")
  
  # With custom callback
  def my_callback(text):
      print(f"Claude: {text}", end='')
  claude.ask("Tell me a joke", callback=my_callback)
  
  # Multiple questions
  claude.chat(["Hi!", "What's the weather like?", "Thanks!"])
  
  # With system prompt
  claude.set_system_prompt("You are a helpful Python tutor.")
  claude.ask("How do I create a list?")
  
  # Initialize with system prompt
  config = SimpleConfig(system_prompt="You are a creative writer.")
  claude = SimpleClaudeAPI(config)

Models available: 'sonnet' (default), 'opus', 'haiku'
        """
        self.console.print(Panel(
            help_text,
            title="[bold blue]🤖 Simple Claude API Help[/bold blue]",
            border_style="blue",
            expand=True
        ))


# Convenience function for one-off questions
def ask_claude_simple(prompt: str, 
                     model: str = "sonnet",
                     show_thinking: bool = False,
                     system_prompt: Optional[str] = None) -> SimpleResponse:
    """Quick function to ask Claude a single question.
    
    Args:
        prompt: Your question
        model: Model to use ('sonnet', 'opus', 'haiku')
        show_thinking: Whether to show thinking process
        system_prompt: Optional system prompt to append
        
    Returns:
        SimpleResponse with answer
    """
    config = SimpleConfig(model=model, show_thinking=show_thinking, system_prompt=system_prompt)
    claude = SimpleClaudeAPI(config)
    return claude.ask(prompt)


# Even simpler function that just prints the answer
def claude_say(prompt: str):
    """Ultra-simple function - just ask and Claude will respond.
    
    Args:
        prompt: Your question
    """
    ask_claude_simple(prompt)

