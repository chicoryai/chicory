import React from "react";
import type { ListItemProps, MarkdownComponentProps } from "~/types/markdown";

/**
 * Unordered list component with enhanced nested styling
 */
export function UnorderedList(props: MarkdownComponentProps & React.HTMLAttributes<HTMLUListElement>) {
  return (
    <ul 
      className="list-disc pl-6 mb-3 space-y-2 
        [&_ul]:mt-2 [&_ul]:mb-2 [&_ul]:pl-4 [&_ul]:list-[circle] 
        [&_ol]:mt-2 [&_ol]:mb-2 [&_ol]:pl-4
        [&_ul_ul]:list-[square] [&_ul_ul]:pl-4
        [&>li>*:not(ul):not(ol)]:pl-4 [&>li>p]:pl-4 [&>li>div]:pl-4" 
      {...props} 
    />
  );
}

/**
 * Ordered list component with enhanced nested styling
 */
export function OrderedList(props: MarkdownComponentProps & React.OlHTMLAttributes<HTMLOListElement>) {
  return (
    <ol 
      className="list-decimal pl-6 mb-3 space-y-2
        [&_ul]:mt-2 [&_ul]:mb-2 [&_ul]:pl-4 [&_ul]:list-disc
        [&_ol]:mt-2 [&_ol]:mb-2 [&_ol]:pl-4 [&_ol]:list-[lower-alpha]
        [&_ol_ol]:list-[lower-roman] [&_ol_ol]:pl-4
        [&>li>*:not(ul):not(ol)]:pl-4 [&>li>p]:pl-4 [&>li>div]:pl-4" 
      {...props} 
    />
  );
}

/**
 * List item component with support for interactive task lists
 */
export function ListItem(props: ListItemProps) {
  const { checked, children, ...otherProps } = props;
  
  // Task list items have a 'checked' prop
  if (typeof checked === 'boolean') {
    const [isChecked, setIsChecked] = React.useState(checked);
    
    const handleToggle = () => {
      setIsChecked(!isChecked);
      // Optional: Emit custom event for external handling
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('taskToggle', { 
          detail: { checked: !isChecked, content: children } 
        }));
      }
    };

    return (
      <li className="flex items-start gap-2" {...otherProps}>
        <button
          onClick={handleToggle}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              handleToggle();
            }
          }}
          className="mt-1 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 rounded"
          aria-label={`Task: ${isChecked ? 'completed' : 'incomplete'}`}
          aria-pressed={isChecked}
        >
          <input
            type="checkbox"
            checked={isChecked}
            readOnly
            tabIndex={-1}
            className="accent-purple-600 dark:accent-purple-400 pointer-events-none"
          />
        </button>
        <span 
          className={`flex-1 transition-colors ${
            isChecked 
              ? 'line-through text-gray-500 dark:text-gray-400' 
              : 'text-gray-800 dark:text-gray-200'
          }`}
        >
          {children}
        </span>
      </li>
    );
  }
  
  return <li className="ml-1" {...otherProps}>{children}</li>;
}

export default { UnorderedList, OrderedList, ListItem };