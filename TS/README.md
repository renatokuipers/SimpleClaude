# 📦 SimpleClaude TypeScript - Ultra-Simple Claude API Wrapper

> **Beautiful, streaming Claude conversations in TypeScript/JavaScript with zero configuration**

Transform the Claude CLI into an elegant TypeScript/JavaScript API that's as easy to use as `console.log()` but as powerful as the full Claude experience.

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
# Using npm
npm install

# Using yarn
yarn install

# Using pnpm
pnpm install
```

## ⚡ Quick Start

### Ultra-Simple Usage (Recommended)
```typescript
import { claude } from './claude';

// Ask a question and get the answer
const answer = await claude("Explain quantum computing in simple terms");
console.log(answer);

// Get full response with metrics
import { claudeWithInfo } from './claude';
const response = await claudeWithInfo("What is TypeScript?");
console.log(`Answer: ${response.text}`);
console.log(`Cost: $${response.cost.toFixed(4)}`);
console.log(`Tokens: ${response.tokens_used}`);
```

### Full-Featured API
```typescript
import { SimpleClaudeAPI } from './SimpleClaude/simple_api';

// Create instance (uses sensible defaults)
const claude = new SimpleClaudeAPI();

// Ask a question and get streaming response
const response = await claude.ask("Explain quantum computing in simple terms");

console.log(`Answer: ${response.text}`);
console.log(`Cost: $${response.cost.toFixed(4)}`);
console.log(`Tokens: ${response.tokens_used}`);
```

### Multi-Turn Conversations
```typescript
import { claudeChat } from './claude';

const answers = await claudeChat([
    "Hi! I'm learning TypeScript.",
    "What are the most important concepts?", 
    "Can you show me an example of interfaces?",
    "Thanks!"
]);

answers.forEach((answer, i) => {
    console.log(`Answer ${i + 1}: ${answer.slice(0, 100)}...`);
});
```

## 🎨 Rich Terminal Output

When you run the code above, you'll see beautiful, real-time output in your terminal:

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

### Using the Simple API with Configuration
```typescript
import { SimpleClaudeAPI, SimpleConfigImpl } from './SimpleClaude/simple_api';

// Configure before creating instance
const config = new SimpleConfigImpl({
    model: "opus",                    // 'sonnet', 'opus', or 'haiku'
    show_thinking: true,              // Show Claude's reasoning process
    show_metrics: true,               // Display cost/token metrics  
    auto_continue: true,              // Continue previous conversations
    max_retries: 3,                   // Retry failed requests
    timeout_seconds: 300,             // Request timeout
    verbose: false,                   // Show debug information
    system_prompt: "You are a helpful TypeScript tutor."  // Custom system prompt
});

const claude = new SimpleClaudeAPI(config);
```

### Runtime Configuration
```typescript
const claude = new SimpleClaudeAPI();

// Change settings on the fly
claude.change_model("opus");                           // Switch models
claude.enable_thinking(true);                         // Show reasoning
claude.enable_metrics(false);                        // Hide metrics
claude.set_system_prompt("You are a creative writer."); // Set personality
```

### Ultra-Simple Global Configuration
```typescript
import { useModel, setPersonality } from './claude';

// Configure the global instance
useModel('opus');                                    // Switch to powerful model
setPersonality('You are a TypeScript expert.');     // Set system prompt

// Now all calls use the new settings
const answer = await claude("Explain TypeScript generics");
```

## 🗣️ Multi-Turn Conversations

### Using the Simple API
```typescript
const claude = new SimpleClaudeAPI();

// Ask multiple related questions
const responses = await claude.chat([
    "Hi! I'm learning TypeScript.",
    "What are the most important concepts to master?", 
    "Can you show me an example of a generic function?",
    "Thanks for the help!"
]);

responses.forEach((response, i) => {
    console.log(`Response ${i + 1}: ${response.text.slice(0, 100)}...`);
});
```

### Interactive CLI
```typescript
import * as readline from 'readline';
import { claude } from './claude';

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

