/**
 * Ultra-simple Claude API wrapper that even toddlers can use (TypeScript version)
 */

import * as util from 'util';
import { performance } from 'perf_hooks';

import {
  ClaudeAPI,
  AsyncClaudeAPI
} from '../claude_api/api';

import {
  APIConfig,
  SessionConfig,
  RateLimitConfig,
  RetryConfig,
  StreamConfig,
  DebugConfig,
  ClaudeModelConfig,
  SystemPromptConfig,
  ConversationConfig,
  AssistantResponse,
  UserResponse,
  SystemInit,
  ResultSummary,
  TextContent,
  ThinkingContent,
  ToolUseContent,
  ToolResultContent,
} from '../claude_api/models';

import {
  SimpleResponse,
  SimpleResponseImpl,
  SimpleMetrics,
  SimpleMetricsImpl,
  SimpleConfig,
  SimpleConfigImpl,
  DEFAULT_SIMPLE_CONFIG
} from './models';

// Simple console colors for Node.js (replacement for Rich library)
const colors = {
  reset: '\x1b[0m',
  bold: '\x1b[1m',
  dim: '\x1b[2m',
  
  // Basic colors
  black: '\x1b[30m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
  white: '\x1b[37m',
  
  // Bright colors
  brightRed: '\x1b[91m',
  brightGreen: '\x1b[92m',
  brightYellow: '\x1b[93m',
  brightBlue: '\x1b[94m',
  brightMagenta: '\x1b[95m',
  brightCyan: '\x1b[96m',
  brightWhite: '\x1b[97m'
};

// Helper functions for console output
function colorize(text: string, color: string): string {
  return `${color}${text}${colors.reset}`;
}

function printColored(text: string, color: string = ''): void {
  console.log(colorize(text, color));
}

function printPanel(content: string, title: string = '', borderColor: string = colors.blue): void {
  const width = 80;
  const border = '─'.repeat(width - 2);
  
  console.log(colorize(`┌${border}┐`, borderColor));
  if (title) {
    const titlePadding = Math.max(0, width - title.length - 4);
    const leftPad = Math.floor(titlePadding / 2);
    const rightPad = titlePadding - leftPad;
    console.log(colorize(`│ ${' '.repeat(leftPad)}${title}${' '.repeat(rightPad)} │`, borderColor));
    console.log(colorize(`├${border}┤`, borderColor));
  }
  
  const lines = content.split('\n');
  for (const line of lines) {
    const padding = Math.max(0, width - line.length - 4);
    console.log(colorize(`│ ${line}${' '.repeat(padding)} │`, borderColor));
  }
  console.log(colorize(`└${border}┘`, borderColor));
}

function printRule(text: string, color: string = colors.blue): void {
  const width = 80;
  const textLength = text.length;
  const ruleLength = Math.max(0, width - textLength - 4);
  const leftRule = '─'.repeat(Math.floor(ruleLength / 2));
  const rightRule = '─'.repeat(Math.ceil(ruleLength / 2));
  
  console.log(colorize(`${leftRule}  ${text}  ${rightRule}`, color));
}

export class SimpleClaudeAPI {
  private config: SimpleConfig;
  private session_metrics: SimpleMetrics;
  private response_times: number[] = [];
  private claude_api: ClaudeAPI;

