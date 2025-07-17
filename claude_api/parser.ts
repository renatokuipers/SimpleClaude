/**
 * Parser for Claude API JSON stream responses with streaming support (TypeScript version)
 */

import {
  SystemInit,
  AssistantResponse,
  UserResponse,
  ResultSummary,
  ClaudeResponse,
  ClaudeResponseImpl,
  AssistantMessage,
  UserMessage,
  TextContent,
  ThinkingContent,
  ToolUseContent,
  ToolResultContent,
  Usage,
  ExtendedUsage,
  ServerToolUse,
  StreamConfig,
  DEFAULT_STREAM_CONFIG,
  MessageContent,
  UserContent
} from './models';

export class ClaudeResponseParser {
  public system_init?: SystemInit;
  public assistant_responses: AssistantResponse[] = [];
  public user_responses: UserResponse[] = [];
  public result_summary?: ResultSummary;
  public raw_lines: string[] = [];
  public events: Record<string, any>[] = [];

  constructor() {
    // Initialize parser
  }

  parse_line(line: string): SystemInit | AssistantResponse | UserResponse | ResultSummary | null {
    if (!line.trim()) {
      return null;
    }

    try {
      // Clean the line - remove any extra whitespace and non-JSON content
      const cleanLine = line.trim();
      
      // Skip lines that don't start with { (not JSON)
      if (!cleanLine.startsWith('{')) {
        return null;
      }

      // Check if line ends with } (complete JSON)
      if (!cleanLine.endsWith('}')) {
        return null;
      }

      const data = JSON.parse(cleanLine);
      this.raw_lines.push(cleanLine);
      this.events.push(data);

      if (data.type === 'system' && data.subtype === 'init') {
        this.system_init = data as SystemInit;
        return this.system_init;
      } else if (data.type === 'assistant') {
        // Parse assistant message with proper content types
        const message_data = data.message || {};
        const content_list: MessageContent[] = [];

        for (const content of message_data.content || []) {
          const content_type = content.type;

          if (content_type === 'text') {
            content_list.push(content as TextContent);
          } else if (content_type === 'thinking') {
            content_list.push(content as ThinkingContent);
          } else if (content_type === 'tool_use') {
            content_list.push(content as ToolUseContent);
          } else {
            // Skip unknown content types
            console.warn(`Unknown content type: ${content_type}`);
            continue;
          }
        }

        // Create AssistantMessage with parsed content
        const assistant_msg: AssistantMessage = {
          ...message_data,
          content: content_list
        };

        // Create AssistantResponse
        const assistant_response: AssistantResponse = {
          type: 'assistant',
          message: assistant_msg,
          parent_tool_use_id: data.parent_tool_use_id,
          session_id: data.session_id
        };

        this.assistant_responses.push(assistant_response);
        return assistant_response;
      } else if (data.type === 'user') {
        // Parse user message (tool results)
        const message_data = data.message || {};
        const content_list: UserContent[] = [];

        for (const content of message_data.content || []) {
          if (content.type === 'tool_result') {
            // Handle case where content field is a list of content objects
            const content_field = content.content || '';
            let content_text: string;

            if (Array.isArray(content_field)) {
              // Extract text from content objects
              const text_parts: string[] = [];
              for (const content_obj of content_field) {
                if (typeof content_obj === 'object' && content_obj.type === 'text') {
                  text_parts.push(content_obj.text || '');
                }
              }
              content_text = text_parts.join('');
            } else {
              content_text = String(content_field);
            }

            // Create ToolResultContent with extracted text
            const tool_result: ToolResultContent = {
              tool_use_id: content.tool_use_id || '',
              type: 'tool_result',
              content: content_text,
              is_error: content.is_error || false
            };
            content_list.push(tool_result);
          }
        }

        // Create UserMessage with parsed content
        const user_msg: UserMessage = {
          ...message_data,
          content: content_list
        };

        // Create UserResponse
        const user_response: UserResponse = {
          type: 'user',
          message: user_msg,
          parent_tool_use_id: data.parent_tool_use_id,
          session_id: data.session_id
        };

        this.user_responses.push(user_response);
        return user_response;
      } else if (data.type === 'result') {
        try {
          this.result_summary = data as ResultSummary;
          return this.result_summary;
        } catch (validation_error) {
          console.warn(`Warning: Could not parse result summary: ${validation_error}`);
          // Create a minimal result summary with available data
          this.result_summary = {
            type: 'result',
            subtype: data.subtype || 'unknown',
            is_error: data.is_error || true,
            session_id: data.session_id || '',
            duration_ms: data.duration_ms || 0,
            duration_api_ms: data.duration_api_ms || 0,
            num_turns: data.num_turns || 0,
            result: data.result || '',
            total_cost_usd: data.total_cost_usd || 0,
            usage: data.usage
          };
          return this.result_summary;
        }
      }
    } catch (error) {
      console.error(`Error parsing line: ${error}`);
      return null;
    }

    return null;
  }