async function chatLoop() {
    while (true) {
        const question = await new Promise<string>(resolve => {
            rl.question('\n🤔 Ask Claude: ', resolve);
        });
        
        if (['exit', 'quit', 'bye'].includes(question.toLowerCase())) {
            break;
        }
        
        const answer = await claude(question);
        console.log(`\n🤖 Claude: ${answer}\n`);
    }
    rl.close();
}

chatLoop();
```

## 🧠 Thinking Process (When Available)

```typescript
import { claudeThink } from './claude';

// Show Claude's reasoning process
const answer = await claudeThink(
    "Solve this: If a function takes 2ms and we call it 1000 times sequentially vs parallel, what's the difference?"
);

// Or with the full API
const response = await claude.ask(
    "Solve this math problem: If a train travels 120 miles in 2 hours, what's its speed?",
    undefined, // no custom callback
    true       // show thinking
);
```

## 🔧 Tool Use Visualization

When Claude uses tools (like web search, code execution), you'll see real-time visualization:

```
┌─ Tool Use ─────────────────────────────────────────┐
│ 🔧 Using Tool: WebSearch                           │
│ Input: {"query": "TypeScript 5.0 new features"}    │
└─────────────────────────────────────────────────────┘

┌─ Tool Response ────────────────────────────────────┐
│ ✅ Tool Result                                     │
│ TypeScript 5.0 introduces decorators support...   │
└─────────────────────────────────────────────────────┘
```

## 📊 Metrics and Cost Tracking

### Global Statistics
```typescript
import { getStats, resetStats } from './claude';

// Ask several questions
await claude("What is TypeScript?");
await claude("How do I install packages?");
await claude("What are type guards?");

// Get session statistics
const stats = getStats();
console.log(`Total cost: $${stats.total_cost.toFixed(4)}`);
console.log(`Total tokens: ${stats.total_tokens}`);
console.log(`Requests made: ${stats.requests_count}`);
console.log(`Average response time: ${stats.average_response_time.toFixed(1)}s`);

// Reset metrics
resetStats();
```

### Using Full API for Detailed Metrics
```typescript
const claude = new SimpleClaudeAPI();

// Ask questions
await claude.ask("What is TypeScript?");
await claude.ask("How do decorators work?");

// Get detailed session statistics
const metrics = claude.get_metrics();
console.log(`Total cost: $${metrics.total_cost.toFixed(4)}`);
console.log(`Total tokens: ${metrics.total_tokens}`);
console.log(`Requests made: ${metrics.requests_count}`);
console.log(`Average response time: ${metrics.average_response_time.toFixed(1)}s`);

// Reset metrics
claude.reset_metrics();
```

### Per-Response Metrics
```typescript
const response = await claude.ask("Explain async/await in TypeScript");

console.log(`This question cost: $${response.cost.toFixed(4)}`);
console.log(`Tokens used: ${response.tokens_used}`);
console.log(`Model: ${response.model}`);
console.log(`Duration: ${response.duration_seconds.toFixed(1)}s`);
console.log(`Success: ${response.success}`);
```

## 🎛️ Advanced Features

### Custom Streaming Callback
```typescript
function myCustomHandler(textChunk: string) {
    // Handle each piece of streaming text
    process.stdout.write(`[CLAUDE] ${textChunk}`);
}

const response = await claude.ask(
    "Write a short TypeScript function",
    myCustomHandler
);
```

### Model Switching
```typescript
import { useModel } from './claude';

// Start with fast, cheap model
useModel("haiku");
const quickAnswer = await claude("What's 2+2?");