  constructor(config?: Partial<SimpleConfig>) {
    this.config = new SimpleConfigImpl(config);
    this.session_metrics = new SimpleMetricsImpl({
      total_cost: 0.0,
      total_tokens: 0,
      requests_count: 0,
      average_response_time: 0.0
    });

    // Configure the underlying Claude API with sensible defaults
    const api_config: Partial<APIConfig> = {
      session: {
        maintain_context: true,
        max_history_size: 50,
        auto_save: true,
        persist_to_file: undefined
      },
      rate_limit: {
        requests_per_minute: 30,
        requests_per_hour: 500,
        burst_size: 10,
        enabled: true
      },
      retry: {
        max_retries: this.config.max_retries,
        initial_delay: 1.0,
        max_delay: 10.0,
        exponential_base: 2.0,
        retry_on: ["TimeoutError", "ConnectionError", "RuntimeError"]
      },
      streaming: {
        buffer_size: 65536,
        timeout_between_chunks: 30.0,
        yield_raw: false
      },
      debug: {
        enabled: this.config.verbose
      },
      claude_model_config: {
        model: this.config.model,
        fallback_model: this.config.model !== "haiku" ? "haiku" : "sonnet"
      },
      system_prompt_config: {
        system_prompt: this.config.system_prompt
      },
      conversation_config: {
        continue_last: this.config.auto_continue,
        resume_session_id: undefined
      },
      default_timeout: this.config.timeout_seconds,
      verbose: this.config.verbose
    };

    this.claude_api = new ClaudeAPI(api_config);

    // Welcome message
    if (!this.config.verbose) {
      console.log('\n');
      printPanel(
        '🤖 Simple Claude API ready! Just call .ask() to start chatting.',
        '',
        colors.green
      );
      console.log('');
    }
  }

