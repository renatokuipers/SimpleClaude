# 🐍 SimpleClaude Python - Ultra-Simple Claude API Wrapper

> **Beautiful, streaming Claude conversations in Python with zero configuration**

Transform the Claude CLI into an elegant Python API that's as easy to use as `print()` but as powerful as the full Claude experience.

## 🚀 Installation

### Prerequisites
```bash
# Install Claude CLI globally
npm install -g @anthropic-ai/claude-cli

# Configure with your API key (one-time setup)
claude auth login
```

### Install Dependencies
```bash
# Using pip
pip install rich pydantic

# Using uv (recommended)
uv pip install rich pydantic
```

## ⚡ Quick Start

### Ultra-Simple Usage
```python
from simple_claude.simple_api import SimpleClaudeAPI

# Create instance (uses sensible defaults)
claude = SimpleClaudeAPI()

# Ask a question and get streaming response
response = claude.ask("Explain quantum computing in simple terms")

print(f"Answer: {response.text}")
print(f"Cost: ${response.cost:.4f}")
print(f"Tokens: {response.tokens_used}")
```

### Even Simpler - One-Liner Functions
```python
from simple_claude.simple_api import ask_claude_simple, claude_say

# Get response object
response = ask_claude_simple("What is Python?")

# Just print the answer (fire and forget)
claude_say("Tell me a joke!")
```

## 🎨 Rich Terminal Output

When you run the code above, you'll see beautiful, real-time output:

```
┌─ New Claude Request ─────────────────────────────────────────────────┐
🤔 Asking Claude: Explain quantum computing in simple terms
💭 Thinking and responding...

Quantum computing is like having a magical computer that can explore 
many possibilities simultaneously...

┌─ 📊 Metrics & Performance ─────────────────────────────────────────┐
│ ✅ Response completed in 3.2s                                      │
│ 💰 Cost: $0.0032 | 🎯 Tokens: 240 | 🤖 Model: claude-3-sonnet    │
└─────────────────────────────────────────────────────────────────────┘
```

## 🔧 Configuration & Customization

### Basic Configuration
```python
from simple_claude.models import SimpleConfig
from simple_claude.simple_api import SimpleClaudeAPI

# Configure before creating instance
config = SimpleConfig(
    model="opus",                    # 'sonnet', 'opus', or 'haiku'
    show_thinking=True,              # Show Claude's reasoning process
    show_metrics=True,               # Display cost/token metrics  
    auto_continue=True,              # Continue previous conversations
    max_retries=3,                   # Retry failed requests
    timeout_seconds=300,             # Request timeout
    verbose=False,                   # Show debug information
    system_prompt="You are a helpful Python tutor."  # Custom system prompt
)

claude = SimpleClaudeAPI(config)
```

### Runtime Configuration
```python
claude = SimpleClaudeAPI()

# Change settings on the fly
claude.change_model("opus")                           # Switch models
claude.enable_thinking(True)                         # Show reasoning
claude.enable_metrics(False)                        # Hide metrics
claude.set_system_prompt("You are a creative writer.")  # Set personality
```

## 🗣️ Multi-Turn Conversations

### Sequential Questions
```python
claude = SimpleClaudeAPI()

# Ask multiple related questions
responses = claude.chat([
    "Hi! I'm learning Python.",
    "What are the most important concepts to master?", 
    "Can you show me an example of a class?",
    "Thanks for the help!"
])

for i, response in enumerate(responses, 1):
    print(f"Response {i}: {response.text[:100]}...")
```

### Interactive Conversation
```python
claude = SimpleClaudeAPI()

while True:
    question = input("\n🤔 Ask Claude: ")
    if question.lower() in ['exit', 'quit', 'bye']:
        break
    
    response = claude.ask(question)
    # Response streams live to terminal automatically!
```

## 🧠 Thinking Process (When Available)

```python
# Show Claude's reasoning process
claude = SimpleClaudeAPI()
response = claude.ask(
    "Solve this math problem: If a train travels 120 miles in 2 hours, what's its speed?",
    show_thinking=True  # Override default setting for this question
)

# Thinking will display in a special panel during streaming
```

## 🔧 Tool Use Visualization

When Claude uses tools (like web search, code execution), you'll see real-time visualization:

```
┌─ Tool Use ─────────────────────────────────────────┐
│ 🔧 Using Tool: WebSearch                           │
│ Input: {"query": "latest Python 3.12 features"}   │
└─────────────────────────────────────────────────────┘

┌─ Tool Response ────────────────────────────────────┐
│ ✅ Tool Result                                     │
│ Python 3.12 introduces improved error messages... │
└─────────────────────────────────────────────────────┘
```

