/**
 * Data models for Claude API responses and configuration (TypeScript version)
 */

export interface Usage {
  input_tokens: number;
  cache_creation_input_tokens?: number;
  cache_read_input_tokens?: number;
  output_tokens: number;
  service_tier?: string;
}

export interface ServerToolUse {
  web_search_requests: number;
}

export interface ExtendedUsage extends Usage {
  server_tool_use?: ServerToolUse;
}

export interface ThinkingContent {
  type: 'thinking';
  thinking: string;
  signature?: string;
}

export interface TextContent {
  type: 'text';
  text: string;
}

export interface ToolUseContent {
  type: 'tool_use';
  id: string;
  name: string;
  input: Record<string, any>;
}

export interface ToolResultContent {
  tool_use_id: string;
  type: 'tool_result';
  content: string;
  is_error?: boolean;
}

export type MessageContent = TextContent | ThinkingContent | ToolUseContent;
export type UserContent = ToolResultContent;

export interface AssistantMessage {
  id: string;
  type: 'message';
  role: 'assistant';
  model: string;
  content: MessageContent[];
  stop_reason?: string;
  stop_sequence?: string;
  usage: Usage;
}

export interface UserMessage {
  role: 'user';
  content: UserContent[];
}

export interface SystemInit {
  type: 'system';
  subtype: 'init';
  cwd: string;
  session_id: string;
  tools: string[];
  mcp_servers: any[];
  model: string;
  permissionMode: string;
  apiKeySource: string;
}

export interface AssistantResponse {
  type: 'assistant';
  message: AssistantMessage;
  parent_tool_use_id?: string;
  session_id: string;
}

export interface UserResponse {
  type: 'user';
  message: UserMessage;
  parent_tool_use_id?: string;
  session_id: string;
}

export interface ResultSummary {
  type: 'result';
  subtype: string;
  is_error: boolean;
  duration_ms: number;
  duration_api_ms: number;
  num_turns: number;
  result: string;
  session_id: string;
  total_cost_usd: number;
  usage?: ExtendedUsage;
}

export interface ClaudeResponse {
  system_init?: SystemInit;
  assistant_responses: AssistantResponse[];
  user_responses: UserResponse[];
  result_summary?: ResultSummary;
  raw_response: string;
  
  // Getter method equivalent
  get assistant_response(): AssistantResponse | undefined;
  
  // Method to get all events in order
  get_all_events(): (SystemInit | AssistantResponse | UserResponse | ResultSummary)[];
}

export class ClaudeResponseImpl implements ClaudeResponse {
  system_init?: SystemInit;
  assistant_responses: AssistantResponse[] = [];
  user_responses: UserResponse[] = [];
  result_summary?: ResultSummary;
  raw_response: string = '';

  get assistant_response(): AssistantResponse | undefined {
    return this.assistant_responses.length > 0 ? this.assistant_responses[0] : undefined;
  }

  get_all_events(): (SystemInit | AssistantResponse | UserResponse | ResultSummary)[] {
    const events: (SystemInit | AssistantResponse | UserResponse | ResultSummary)[] = [];
    if (this.system_init) {
      events.push(this.system_init);
    }
    events.push(...this.assistant_responses);
    events.push(...this.user_responses);
    if (this.result_summary) {
      events.push(this.result_summary);
    }
    return events;
  }
}

// Configuration models
export interface RetryConfig {
  max_retries: number;
  initial_delay: number;
  max_delay: number;
  exponential_base: number;
  retry_on: string[];
}

export interface RateLimitConfig {
  requests_per_minute: number;
  requests_per_hour: number;
  burst_size: number;
  enabled: boolean;
}

export interface StreamConfig {
  buffer_size: number;
  timeout_between_chunks: number;
  yield_raw: boolean;
}

export interface SessionConfig {
  maintain_context: boolean;
  max_history_size: number;
  persist_to_file?: string;
  auto_save: boolean;
}

export interface DebugConfig {
  enabled: boolean;
}

export interface InputFormat {
  format: 'text' | 'stream-json';
}

export interface ToolRestrictions {
  allowed_tools?: string[];
  disallowed_tools?: string[];
}

export interface ClaudeModelConfig {
  model?: string;
  fallback_model?: string;
}

export interface DirectoryConfig {
  additional_dirs: string[];
}

export interface ConversationConfig {
  continue_last: boolean;
  resume_session_id?: string;
}

export interface SystemPromptConfig {
  system_prompt?: string;
}

export interface CommandFlags {
  allowed_flags: string[];
  custom_flags: Record<string, string>;
  override_defaults: boolean;
}

export interface Session {
  session_id?: string;
  created_at: Date;
  last_activity: Date;
  message_history: (AssistantResponse | UserResponse)[];
  total_tokens: number;
  total_cost: number;
  metadata: Record<string, any>;
  
  add_response(response: AssistantResponse | UserResponse): void;
  get_context(max_messages?: number): (AssistantResponse | UserResponse)[];
  clear_history(): void;
}

export class SessionImpl implements Session {
  session_id?: string;
  created_at: Date = new Date();
  last_activity: Date = new Date();
  message_history: (AssistantResponse | UserResponse)[] = [];
  total_tokens: number = 0;
  total_cost: number = 0;
  metadata: Record<string, any> = {};

  add_response(response: AssistantResponse | UserResponse): void {
    this.message_history.push(response);
    this.last_activity = new Date();
    
    // Update token count if assistant response
    if (response.type === 'assistant' && response.message.usage) {
      this.total_tokens += response.message.usage.input_tokens + response.message.usage.output_tokens;
    }
  }