  /**
   * Ask Claude a question with automatic streaming and metrics
   */
  async ask(
    prompt: string,
    callback?: (text: string) => void,
    show_thinking?: boolean
  ): Promise<SimpleResponse> {
    if (!prompt || !prompt.trim()) {
      console.log('\n');
      printColored('❌ Error: Please provide a non-empty prompt!', colors.red);
      console.log('');
      return new SimpleResponseImpl({
        text: "Error: Empty prompt provided",
        cost: 0.0,
        tokens_used: 0,
        model: "none",
        success: false,
        duration_seconds: 0.0,
        tool_uses: [],
        tool_results: []
      });
    }

    console.log('\n');
    printRule('New Claude Request', colors.blue);
    printColored(`🤔 Asking Claude: ${prompt}`, colors.cyan);
    printColored('💭 Thinking and responding...', colors.yellow);
    console.log('');

    const start_time = performance.now();
    const response_text_parts: string[] = [];
    const thinking_parts: string[] = [];
    const tool_uses: Record<string, any>[] = [];
    const tool_results: Record<string, any>[] = [];

    // Variables to capture metrics from streaming
    let cost = 0.0;
    let tokens = 0;
    let model = "unknown";
    let success = true;
    let session_id: string | undefined;

    // Stream handler
    const stream_handler = (text: string) => {
      response_text_parts.push(text);
      if (callback) {
        callback(text);
      } else {
        process.stdout.write(colorize(text, colors.green));
      }
    };

    try {
      // Stream the response
      for await (const event of this.claude_api.execute_stream(prompt)) {
        if (event && typeof event === 'object' && 'type' in event) {
          if (event.type === 'assistant') {
            const assistantEvent = event as AssistantResponse;
            model = assistantEvent.message.model;
            
            for (const content of assistantEvent.message.content) {
              if (content.type === 'text') {
                const textContent = content as TextContent;
                stream_handler(textContent.text);
              } else if (content.type === 'thinking') {
                const thinkingContent = content as ThinkingContent;
                thinking_parts.push(thinkingContent.thinking);
                
                if (show_thinking || (show_thinking === undefined && this.config.show_thinking)) {
                  console.log('\n');
                  printPanel(
                    thinkingContent.thinking,
                    '💭 Claude\'s Thinking',
                    colors.yellow
                  );
                  console.log('');
                }
              } else if (content.type === 'tool_use') {
                const toolUseContent = content as ToolUseContent;
                const tool_use_dict = {
                  id: toolUseContent.id,
                  name: toolUseContent.name,
                  input: toolUseContent.input
                };
                tool_uses.push(tool_use_dict);

                console.log('\n');
                printPanel(
                  `🔧 Using Tool: ${toolUseContent.name}\nInput: ${JSON.stringify(toolUseContent.input)}`,
                  'Tool Use',
                  colors.magenta
                );
                console.log('');
              }
            }
          } else if (event.type === 'user') {
            const userEvent = event as UserResponse;
            for (const content of userEvent.message.content) {
              if (content.type === 'tool_result') {
                const toolResultContent = content as ToolResultContent;
                const tool_result_dict = {
                  tool_use_id: toolResultContent.tool_use_id,
                  content: toolResultContent.content,
                  is_error: toolResultContent.is_error
                };
                tool_results.push(tool_result_dict);

                const result_color = toolResultContent.is_error ? colors.red : colors.green;
                const result_icon = toolResultContent.is_error ? '❌' : '✅';

                console.log('\n');
                printPanel(
                  `${result_icon} Tool Result\n${toolResultContent.content}`,
                  'Tool Response',
                  result_color
                );
                console.log('');
              }
            }
          } else if (event.type === 'system') {
            const systemEvent = event as SystemInit;
            session_id = systemEvent.session_id;
          } else if (event.type === 'result') {
            const resultEvent = event as ResultSummary;
            cost = resultEvent.total_cost_usd;
            if (resultEvent.usage) {
              tokens = resultEvent.usage.input_tokens + resultEvent.usage.output_tokens;
            }
            success = !resultEvent.is_error;
          }
        }
      }

      const end_time = performance.now();
      const duration = (end_time - start_time) / 1000; // Convert to seconds

      // Process response
      const complete_text = response_text_parts.join('');
      const thinking_text = thinking_parts.length > 0 ? thinking_parts.join('\n') : undefined;

      // Update session metrics
      this.session_metrics.total_cost += cost;
      this.session_metrics.total_tokens += tokens;
      this.session_metrics.requests_count += 1;
      this.response_times.push(duration);
      this.session_metrics.average_response_time = 
        this.response_times.reduce((a, b) => a + b, 0) / this.response_times.length;

      // Create response object
      const simple_response = new SimpleResponseImpl({
        text: complete_text,
        cost: cost,
        tokens_used: tokens,
        model: model,
        success: success,
        session_id: session_id,
        duration_seconds: duration,
        thinking: thinking_text,
        tool_uses: tool_uses,
        tool_results: tool_results
      });

      // Show metrics if enabled
      if (this.config.show_metrics) {
        console.log('\n');
        printRule('Response Complete', colors.green);

        const metrics_text = 
          `✅ Response completed in ${duration.toFixed(1)}s\n` +
          `💰 Cost: $${cost.toFixed(4)} | 🎯 Tokens: ${tokens} | 🤖 Model: ${model}\n\n` +
          `📊 Session Stats:\n` +
          `💵 Total Cost: $${this.session_metrics.total_cost.toFixed(4)}\n` +
          `🎯 Total Tokens: ${this.session_metrics.total_tokens}\n` +
          `📨 Requests: ${this.session_metrics.requests_count}\n` +
          `⏱️  Avg Response Time: ${this.session_metrics.average_response_time.toFixed(1)}s`;

        printPanel(metrics_text, '📊 Metrics & Performance', colors.blue);
        console.log('');
      }

      return simple_response;

    } catch (error) {
      const end_time = performance.now();
      const duration = (end_time - start_time) / 1000;

      console.log('\n');
      printPanel(
        `❌ Something went wrong: ${error}\n\n🔄 Don't worry, this happens sometimes. Try again!`,
        'Error',
        colors.red
      );
      console.log('');

      return new SimpleResponseImpl({
        text: `Error: ${error}`,
        cost: 0.0,
        tokens_used: 0,
        model: "unknown",
        success: false,
        duration_seconds: duration,
        tool_uses: [],
        tool_results: []
      });
    }
  }

  /**
   * Have a multi-turn conversation with Claude
   */
  async chat(prompts: string[]): Promise<SimpleResponse[]> {
    const responses: SimpleResponse[] = [];
    console.log('\n');
    printPanel(
      `🗣️ Starting conversation with ${prompts.length} messages...`,
      '',
      colors.cyan
    );
    console.log('');

    for (let i = 0; i < prompts.length; i++) {
      const prompt = prompts[i];
      console.log('\n');
      printRule(`💬 Message ${i + 1}/${prompts.length}`, colors.magenta);
      
      const response = await this.ask(prompt);
      responses.push(response);

      if (!response.success) {
        printColored(`❌ Stopping conversation due to error in message ${i + 1}`, colors.red);
        break;
      }
    }

    console.log('\n');
    printPanel(
      `🎉 Conversation completed! ${responses.length} responses received.`,
      '',
      colors.green
    );
    console.log('');
    return responses;
  }

