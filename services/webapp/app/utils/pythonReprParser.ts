/**
 * Parser for Python repr() string representations
 * Handles parsing of Python objects like AssistantMessage, ToolUseBlock, etc.
 */
export class PythonReprParser {
  private pos = 0;
  private input = '';

  /**
   * Parse a Python repr string
   */
  parse(input: string): any {
    this.input = input;
    this.pos = 0;
    return this.parseValue();
  }

  private parseValue(): any {
    this.skipWhitespace();

    // Check for named objects
    if (this.matchWord('AssistantMessage')) return this.parseNamedObject('AssistantMessage');
    if (this.matchWord('ResultMessage')) return this.parseNamedObject('ResultMessage');
    if (this.matchWord('UserMessage')) return this.parseNamedObject('UserMessage');
    if (this.matchWord('ToolUseBlock')) return this.parseNamedObject('ToolUseBlock');
    if (this.matchWord('TextBlock')) return this.parseNamedObject('TextBlock');
    if (this.matchWord('ToolResultBlock')) return this.parseNamedObject('ToolResultBlock');

    // Parse literals
    if (this.peek() === "'" || this.peek() === '"') return this.parseString();
    if (this.peek() === '{') return this.parseDict();
    if (this.peek() === '[') return this.parseList();
    if (this.match('True')) return true;
    if (this.match('False')) return false;
    if (this.match('None')) return null;
    
    // Parse numbers
    if (this.isDigit(this.peek()) || this.peek() === '-' || this.peek() === '.') {
      return this.parseNumber();
    }

    // Parse identifiers (for unquoted values)
    if (this.isAlpha(this.peek())) {
      return this.parseIdentifier();
    }

    throw new Error(`Unexpected character at position ${this.pos}: '${this.peek()}'`);
  }

  private parseNamedObject(typeName: string): any {
    const result: Record<string, any> = { __type__: typeName };
    
    this.expect('(');
    this.skipWhitespace();

    // Parse key=value pairs
    while (!this.check(')')) {
      const key = this.parseIdentifier();
      this.skipWhitespace();
      this.expect('=');
      this.skipWhitespace();
      const value = this.parseValue();
      result[key] = value;

      this.skipWhitespace();
      if (!this.check(')')) {
        this.expect(',');
        this.skipWhitespace();
      }
    }

    this.expect(')');
    return result;
  }

  private parseString(): string {
    const quote = this.peek();
    if (quote !== "'" && quote !== '"') {
      throw new Error(`Expected string quote at position ${this.pos}`);
    }

    this.advance(); // Skip opening quote
    let result = '';
    let escaped = false;

    while (!this.isAtEnd() && (escaped || this.peek() !== quote)) {
      if (escaped) {
        // Handle escape sequences
        const char = this.peek();
        switch (char) {
          case 'n': result += '\n'; break;
          case 't': result += '\t'; break;
          case 'r': result += '\r'; break;
          case '\\': result += '\\'; break;
          case "'": result += "'"; break;
          case '"': result += '"'; break;
          default: result += char;
        }
        escaped = false;
      } else if (this.peek() === '\\') {
        escaped = true;
      } else {
        result += this.peek();
      }
      this.advance();
    }

    if (this.isAtEnd()) {
      throw new Error(`Unterminated string at position ${this.pos}`);
    }

    this.advance(); // Skip closing quote
    return result;
  }

  private parseDict(): Record<string, any> {
    const result: Record<string, any> = {};
    
    this.expect('{');
    this.skipWhitespace();

    while (!this.check('}')) {
      // Parse key (can be string or identifier)
      let key: string;
      if (this.peek() === "'" || this.peek() === '"') {
        key = this.parseString();
      } else {
        key = this.parseIdentifier();
      }

      this.skipWhitespace();
      this.expect(':');
      this.skipWhitespace();
      
      const value = this.parseValue();
      result[key] = value;

      this.skipWhitespace();
      if (!this.check('}')) {
        this.expect(',');
        this.skipWhitespace();
      }
    }

    this.expect('}');
    return result;
  }

  private parseList(): any[] {
    const result: any[] = [];
    
    this.expect('[');
    this.skipWhitespace();

    while (!this.check(']')) {
      result.push(this.parseValue());
      
      this.skipWhitespace();
      if (!this.check(']')) {
        this.expect(',');
        this.skipWhitespace();
      }
    }

    this.expect(']');
    return result;
  }

