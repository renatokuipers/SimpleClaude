/**
 * Simple data models for toddler-friendly Claude API (TypeScript version)
 */

export interface SimpleResponse {
  /** The complete text response from Claude */
  text: string;
  
  /** How much this request cost in USD */
  cost: number;
  
  /** Total tokens consumed (input + output) */
  tokens_used: number;
  
  /** Which model was used (e.g., 'claude-3-sonnet') */
  model: string;
  
  /** Whether the request was successful */
  success: boolean;
  
  /** Session ID for this conversation */
  session_id?: string;
  
  /** How long the request took in seconds */
  duration_seconds: number;
  
  /** Claude's internal thinking process (if available) */
  thinking?: string;
  
  /** Tools that Claude used during this response */
  tool_uses: Record<string, any>[];
  
  /** Results from the tools that Claude used */
  tool_results: Record<string, any>[];
}

export class SimpleResponseImpl implements SimpleResponse {
  text: string;
  cost: number;
  tokens_used: number;
  model: string;
  success: boolean;
  session_id?: string;
  duration_seconds: number;
  thinking?: string;
  tool_uses: Record<string, any>[];
  tool_results: Record<string, any>[];

  constructor(data: SimpleResponse) {
    this.text = data.text;
    this.cost = data.cost;
    this.tokens_used = data.tokens_used;
    this.model = data.model;
    this.success = data.success;
    this.session_id = data.session_id;
    this.duration_seconds = data.duration_seconds || 0.0;
    this.thinking = data.thinking;
    this.tool_uses = data.tool_uses || [];
    this.tool_results = data.tool_results || [];
  }

  /** Human-readable representation */
  toString(): string {
    return `SimpleResponse(text='${this.text}', cost=$${this.cost.toFixed(4)}, tokens=${this.tokens_used})`;
  }
}

export interface SimpleMetrics {
  /** Total cost for this session */
  total_cost: number;
  
  /** Total tokens used in this session */
  total_tokens: number;
  
  /** Number of requests made in this session */
  requests_count: number;
  
  /** Average response time in seconds */
  average_response_time: number;
}

export class SimpleMetricsImpl implements SimpleMetrics {
  total_cost: number;
  total_tokens: number;
  requests_count: number;
  average_response_time: number;

  constructor(data: SimpleMetrics) {
    this.total_cost = data.total_cost;
    this.total_tokens = data.total_tokens;
    this.requests_count = data.requests_count;
    this.average_response_time = data.average_response_time;
  }

  /** Human-readable metrics */
  toString(): string {
    return `📊 Session Stats: $${this.total_cost.toFixed(4)} spent, ` +
           `${this.total_tokens} tokens, ${this.requests_count} requests, ` +
           `${this.average_response_time.toFixed(1)}s avg response time`;
  }
}

export interface SimpleConfig {
  /** Model to use: 'sonnet' (default), 'opus', or 'haiku' */
  model: string;
  
  /** Whether to show Claude's internal thinking process */
  show_thinking: boolean;
  
  /** Whether to show metrics after each response */
  show_metrics: boolean;
  
  /** Whether to continue previous conversations automatically */
  auto_continue: boolean;
  
  /** Maximum number of retries on failure */
  max_retries: number;
  
  /** Request timeout in seconds */
  timeout_seconds: number;
  
  /** Show detailed debug information */
  verbose: boolean;
  
  /** System prompt to append to all requests */
  system_prompt?: string;
}

export class SimpleConfigImpl implements SimpleConfig {
  model: string;
  show_thinking: boolean;
  show_metrics: boolean;
  auto_continue: boolean;
  max_retries: number;
  timeout_seconds: number;
  verbose: boolean;
  system_prompt?: string;

  constructor(config: Partial<SimpleConfig> = {}) {
    this.model = config.model || "sonnet";
    this.show_thinking = config.show_thinking || false;
    this.show_metrics = config.show_metrics !== undefined ? config.show_metrics : true;
    this.auto_continue = config.auto_continue || false;
    this.max_retries = config.max_retries || 3;
    this.timeout_seconds = config.timeout_seconds || 300;
    this.verbose = config.verbose || false;
    this.system_prompt = config.system_prompt;
  }
}

// Default configurations
export const DEFAULT_SIMPLE_CONFIG: SimpleConfig = {
  model: "sonnet",
  show_thinking: false,
  show_metrics: true,
  auto_continue: false,
  max_retries: 3,
  timeout_seconds: 300,
  verbose: false,
  system_prompt: undefined
};