## 📊 Metrics and Cost Tracking

### Session Metrics
```python
claude = SimpleClaudeAPI()

# Ask several questions
claude.ask("What is Python?")
claude.ask("How do I install packages?")
claude.ask("What are virtual environments?")

# Get session statistics
metrics = claude.get_metrics()
print(f"Total cost: ${metrics.total_cost:.4f}")
print(f"Total tokens: {metrics.total_tokens}")
print(f"Requests made: {metrics.requests_count}")
print(f"Average response time: {metrics.average_response_time:.1f}s")

# Reset metrics
claude.reset_metrics()
```

### Per-Response Metrics
```python
response = claude.ask("Explain machine learning")

print(f"This question cost: ${response.cost:.4f}")
print(f"Tokens used: {response.tokens_used}")
print(f"Model: {response.model}")
print(f"Duration: {response.duration_seconds:.1f}s")
print(f"Success: {response.success}")
```

## 🎛️ Advanced Features

### Custom Streaming Callback
```python
def my_custom_handler(text_chunk):
    """Handle each piece of streaming text"""
    print(f"[CLAUDE] {text_chunk}", end='', flush=True)

response = claude.ask(
    "Write a short poem about coding",
    callback=my_custom_handler
)
```

### Model Switching
```python
claude = SimpleClaudeAPI()

# Start with fast, cheap model
claude.change_model("haiku")
quick_response = claude.ask("What's 2+2?")

# Switch to powerful model for complex task
claude.change_model("opus") 
detailed_response = claude.ask("Explain the theory of relativity")
```

### Error Handling
```python
try:
    response = claude.ask("Your question here")
    if response.success:
        print(f"Success! Answer: {response.text}")
    else:
        print(f"Error occurred: {response.text}")
except Exception as e:
    print(f"Network or CLI error: {e}")
```

## 🛠️ Underlying Architecture

This wrapper provides three layers:

1. **`SimpleClaudeAPI`** - The main user-friendly class (recommended)
2. **`ClaudeAPI`** - Advanced API with full configuration options  
3. **Claude CLI** - The official Anthropic command-line tool

```python
# If you need advanced features, use the full API
from claude_api.api import ClaudeAPI
from claude_api.models import APIConfig

api_config = APIConfig(
    # Advanced rate limiting, retry logic, session management, etc.
)
advanced_claude = ClaudeAPI(api_config)
```

## 📝 Complete API Reference

### SimpleClaudeAPI Methods
- `ask(prompt, callback=None, show_thinking=None)` - Ask a question
- `chat(prompts)` - Multi-turn conversation  
- `get_metrics()` - Get session statistics
- `reset_metrics()` - Reset statistics to zero
- `change_model(model)` - Switch Claude model
- `enable_thinking(enabled)` - Toggle thinking display
- `enable_metrics(enabled)` - Toggle metrics display
- `set_system_prompt(prompt)` - Set personality/context
- `help()` - Show help information

### Response Object Properties
- `text` - The complete response text
- `cost` - Cost in USD for this request
- `tokens_used` - Total tokens (input + output)
- `model` - Which model was used
- `success` - Whether request succeeded
- `duration_seconds` - How long the request took
- `thinking` - Claude's reasoning (if available)
- `tool_uses` - List of tools Claude used
- `tool_results` - Results from tool usage

## 🎯 Tips & Best Practices

- **Start with `SimpleClaudeAPI()`** - covers 95% of use cases
- **Use `show_thinking=True`** for complex reasoning tasks
- **Monitor costs** with automatic metrics tracking
- **Use `haiku` model** for simple questions to save money
- **Use `opus` model** for complex analysis and reasoning
- **Set system prompts** to give Claude context about your domain

## 🐛 Troubleshooting

### Common Issues

**"claude command not found"**
```bash
npm install -g @anthropic-ai/claude-cli
```

**"Authentication required"**
```bash
claude auth login
```

**Import errors**
```bash
pip install rich pydantic
# or
uv pip install rich pydantic
```

**Slow responses**
- Try switching to `haiku` model for faster responses
- Check your internet connection
- Increase timeout in config

## 📖 More Examples

Check out the `/examples` directory for complete working examples:
- Basic Q&A scripts
- Multi-turn conversation bots  
- Cost analysis tools
- Custom streaming implementations

---

**Ready to build something amazing with Claude?** This wrapper makes it as easy as possible! 🚀