  private parseNumber(): number {
    let numStr = '';
    
    // Handle negative numbers
    if (this.peek() === '-') {
      numStr += this.advance();
    }

    // Parse digits before decimal
    while (!this.isAtEnd() && this.isDigit(this.peek())) {
      numStr += this.advance();
    }

    // Parse decimal part
    if (this.peek() === '.') {
      numStr += this.advance();
      while (!this.isAtEnd() && this.isDigit(this.peek())) {
        numStr += this.advance();
      }
    }

    // Parse scientific notation
    if (this.peek() === 'e' || this.peek() === 'E') {
      numStr += this.advance();
      if (this.peek() === '+' || this.peek() === '-') {
        numStr += this.advance();
      }
      while (!this.isAtEnd() && this.isDigit(this.peek())) {
        numStr += this.advance();
      }
    }

    return parseFloat(numStr);
  }

  private parseIdentifier(): string {
    let result = '';
    
    while (!this.isAtEnd() && (this.isAlphaNumeric(this.peek()) || this.peek() === '_')) {
      result += this.advance();
    }
    
    return result;
  }

  // Helper methods
  private skipWhitespace(): void {
    while (!this.isAtEnd() && /\s/.test(this.peek())) {
      this.advance();
    }
  }

  private peek(): string {
    if (this.isAtEnd()) return '\0';
    return this.input[this.pos];
  }

  private advance(): string {
    if (!this.isAtEnd()) this.pos++;
    return this.input[this.pos - 1];
  }

  private check(expected: string): boolean {
    if (this.isAtEnd()) return false;
    return this.input.substring(this.pos, this.pos + expected.length) === expected;
  }

  private match(expected: string): boolean {
    if (this.check(expected)) {
      this.pos += expected.length;
      return true;
    }
    return false;
  }

  private matchWord(word: string): boolean {
    // Check if the word matches and is followed by '(' or non-alphanumeric
    if (!this.check(word)) return false;
    
    const nextPos = this.pos + word.length;
    if (nextPos < this.input.length) {
      const nextChar = this.input[nextPos];
      if (this.isAlphaNumeric(nextChar) || nextChar === '_') {
        return false; // Part of a longer identifier
      }
    }
    
    this.pos += word.length;
    return true;
  }

  private expect(expected: string): void {
    if (!this.match(expected)) {
      throw new Error(`Expected '${expected}' at position ${this.pos}, got '${this.peek()}'`);
    }
  }

  private isAtEnd(): boolean {
    return this.pos >= this.input.length;
  }

  private isDigit(char: string): boolean {
    return /[0-9]/.test(char);
  }

  private isAlpha(char: string): boolean {
    return /[a-zA-Z]/.test(char);
  }

  private isAlphaNumeric(char: string): boolean {
    return /[a-zA-Z0-9]/.test(char);
  }
}

/**
 * Transform parsed Python objects into more usable JavaScript structures
 */
export function transformParsedMessage(parsed: any): any {
  if (!parsed || typeof parsed !== 'object') return parsed;

  // Handle named objects
  if (parsed.__type__) {
    switch (parsed.__type__) {
      case 'AssistantMessage':
        return {
          type: 'assistant',
          content: transformContent(parsed.content)
        };
      
      case 'ResultMessage':
        return {
          type: 'result',
          result: parsed.result,
          subtype: parsed.subtype,
          duration_ms: parsed.duration_ms,
          duration_api_ms: parsed.duration_api_ms,
          is_error: parsed.is_error,
          num_turns: parsed.num_turns,
          session_id: parsed.session_id,
          total_cost_usd: parsed.total_cost_usd,
          usage: parsed.usage
        };
      
      case 'UserMessage':
        return {
          type: 'user',
          content: transformContent(parsed.content)
        };
      
      case 'ToolUseBlock':
        return {
          type: 'tool_use',
          id: parsed.id,
          name: parsed.name,
          input: parsed.input
        };
      
      case 'TextBlock':
        return {
          type: 'text',
          text: parsed.text
        };
      
      case 'ToolResultBlock':
        return {
          type: 'tool_result',
          tool_use_id: parsed.tool_use_id,
          content: parsed.content
        };
      
      default:
        return parsed;
    }
  }

  // Recursively transform nested structures
  if (Array.isArray(parsed)) {
    return parsed.map(transformParsedMessage);
  }

  const result: any = {};
  for (const [key, value] of Object.entries(parsed)) {
    result[key] = transformParsedMessage(value);
  }
  return result;
}

function transformContent(content: any): any {
  if (Array.isArray(content)) {
    return content.map(transformParsedMessage);
  }
  return transformParsedMessage(content);
}