  /**
   * Get current session metrics
   */
  get_metrics(): SimpleMetrics {
    return this.session_metrics;
  }

  /**
   * Reset session metrics to zero
   */
  reset_metrics(): void {
    this.session_metrics = new SimpleMetricsImpl({
      total_cost: 0.0,
      total_tokens: 0,
      requests_count: 0,
      average_response_time: 0.0
    });
    this.response_times = [];
    printColored('📊 Session metrics reset!', colors.green);
  }

  /**
   * Change the Claude model
   */
  change_model(model: string): void {
    this.config.model = model;
    const fallback = model !== "haiku" ? "haiku" : "sonnet";
    this.claude_api.set_model(model, fallback);
    printColored(`🤖 Switched to model: ${model} (fallback: ${fallback})`, colors.cyan);
  }

  /**
   * Enable or disable showing Claude's thinking process
   */
  enable_thinking(enabled: boolean = true): void {
    this.config.show_thinking = enabled;
    const status = enabled ? "enabled" : "disabled";
    printColored(`🧠 Thinking display ${status}`, colors.yellow);
  }

  /**
   * Enable or disable metrics display
   */
  enable_metrics(enabled: boolean = true): void {
    this.config.show_metrics = enabled;
    const status = enabled ? "enabled" : "disabled";
    printColored(`📊 Metrics display ${status}`, colors.blue);
  }

  /**
   * Set or clear the system prompt that gets appended to all requests
   */
  set_system_prompt(system_prompt?: string): void {
    this.config.system_prompt = system_prompt;
    this.claude_api.set_system_prompt(system_prompt || "");

    if (system_prompt) {
      printColored(`📝 System prompt set: ${system_prompt}`, colors.green);
    } else {
      printColored('📝 System prompt cleared', colors.green);
    }
  }

  /**
   * Show help information
   */
  help(): void {
    const help_text = `
🤖 Simple Claude API Help

Basic Usage:
  const claude = new SimpleClaudeAPI();
  const response = await claude.ask("Your question here");

Methods:
  .ask(prompt, callback?)         - Ask a question (with streaming)
  .chat([prompt1, prompt2, ...])  - Multi-turn conversation
  .get_metrics()                  - View session statistics
  .reset_metrics()                - Reset statistics
  .change_model(model)            - Switch models
  .enable_thinking(true/false)    - Show/hide thinking
  .enable_metrics(true/false)     - Show/hide metrics
  .set_system_prompt(prompt)      - Set system prompt for all requests
  .help()                         - Show this help

Examples:
  // Basic usage
  await claude.ask("What is Python?");
  
  // With custom callback
  const my_callback = (text: string) => {
    console.log(\`Claude: \${text}\`);
  };
  await claude.ask("Tell me a joke", my_callback);
  
  // Multiple questions
  await claude.chat(["Hi!", "What's the weather like?", "Thanks!"]);
  
  // With system prompt
  claude.set_system_prompt("You are a helpful Python tutor.");
  await claude.ask("How do I create a list?");
  
  // Initialize with system prompt
  import { SimpleClaudeAPI, SimpleConfigImpl } from './simple_api';
  const config = new SimpleConfigImpl({
    system_prompt: "You are a creative writer."
  });
  const claude = new SimpleClaudeAPI(config);

Models available: 'sonnet' (default), 'opus', 'haiku'
    `;

    printPanel(help_text, '🤖 Simple Claude API Help', colors.blue);
  }
}

// Export the config class for external use
export { SimpleConfigImpl };

// Convenience function for one-off questions
export async function ask_claude_simple(
  prompt: string,
  model: string = "sonnet",
  show_thinking: boolean = false,
  system_prompt?: string
): Promise<SimpleResponse> {
  const config = new SimpleConfigImpl({
    model: model,
    show_thinking: show_thinking,
    system_prompt: system_prompt
  });
  const claude = new SimpleClaudeAPI(config);
  return claude.ask(prompt);
}

// Even simpler function that just prints the answer
export async function claude_say(prompt: string): Promise<void> {
  await ask_claude_simple(prompt);
}