  get_context(max_messages?: number): (AssistantResponse | UserResponse)[] {
    if (max_messages) {
      return this.message_history.slice(-max_messages);
    }
    return this.message_history;
  }

  clear_history(): void {
    this.message_history = [];
    this.total_tokens = 0;
    this.total_cost = 0;
  }
}

export interface RateLimitState {
  requests_this_minute: number;
  requests_this_hour: number;
  minute_reset_time: Date;
  hour_reset_time: Date;
  last_request_time?: Date;
}

export class RateLimitStateImpl implements RateLimitState {
  requests_this_minute: number = 0;
  requests_this_hour: number = 0;
  minute_reset_time: Date = new Date();
  hour_reset_time: Date = new Date();
  last_request_time?: Date;

  should_delay(config: RateLimitConfig): [boolean, number] {
    const now = new Date();
    
    // Reset counters if needed
    if ((now.getTime() - this.minute_reset_time.getTime()) >= 60000) {
      this.requests_this_minute = 0;
      this.minute_reset_time = now;
    }
    
    if ((now.getTime() - this.hour_reset_time.getTime()) >= 3600000) {
      this.requests_this_hour = 0;
      this.hour_reset_time = now;
    }
    
    // Check limits
    if (this.requests_this_minute >= config.requests_per_minute) {
      const delay = 60 - (now.getTime() - this.minute_reset_time.getTime()) / 1000;
      return [true, Math.max(0, delay)];
    }
    
    if (this.requests_this_hour >= config.requests_per_hour) {
      const delay = 3600 - (now.getTime() - this.hour_reset_time.getTime()) / 1000;
      return [true, Math.max(0, delay)];
    }
    
    return [false, 0];
  }

  record_request(): void {
    this.requests_this_minute++;
    this.requests_this_hour++;
    this.last_request_time = new Date();
  }
}

export interface APIConfig {
  retry: RetryConfig;
  rate_limit: RateLimitConfig;
  streaming: StreamConfig;
  session: SessionConfig;
  command_flags: CommandFlags;
  debug: DebugConfig;
  input_format: InputFormat;
  tool_restrictions: ToolRestrictions;
  claude_model_config: ClaudeModelConfig;
  directory_config: DirectoryConfig;
  conversation_config: ConversationConfig;
  system_prompt_config: SystemPromptConfig;
  verbose: boolean;
  default_timeout: number;
}

// Default configurations
export const DEFAULT_RETRY_CONFIG: RetryConfig = {
  max_retries: 3,
  initial_delay: 1.0,
  max_delay: 60.0,
  exponential_base: 2.0,
  retry_on: ['TimeoutError', 'ConnectionError']
};

export const DEFAULT_RATE_LIMIT_CONFIG: RateLimitConfig = {
  requests_per_minute: 60,
  requests_per_hour: 1000,
  burst_size: 10,
  enabled: true
};

export const DEFAULT_STREAM_CONFIG: StreamConfig = {
  buffer_size: 65536,
  timeout_between_chunks: 30.0,
  yield_raw: false
};

export const DEFAULT_SESSION_CONFIG: SessionConfig = {
  maintain_context: true,
  max_history_size: 100,
  persist_to_file: undefined,
  auto_save: true
};

export const DEFAULT_DEBUG_CONFIG: DebugConfig = {
  enabled: false
};

export const DEFAULT_INPUT_FORMAT: InputFormat = {
  format: 'text'
};

export const DEFAULT_TOOL_RESTRICTIONS: ToolRestrictions = {
  allowed_tools: undefined,
  disallowed_tools: undefined
};

export const DEFAULT_CLAUDE_MODEL_CONFIG: ClaudeModelConfig = {
  model: 'sonnet',
  fallback_model: undefined
};

export const DEFAULT_DIRECTORY_CONFIG: DirectoryConfig = {
  additional_dirs: []
};

export const DEFAULT_CONVERSATION_CONFIG: ConversationConfig = {
  continue_last: false,
  resume_session_id: undefined
};

export const DEFAULT_SYSTEM_PROMPT_CONFIG: SystemPromptConfig = {
  system_prompt: undefined
};

export const DEFAULT_COMMAND_FLAGS: CommandFlags = {
  allowed_flags: [
    '--temperature', '--max-tokens', '--stop-sequence',
    '-d', '--debug', '--input-format', '--allowedTools',
    '--disallowedTools', '-c', '--continue', '-r', '--resume',
    '--model', '--fallback-model', '--add-dir', '--append-system-prompt'
  ],
  custom_flags: {},
  override_defaults: false
};

export const DEFAULT_API_CONFIG: APIConfig = {
  retry: DEFAULT_RETRY_CONFIG,
  rate_limit: DEFAULT_RATE_LIMIT_CONFIG,
  streaming: DEFAULT_STREAM_CONFIG,
  session: DEFAULT_SESSION_CONFIG,
  command_flags: DEFAULT_COMMAND_FLAGS,
  debug: DEFAULT_DEBUG_CONFIG,
  input_format: DEFAULT_INPUT_FORMAT,
  tool_restrictions: DEFAULT_TOOL_RESTRICTIONS,
  claude_model_config: DEFAULT_CLAUDE_MODEL_CONFIG,
  directory_config: DEFAULT_DIRECTORY_CONFIG,
  conversation_config: DEFAULT_CONVERSATION_CONFIG,
  system_prompt_config: DEFAULT_SYSTEM_PROMPT_CONFIG,
  verbose: true,
  default_timeout: 300
};