// Switch to powerful model for complex task
useModel("opus");
const detailedAnswer = await claude("Explain TypeScript's type system");
```

### Error Handling
```typescript
try {
    const response = await claude.ask("Your question here");
    if (response.success) {
        console.log(`Success! Answer: ${response.text}`);
    } else {
        console.log(`Error occurred: ${response.text}`);
    }
} catch (error) {
    console.log(`Network or CLI error: ${error}`);
}
```

## 🏗️ Project Structure

```
TS/
├── claude_api/           # Core API layer
│   ├── models.ts        # TypeScript type definitions
│   ├── parser.ts        # JSON stream parsing
│   └── api.ts           # Main API implementation
├── SimpleClaude/        # User-friendly wrapper
│   ├── models.ts        # Simple type definitions  
│   ├── simple_api.ts    # Full-featured simple API
│   └── claude.ts        # Ultra-simple functions
└── README.md           # This file
```

## 🛠️ Underlying Architecture

This wrapper provides three layers:

1. **`claude.ts` functions** - Ultra-simple one-liners (recommended for beginners)
2. **`SimpleClaudeAPI`** - Full-featured class with configuration options
3. **`ClaudeAPI`** - Advanced API with complete control over Claude CLI

```typescript
// If you need advanced features, use the full API
import { ClaudeAPI } from './claude_api/api';
import { DEFAULT_API_CONFIG } from './claude_api/models';

const advancedClaude = new ClaudeAPI({
    ...DEFAULT_API_CONFIG,
    // Advanced rate limiting, retry logic, session management, etc.
});
```

## 📝 Complete API Reference

### Ultra-Simple Functions (`claude.ts`)
- `claude(question)` - Ask and get text answer
- `claudeWithInfo(question)` - Ask and get full response object
- `claudePretty(question)` - Ask with pretty terminal output
- `claudeChat(questions[])` - Multi-turn conversation
- `claudeThink(question)` - Ask with thinking process visible
- `useModel(model)` - Switch models globally
- `setPersonality(prompt)` - Set system prompt globally
- `clearPersonality()` - Clear system prompt
- `getStats()` - Get usage statistics
- `resetStats()` - Reset statistics

### SimpleClaudeAPI Methods
- `ask(prompt, callback?, show_thinking?)` - Ask a question
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

- **Start with `claude()` function** - simplest possible interface
- **Use `claudeWithInfo()`** when you need cost/token information
- **Use `SimpleClaudeAPI`** for complex applications with configuration
- **Use `show_thinking=true`** for complex reasoning tasks
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

**TypeScript compilation errors**
```bash
npm install -D typescript @types/node
npx tsc --init
```

**Module import errors**
```typescript
// Use relative imports
import { claude } from './claude';
// Not absolute imports
```

**Slow responses**
- Try switching to `haiku` model: `useModel('haiku')`
- Check your internet connection
- Increase timeout in config

### Development Setup

```bash
# Clone and setup
git clone <your-repo>
cd TS/

# Install dependencies
npm install

# For TypeScript development
npm install -D typescript @types/node ts-node

# Run TypeScript directly
npx ts-node your-script.ts

# Or compile and run
npx tsc
node dist/your-script.js
```

## 📖 Example Scripts

### Basic Q&A Bot
```typescript
import { claude } from './claude';

async function askQuestion() {
    const answer = await claude("Explain TypeScript interfaces in simple terms");
    console.log(answer);
}

askQuestion();
```

### Cost-Aware Chatbot
```typescript
import { claudeWithInfo, getStats } from './claude';

async function costAwareChatbot() {
    const response = await claudeWithInfo("Write a TypeScript function to reverse a string");
    
    console.log(`Answer: ${response.text}`);
    console.log(`Cost: $${response.cost.toFixed(4)}`);
    
    const stats = getStats();
    if (stats.total_cost > 0.10) {
        console.log("⚠️  Cost limit reached!");
    }
}

costAwareChatbot();
```

### Interactive Development Assistant
```typescript
import { SimpleClaudeAPI, SimpleConfigImpl } from './SimpleClaude/simple_api';

const config = new SimpleConfigImpl({
    system_prompt: "You are a TypeScript development assistant. Provide practical, working code examples.",
    model: "sonnet",
    show_metrics: true
});

const claude = new SimpleClaudeAPI(config);

async function devAssistant() {
    const response = await claude.ask(
        "How do I create a generic function that works with arrays?"
    );
    
    // Response automatically streams to terminal with beautiful formatting!
}

devAssistant();
```

---

**Ready to build something amazing with Claude and TypeScript?** This wrapper makes it as easy as possible! 🚀