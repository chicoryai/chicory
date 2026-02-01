import React from "react";
import type { MarkdownComponentProps, LinkProps, ImageProps } from "~/types/markdown";

/**
 * Paragraph component with proper spacing
 */
export function Paragraph(props: MarkdownComponentProps & React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className="mb-2 leading-relaxed text-gray-800 dark:text-gray-200" {...props} />;
}

/**
 * Blockquote component with styling
 */
export function Blockquote(props: MarkdownComponentProps & React.BlockquoteHTMLAttributes<HTMLElement>) {
  return (
    <blockquote
      className="border-l-4 border-purple-400 dark:border-purple-600 bg-purple-50 dark:bg-purple-900/30 pl-4 pr-2 py-2 my-4 italic text-gray-700 dark:text-gray-200 rounded"
      {...props}
    />
  );
}

/**
 * Horizontal rule component
 */
export function Hr(props: React.HTMLAttributes<HTMLHRElement>) {
  return <hr className="my-6 border-t border-gray-300 dark:border-gray-600" {...props} />;
}

/**
 * Emphasis (italic) component
 */
export function Em(props: MarkdownComponentProps & React.HTMLAttributes<HTMLElement>) {
  return <em className="italic" {...props} />;
}

/**
 * Strong (bold) component
 */
export function Strong(props: MarkdownComponentProps & React.HTMLAttributes<HTMLElement>) {
  return <strong className="font-semibold text-gray-900 dark:text-white" {...props} />;
}

/**
 * Strikethrough component
 */
export function Del(props: MarkdownComponentProps & React.HTMLAttributes<HTMLElement>) {
  return <del className="line-through text-gray-500 dark:text-gray-400" {...props} />;
}

/**
 * Line break component
 */
export function Br() {
  return <br />;
}

/**
 * Link component with external link handling
 */
export function CustomLink(props: LinkProps) {
  const { href, children, ...otherProps } = props;
  
  // Check if it's an external link
  const isExternal = href && (href.startsWith('http') || href.startsWith('https'));
  
  return (
    <a
      {...otherProps}
      href={href}
      target={isExternal ? "_blank" : undefined}
      rel={isExternal ? "noopener noreferrer" : undefined}
      className="text-purple-600 dark:text-purple-400 underline hover:text-purple-800 dark:hover:text-purple-300 break-words transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 rounded"
    >
      {children}
    </a>
  );
}

/**
 * Image component with lazy loading
 */
export function CustomImage(props: ImageProps) {
  const { src, alt, ...otherProps } = props;
  
  return (
    <img 
      {...otherProps}
      src={src}
      alt={alt}
      loading="lazy" 
      className="rounded max-w-full h-auto shadow-sm border border-gray-200 dark:border-gray-700" 
    />
  );
}

export default {
  Paragraph,
  Blockquote,
  Hr,
  Em,
  Strong,
  Del,
  Br,
  CustomLink,
  CustomImage,
};