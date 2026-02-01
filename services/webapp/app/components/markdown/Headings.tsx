import React from "react";
import { twMerge } from "tailwind-merge";
import { CopyButton } from "./CopyButton";
import type { HeadingProps } from "~/types/markdown";

/**
 * Heading components with copy link functionality
 */
export function Heading({ level, children, ...props }: HeadingProps) {
  const Tag = `h${level}` as keyof JSX.IntrinsicElements;
  
  // Generate id for anchor
  const text = React.Children.toArray(children).join("");
  const id = typeof text === "string"
    ? text
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, "")
        .replace(/\s+/g, "-")
    : undefined;

  return (
    <Tag
      id={id}
      className={twMerge(
        "group scroll-mt-20 flex items-center font-bold text-gray-900 dark:text-white",
        level === 1 && "text-3xl mt-4 mb-3",
        level === 2 && "text-2xl mt-3 mb-2",
        level === 3 && "text-xl mt-2 mb-1.5",
        level > 3 && "text-lg mt-2 mb-1"
      )}
      {...props}
    >
      <span>{children}</span>
      {id && (
        <CopyButton 
          value={`#${id}`} 
          className="group-hover:opacity-100 opacity-0 ml-2" 
          tooltip="Copy link" 
        />
      )}
    </Tag>
  );
}

// Export individual heading components for convenience
export const H1 = (props: Omit<HeadingProps, 'level'>) => <Heading level={1} {...props} />;
export const H2 = (props: Omit<HeadingProps, 'level'>) => <Heading level={2} {...props} />;
export const H3 = (props: Omit<HeadingProps, 'level'>) => <Heading level={3} {...props} />;
export const H4 = (props: Omit<HeadingProps, 'level'>) => <Heading level={4} {...props} />;
export const H5 = (props: Omit<HeadingProps, 'level'>) => <Heading level={5} {...props} />;
export const H6 = (props: Omit<HeadingProps, 'level'>) => <Heading level={6} {...props} />;

export default Heading;