  parse_stream(stream: string): ClaudeResponse {
    const lines = stream.trim().split('\n');

    for (const line of lines) {
      this.parse_line(line);
    }

    const response = new ClaudeResponseImpl();
    response.system_init = this.system_init;
    response.assistant_responses = this.assistant_responses;
    response.user_responses = this.user_responses;
    response.result_summary = this.result_summary;
    response.raw_response = stream;

    return response;
  }

  get_message_text(): string {
    const texts: string[] = [];
    for (const response of this.assistant_responses) {
      for (const content of response.message.content) {
        if (content.type === 'text') {
          texts.push((content as TextContent).text);
        }
      }
    }
    return texts.join('\n');
  }

  get_tool_uses(): ToolUseContent[] {
    const tool_uses: ToolUseContent[] = [];
    for (const response of this.assistant_responses) {
      for (const content of response.message.content) {
        if (content.type === 'tool_use') {
          tool_uses.push(content as ToolUseContent);
        }
      }
    }
    return tool_uses;
  }

  get_thinking(): string[] {
    const thoughts: string[] = [];
    for (const response of this.assistant_responses) {
      for (const content of response.message.content) {
        if (content.type === 'thinking') {
          thoughts.push((content as ThinkingContent).thinking);
        }
      }
    }
    return thoughts;
  }

  get_tool_results(): ToolResultContent[] {
    const results: ToolResultContent[] = [];
    for (const response of this.user_responses) {
      for (const content of response.message.content) {
        if (content.type === 'tool_result') {
          results.push(content as ToolResultContent);
        }
      }
    }
    return results;
  }

  get_usage_summary(): ExtendedUsage | null {
    return this.result_summary?.usage || null;
  }

  get_cost(): number | null {
    return this.result_summary?.total_cost_usd || null;
  }

  was_successful(): boolean {
    return (
      this.result_summary !== undefined &&
      !this.result_summary.is_error &&
      this.result_summary.subtype === 'success'
    );
  }

  *get_event_stream(): Generator<Record<string, any>, void, unknown> {
    for (const event of this.events) {
      yield event;
    }
  }
}

export class StreamingResponseParser {
  private config: StreamConfig;
  private buffer: string = '';
  public parser: ClaudeResponseParser;

  constructor(config?: StreamConfig) {
    this.config = config || DEFAULT_STREAM_CONFIG;
    this.parser = new ClaudeResponseParser();
  }

  *parse_chunk(chunk: string): Generator<SystemInit | AssistantResponse | UserResponse | ResultSummary | string, void, unknown> {
    this.buffer += chunk;

    while (this.buffer.includes('\n')) {
      const newlineIndex = this.buffer.indexOf('\n');
      const line = this.buffer.substring(0, newlineIndex);
      this.buffer = this.buffer.substring(newlineIndex + 1);

      const cleanLine = line.trim();
      if (cleanLine && cleanLine.startsWith('{')) {
        if (this.config.yield_raw) {
          // Yield raw JSON string
          yield cleanLine;
        } else {
          // Parse and yield structured event
          const event = this.parser.parse_line(cleanLine);
          if (event) {
            yield event;
          }
        }
      }
    }
  }

  *flush(): Generator<SystemInit | AssistantResponse | UserResponse | ResultSummary | string, void, unknown> {
    const cleanBuffer = this.buffer.trim();
    if (cleanBuffer && cleanBuffer.startsWith('{')) {
      if (this.config.yield_raw) {
        yield cleanBuffer;
      } else {
        const event = this.parser.parse_line(cleanBuffer);
        if (event) {
          yield event;
        }
      }
    }
    this.buffer = '';
  }

  get_response(): ClaudeResponse {
    const response = new ClaudeResponseImpl();
    response.system_init = this.parser.system_init;
    response.assistant_responses = this.parser.assistant_responses;
    response.user_responses = this.parser.user_responses;
    response.result_summary = this.parser.result_summary;
    response.raw_response = this.parser.raw_lines.join('\n');

    return response;
  }
}

// Convenience functions

export function parse_claude_stream(stream: string): ClaudeResponse {
  const parser = new ClaudeResponseParser();
  return parser.parse_stream(stream);
}

export function* stream_parse_generator(
  stream: Generator<string, void, unknown>,
  config?: StreamConfig
): Generator<SystemInit | AssistantResponse | UserResponse | ResultSummary | string, void, unknown> {
  const parser = new StreamingResponseParser(config);

  for (const chunk of stream) {
    yield* parser.parse_chunk(chunk);
  }

  // Flush any remaining content
  yield* parser.flush();
}

export async function* async_stream_parse_generator(
  stream: AsyncGenerator<string, void, unknown>,
  config?: StreamConfig
): AsyncGenerator<SystemInit | AssistantResponse | UserResponse | ResultSummary | string, void, unknown> {
  const parser = new StreamingResponseParser(config);

  for await (const chunk of stream) {
    for (const event of parser.parse_chunk(chunk)) {
      yield event;
    }
  }

  // Flush any remaining content
  for (const event of parser.flush()) {
    yield event;
  }
}