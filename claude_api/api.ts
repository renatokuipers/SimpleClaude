/**
 * Main Claude API module with advanced features including streaming, sessions, retry, and rate limiting (TypeScript version)
 */

import { spawn, ChildProcess } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import { EventEmitter } from 'events';

import {
  ClaudeResponse,
  APIConfig,
  DEFAULT_API_CONFIG,
  Session,
  SessionImpl,
  RateLimitState,
  RateLimitStateImpl,
  RetryConfig,
  RateLimitConfig,
  StreamConfig,
  SessionConfig,
  CommandFlags,
  SystemInit,
  AssistantResponse,
  UserResponse,
  ResultSummary,
  DebugConfig,
  InputFormat,
  ToolRestrictions,
  ClaudeModelConfig,
  DirectoryConfig,
  ConversationConfig,
  SystemPromptConfig
} from './models';

import {
  ClaudeResponseParser,
  parse_claude_stream,
  StreamingResponseParser,
  stream_parse_generator,
  async_stream_parse_generator
} from './parser';

const sleep = (ms: number): Promise<void> => new Promise(resolve => setTimeout(resolve, ms));

export class ClaudeAPI {
  protected config: APIConfig;
  protected session?: Session;
  protected rate_limiter?: RateLimitStateImpl;
  protected base_command: string[];

  constructor(config?: Partial<APIConfig>) {
    this.config = { ...DEFAULT_API_CONFIG, ...config };
    this.session = this.config.session.maintain_context ? new SessionImpl() : undefined;
    this.rate_limiter = this.config.rate_limit.enabled ? new RateLimitStateImpl() : undefined;

    // Build base command
    this.base_command = [
      'claude',
      '-p',
      '--dangerously-skip-permissions',
      '--output-format',
      'stream-json',
      '--verbose'
    ];
  }

  protected _build_command(prompt: string): string[] {
    const command = [...this.base_command];

    // Add debug flag
    if (this.config.debug.enabled) {
      command.push('--debug');
    }

    // Add input format (only if not default)
    if (this.config.input_format.format !== 'text') {
      command.push('--input-format', this.config.input_format.format);
    }

    // Add model configuration
    if (this.config.claude_model_config.model) {
      command.push('--model', this.config.claude_model_config.model);
    }

    if (this.config.claude_model_config.fallback_model) {
      command.push('--fallback-model', this.config.claude_model_config.fallback_model);
    }

    // Add tool restrictions
    if (this.config.tool_restrictions.allowed_tools) {
      const tools_str = this.config.tool_restrictions.allowed_tools.join(' ');
      command.push('--allowedTools', tools_str);
    }

    if (this.config.tool_restrictions.disallowed_tools) {
      const tools_str = this.config.tool_restrictions.disallowed_tools.join(' ');
      command.push('--disallowedTools', tools_str);
    }

    // Add conversation flags
    if (this.config.conversation_config.continue_last) {
      command.push('--continue');
    } else if (this.config.conversation_config.resume_session_id) {
      command.push('--resume', this.config.conversation_config.resume_session_id);
    }

    // Add system prompt
    if (this.config.system_prompt_config.system_prompt) {
      command.push('--append-system-prompt', this.config.system_prompt_config.system_prompt);
    }

    // Add additional directories
    if (this.config.directory_config.additional_dirs.length > 0) {
      command.push('--add-dir');
      command.push(...this.config.directory_config.additional_dirs);
    }

    // Add any additional custom flags
    if (this.config.command_flags.custom_flags) {
      for (const [flag, value] of Object.entries(this.config.command_flags.custom_flags)) {
        if (this.config.command_flags.allowed_flags.includes(flag)) {
          // Skip flags we've already handled above
          const handled_flags = [
            '-d', '--debug', '--input-format', '--model',
            '--fallback-model', '--allowedTools', '--disallowedTools',
            '-c', '--continue', '-r', '--resume', '--add-dir',
            '--append-system-prompt'
          ];
          if (!handled_flags.includes(flag)) {
            if (value) {
              command.push(flag, value);
            } else {
              command.push(flag);
            }
          }
        }
      }
    }

    // Add prompt last
    command.push(prompt);
    return command;
  }

