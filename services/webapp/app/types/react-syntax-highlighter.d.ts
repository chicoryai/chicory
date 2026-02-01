/**
 * Type declarations for react-syntax-highlighter
 * Fix for React 18 compatibility issues
 */

declare module 'react-syntax-highlighter' {
  import { Component } from 'react';
  
  export interface SyntaxHighlighterProps {
    language?: string;
    style?: any;
    customStyle?: any;
    showLineNumbers?: boolean;
    wrapLines?: boolean;
    PreTag?: any;
    className?: string;
    children?: any;
    [key: string]: any;
  }

  export class Prism extends Component<SyntaxHighlighterProps> {
    static registerLanguage(name: string, func: any): void;
  }
  
  export class Light extends Component<SyntaxHighlighterProps> {
    static registerLanguage(name: string, func: any): void;
  }
}

declare module 'react-syntax-highlighter/dist/esm/languages/prism/*' {
  const language: any;
  export default language;
}