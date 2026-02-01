/**
 * Barrel export for all markdown components
 * Provides a clean interface for importing markdown components
 */

import React from 'react';

// Core components
export { CopyButton } from './CopyButton';
export { CodeBlock } from './CodeBlock';
export { TableWrapper, TableHead, TableRow, TableCell, TableBody, TableHeader } from './Table';
export { Heading, H1, H2, H3, H4, H5, H6 } from './Headings';
export { UnorderedList, OrderedList, ListItem } from './Lists';
export { 
  Paragraph, 
  Blockquote, 
  Hr, 
  Em, 
  Strong, 
  Del, 
  Br, 
  CustomLink, 
  CustomImage 
} from './Typography';

// Re-export types for convenience
export type { 
  CopyButtonProps, 
  CodeBlockProps, 
  TableWrapperProps, 
  HeadingProps, 
  ListItemProps,
  LinkProps,
  ImageProps,
  MarkdownComponentProps 
} from '~/types/markdown';

// Component map for react-markdown
import type { Components } from 'react-markdown';
import { CodeBlock } from './CodeBlock';
import { TableWrapper, TableHead, TableRow, TableCell, TableBody, TableHeader } from './Table';
import { Heading } from './Headings';
import { UnorderedList, OrderedList, ListItem } from './Lists';
import { 
  Paragraph, 
  Blockquote, 
  Hr, 
  Em, 
  Strong, 
  Del, 
  Br, 
  CustomLink, 
  CustomImage 
} from './Typography';

/**
 * Components mapping for ReactMarkdown
 * Updated to use the new modular components
 */
export const markdownComponents: Components = {
  // Headings
  h1: (props: any) => <Heading level={1} {...props} />,
  h2: (props: any) => <Heading level={2} {...props} />, 
  h3: (props: any) => <Heading level={3} {...props} />, 
  h4: (props: any) => <Heading level={4} {...props} />, 
  h5: (props: any) => <Heading level={5} {...props} />, 
  h6: (props: any) => <Heading level={6} {...props} />, 
  
  // Typography
  p: Paragraph,
  blockquote: Blockquote,
  hr: Hr,
  em: Em,
  strong: Strong,
  del: Del,
  br: Br,
  a: CustomLink,
  img: CustomImage,
  
  // Code
  code: CodeBlock,
  
  // Lists
  ul: UnorderedList,
  ol: OrderedList,
  li: ListItem,
  
  // Tables
  table: TableWrapper,
  thead: TableHeader,
  tbody: TableBody,
  tr: TableRow,
  th: TableHead,
  td: TableCell,
};