  protected async _check_rate_limit(): Promise<void> {
    if (!this.rate_limiter || !this.config.rate_limit.enabled) {
      return;
    }

    const [should_delay, delay_seconds] = this.rate_limiter.should_delay(this.config.rate_limit);
    if (should_delay) {
      await sleep(delay_seconds * 1000);
    }
  }

  protected _should_retry(error: Error): boolean {
    const error_type = error.constructor.name;
    return this.config.retry.retry_on.includes(error_type);
  }

  protected _calculate_retry_delay(attempt: number): number {
    const delay = Math.min(
      this.config.retry.initial_delay * Math.pow(this.config.retry.exponential_base, attempt),
      this.config.retry.max_delay
    );
    return delay;
  }

  protected _run_command(command: string[], timeout: number): Promise<{ stdout: string; stderr: string }> {
    return new Promise((resolve, reject) => {
      const child = spawn(command[0], command.slice(1), {
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, CLAUDE_OUTPUT_FORMAT: 'stream-json' }
      });

      let stdout = '';
      let stderr = '';

      child.stdout?.on('data', (data) => {
        const chunk = data.toString();
        stdout += chunk;
      });

      child.stderr?.on('data', (data) => {
        const chunk = data.toString();
        stderr += chunk;
        // Log stderr for debugging but don't mix with stdout
        if (this.config.debug.enabled) {
          console.error('Claude stderr:', chunk);
        }
      });

      const timeoutId = setTimeout(() => {
        child.kill();
        reject(new Error(`Claude command timed out after ${timeout} seconds`));
      }, timeout * 1000);

      child.on('close', (code) => {
        clearTimeout(timeoutId);
        if (code !== 0) {
          reject(new Error(`Claude command failed: ${stderr}`));
        } else {
          resolve({ stdout, stderr });
        }
      });

      child.on('error', (error) => {
        clearTimeout(timeoutId);
        reject(error);
      });
    });
  }

  public async execute(prompt: string, timeout?: number): Promise<ClaudeResponse> {
    timeout = timeout || this.config.default_timeout;
    const command = this._build_command(prompt);

    let last_error: Error | null = null;
    
    for (let attempt = 0; attempt <= this.config.retry.max_retries; attempt++) {
      try {
        // Check rate limit
        await this._check_rate_limit();

        // Execute command
        const result = await this._run_command(command, timeout);

        // Record successful request
        if (this.rate_limiter) {
          this.rate_limiter.record_request();
        }

        // Parse response
        const response = parse_claude_stream(result.stdout);

        // Update session if enabled
        if (this.session && response.system_init) {
          this.session.session_id = response.system_init.session_id;
          for (const resp of response.assistant_responses) {
            this.session.add_response(resp);
          }
          for (const resp of response.user_responses) {
            this.session.add_response(resp);
          }
          if (response.result_summary) {
            this.session.total_cost += response.result_summary.total_cost_usd;
          }
        }

        // Save session if configured
        if (this.session && this.config.session.auto_save && this.config.session.persist_to_file) {
          await this.save_session();
        }

        return response;
      } catch (error) {
        last_error = error as Error;
        
        if (this._should_retry(last_error) && attempt < this.config.retry.max_retries) {
          const delay = this._calculate_retry_delay(attempt);
          await sleep(delay * 1000);
          continue;
        }
        throw last_error;
      }
    }

    throw last_error || new Error('Unexpected error in retry logic');
  }

  public async *execute_stream(prompt: string, timeout?: number): AsyncGenerator<SystemInit | AssistantResponse | UserResponse | ResultSummary | string, void, unknown> {
    timeout = timeout || this.config.default_timeout;
    const command = this._build_command(prompt);

    // Check rate limit
    await this._check_rate_limit();

    // Create process
    const process = spawn(command[0], command.slice(1), {
      stdio: ['pipe', 'pipe', 'pipe']
    });

    // CRITICAL: Close stdin immediately so Claude CLI doesn't wait for input
    if (process.stdin) {
      process.stdin.end();
    }

    // Record request
    if (this.rate_limiter) {
      this.rate_limiter.record_request();
    }

    // Create streaming parser
    const stream_parser = new StreamingResponseParser(this.config.streaming);

    try {
      // Set timeout
      let timeoutId: NodeJS.Timeout | null = null;

      if (timeout) {
        timeoutId = setTimeout(() => {
          process.kill('SIGTERM');
          throw new Error(`Claude command timed out after ${timeout} seconds`);
        }, timeout * 1000);
      }

      // Use async iterator pattern with proper stream handling
      const eventAsyncIterator = this._createEventAsyncIterator(process, stream_parser, timeoutId);

      // Yield events as they come
      for await (const event of eventAsyncIterator) {
        // Update session if it's a response
        if (this.session && (event as any).type && 
            ((event as any).type === 'assistant' || (event as any).type === 'user')) {
          this.session.add_response(event as AssistantResponse | UserResponse);
        }
        yield event;
      }

      // Clear timeout if still active
      if (timeoutId) {
        clearTimeout(timeoutId);
      }

      // Get final response for session update
      if (this.session) {
        const response = stream_parser.get_response();
        if (response.result_summary) {
          this.session.total_cost += response.result_summary.total_cost_usd;
        }

        // Save session if configured
        if (this.config.session.auto_save && this.config.session.persist_to_file) {
          await this.save_session();
        }
      }
    } finally {
      if (process.pid) {
        process.kill('SIGTERM');
      }
    }
  }

  private async *_createEventAsyncIterator(
    process: ChildProcess,
    stream_parser: StreamingResponseParser,
    timeoutId: NodeJS.Timeout | null
  ): AsyncGenerator<SystemInit | AssistantResponse | UserResponse | ResultSummary | string, void, unknown> {
    const eventQueue: (SystemInit | AssistantResponse | UserResponse | ResultSummary | string)[] = [];
    let processComplete = false;
    let processError: Error | null = null;

    // Read output line by line
    let buffer = '';
    
    process.stdout?.on('data', (data) => {
      buffer += data.toString();
      
      while (buffer.includes('\n')) {
        const newlineIndex = buffer.indexOf('\n');
        const line = buffer.substring(0, newlineIndex);
        buffer = buffer.substring(newlineIndex + 1);
        
        const cleanLine = line.trim();
        if (cleanLine && cleanLine.startsWith('{')) {
          // Parse single line directly instead of using parse_chunk
          const event = stream_parser.parser.parse_line(cleanLine);
          if (event) {
            eventQueue.push(event);
          }
        }
      }
    });

    // Handle process completion
    process.on('close', (code) => {
      if (timeoutId) clearTimeout(timeoutId);
      if (code !== 0) {
        processError = new Error(`Claude command failed with exit code ${code}`);
      } else {
        // Process any remaining buffer content
        const remainingLine = buffer.trim();
        if (remainingLine && remainingLine.startsWith('{')) {
          const event = stream_parser.parser.parse_line(remainingLine);
          if (event) {
            eventQueue.push(event);
          }
        }
      }
      processComplete = true;
    });

    process.on('error', (error) => {
      if (timeoutId) clearTimeout(timeoutId);
      processError = error;
      processComplete = true;
    });

    // Yield events as they become available
    while (!processComplete || eventQueue.length > 0) {
      if (eventQueue.length > 0) {
        const event = eventQueue.shift()!;
        yield event;
      } else if (!processComplete) {
        // Use setImmediate to yield control back to event loop
        await new Promise(resolve => setImmediate(resolve));
      }
    }

    // Throw error if process failed
    if (processError) {
      throw processError;
    }
  }

  public async ask(prompt: string, timeout?: number): Promise<string> {
    const response = await this.execute(prompt, timeout);
    const parser = new ClaudeResponseParser();
    parser.assistant_responses = response.assistant_responses;
    return parser.get_message_text();
  }

  public async execute_with_metrics(prompt: string, timeout?: number): Promise<Record<string, any>> {
    const response = await this.execute(prompt, timeout);
    const parser = new ClaudeResponseParser();
    parser.assistant_responses = response.assistant_responses;
    parser.result_summary = response.result_summary;

    return {
      text: parser.get_message_text(),
      successful: parser.was_successful(),
      usage: parser.get_usage_summary(),
      cost_usd: parser.get_cost(),
      duration_ms: response.result_summary?.duration_ms || null,
      model: response.assistant_response?.message.model || null,
      session_id: this.session?.session_id || null,
      total_session_cost: this.session?.total_cost || null
    };
  }

  public set_custom_flags(flags: Record<string, string>): void {
    this.config.command_flags.custom_flags = flags;
  }

  public set_debug(enabled: boolean = true): void {
    this.config.debug.enabled = enabled;
  }

  public set_model(model: string, fallback_model?: string): void {
    this.config.claude_model_config.model = model;
    if (fallback_model) {
      this.config.claude_model_config.fallback_model = fallback_model;
    }
  }

  public set_tool_restrictions(allowed_tools?: string[], disallowed_tools?: string[]): void {
    if (allowed_tools !== undefined) {
      this.config.tool_restrictions.allowed_tools = allowed_tools;
    }
    if (disallowed_tools !== undefined) {
      this.config.tool_restrictions.disallowed_tools = disallowed_tools;
    }
  }

  public add_directories(directories: string[]): void {
    this.config.directory_config.additional_dirs.push(...directories);
  }

  public continue_conversation(): void {
    this.config.conversation_config.continue_last = true;
    this.config.conversation_config.resume_session_id = undefined;
  }

  public resume_conversation(session_id: string): void {
    this.config.conversation_config.continue_last = false;
    this.config.conversation_config.resume_session_id = session_id;
  }

  public set_system_prompt(system_prompt: string): void {
    this.config.system_prompt_config.system_prompt = system_prompt;
  }

  public get_session(): Session | undefined {
    return this.session;
  }

  public clear_session(): void {
    if (this.session) {
      this.session.clear_history();
    }
  }

  public async save_session(path?: string): Promise<void> {
    if (!this.session) {
      return;
    }

    const save_path = path || this.config.session.persist_to_file;
    if (save_path) {
      const session_data = JSON.stringify(this.session);
      await fs.promises.writeFile(save_path, session_data);
    }
  }

  public async load_session(path: string): Promise<void> {
    const session_data = await fs.promises.readFile(path, 'utf8');
    const session_obj = JSON.parse(session_data);
    this.session = new SessionImpl();
    Object.assign(this.session, session_obj);
  }

  public get_rate_limit_status(): Record<string, any> | null {
    if (!this.rate_limiter) {
      return null;
    }

    return {
      requests_this_minute: this.rate_limiter.requests_this_minute,
      requests_this_hour: this.rate_limiter.requests_this_hour,
      minute_limit: this.config.rate_limit.requests_per_minute,
      hour_limit: this.config.rate_limit.requests_per_hour,
      next_minute_reset: this.rate_limiter.minute_reset_time,
      next_hour_reset: this.rate_limiter.hour_reset_time
    };
  }
}

export class AsyncClaudeAPI extends ClaudeAPI {
  constructor(config?: Partial<APIConfig>) {
    super(config);
  }

  public async execute_async(prompt: string, timeout?: number): Promise<ClaudeResponse> {
    // This is already async in the base class
    return this.execute(prompt, timeout);
  }

  public async *execute_stream_async(prompt: string, timeout?: number): AsyncGenerator<SystemInit | AssistantResponse | UserResponse | ResultSummary | string, void, unknown> {
    // This is already async in the base class
    yield* this.execute_stream(prompt, timeout);
  }

  public async ask_async(prompt: string, timeout?: number): Promise<string> {
    // This is already async in the base class
    return this.ask(prompt, timeout);
  }
}

// Convenience functions
export async function ask_claude(prompt: string, config?: Partial<APIConfig>): Promise<string> {
  const api = new ClaudeAPI(config);
  return api.ask(prompt);
}

export function create_api_with_config(config: Partial<APIConfig>): ClaudeAPI {
  return new ClaudeAPI(config);
}