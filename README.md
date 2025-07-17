# 🤖 SimpleClaude - Ultra-Simple Claude API Wrappers

> **Transform Claude CLI into beautiful, streaming conversations with zero configuration**

SimpleClaude provides dead-simple wrappers around Anthropic's Claude CLI that make AI conversations as easy as printing "Hello World". No API keys to manage, no complex setup - just install and start chatting!

## ✨ What Makes SimpleClaude Special?

- 🎯 **Zero Configuration** - Works out of the box with sensible defaults
- 🌊 **Real-time Streaming** - See Claude think and respond live
- 💰 **Automatic Metrics** - Track costs, tokens, and performance seamlessly  
- 🎨 **Beautiful Output** - Rich, colorful terminal displays that make conversations engaging
- 🔧 **Tool Use Visualization** - Watch Claude use tools in real-time
- 🧠 **Thinking Process** - Optionally see Claude's reasoning (when available)
- 🔄 **Session Management** - Maintains conversation context automatically
- ⚡ **Smart Retries** - Handles errors and rate limits gracefully

## 🚀 Quick Start

Choose your preferred language:

### Python 🐍
```python
from simple_claude.simple_api import SimpleClaudeAPI

claude = SimpleClaudeAPI()
response = claude.ask("What's the meaning of life?")
print(f"Answer: {response.text}")
print(f"Cost: ${response.cost:.4f}")
```

### TypeScript/JavaScript 📦
```typescript
import { claude } from './claude';

const answer = await claude("What's the meaning of life?");
console.log(answer);
```

## 🎪 Live Demo

When you ask a question, you'll see something like this in your terminal:

```
┌─ New Claude Request ─────────────────────────────────────────────────┐
🤔 Asking Claude: What's the meaning of life?
💭 Thinking and responding...

The meaning of life is a profound philosophical question that has been 
contemplated for millennia. Some find meaning through relationships, 
personal growth, helping others, or pursuing their passions...

┌─ 📊 Metrics & Performance ─────────────────────────────────────────┐
│ ✅ Response completed in 2.3s                                      │
│ 💰 Cost: $0.0045 | 🎯 Tokens: 150 | 🤖 Model: claude-3-sonnet    │
│                                                                     │
│ 📊 Session Stats:                                                  │
│ 💵 Total Cost: $0.0045                                            │
│ 🎯 Total Tokens: 150                                              │
│ 📨 Requests: 1                                                     │
│ ⏱️  Avg Response Time: 2.3s                                        │
└─────────────────────────────────────────────────────────────────────┘
```

## 🌟 Core Features

| Feature | Description |
|---------|-------------|
| **Streaming Responses** | Watch Claude type in real-time, just like ChatGPT |
| **Cost Tracking** | Know exactly how much each conversation costs |
| **Session Memory** | Claude remembers your conversation history |
| **Tool Visualization** | See when Claude uses tools like web search or code execution |
| **Error Recovery** | Automatic retries with exponential backoff |
| **Multiple Models** | Easy switching between Sonnet, Opus, and Haiku |
| **Rich Formatting** | Beautiful, colorful terminal output |

## 📚 Detailed Documentation

For complete installation instructions, advanced usage, and API references:

- **[📖 Python Documentation](./Python/README.md)** - Complete Python guide with examples
- **[📖 TypeScript Documentation](./TS/README.md)** - Complete TypeScript/Node.js guide

## 🛠️ Requirements

- **Claude CLI** installed and configured (`npm install -g @anthropic-ai/claude-cli`)
- **Python 3.8+** (for Python version) with `rich` library
- **Node.js 16+** (for TypeScript version)

## 🎯 Perfect For

- 🔬 **Researchers** who need quick AI assistance with cost tracking
- 👩‍💻 **Developers** building AI-powered tools and prototypes  
- 🎓 **Students** learning about AI and natural language processing
- 📝 **Writers** who want AI collaboration with beautiful output
- 🤖 **AI Enthusiasts** who want the simplest possible Claude integration

## 🤝 Contributing

This project wraps the official Anthropic Claude CLI with a focus on simplicity and beautiful user experience. Contributions welcome!

## 📄 License

MIT License - feel free to use this in your projects!

---

**Ready to start chatting with Claude?** Pick your language and dive into the detailed documentation above! 🚀