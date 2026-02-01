import React from "react";
import { twMerge } from "tailwind-merge";
import type { TableWrapperProps, MarkdownComponentProps } from "~/types/markdown";

/**
 * Table wrapper with responsive design and scroll indicators
 * Memoized to prevent unnecessary re-renders of complex tables
 */
export const TableWrapper = React.memo(function TableWrapper({ children, ...props }: TableWrapperProps & React.TableHTMLAttributes<HTMLTableElement>) {
  const tableId = `table-${Math.random().toString(36).substr(2, 9)}`;
  
  return (
    <div 
      className="overflow-x-auto my-4 relative scrollbar-thin scrollbar-thumb-rounded scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-700"
      role="region"
      aria-labelledby={`${tableId}-caption`}
      tabIndex={0}
    >
      {/* Screen reader announcement for scrollable table */}
      <div id={`${tableId}-caption`} className="sr-only">
        Data table with horizontal scrolling available. Use arrow keys to navigate.
      </div>
      
      <table 
        id={tableId}
        className="min-w-full border border-gray-300 dark:border-gray-700 text-sm rounded-lg overflow-hidden bg-white dark:bg-gray-900" 
        role="table"
        aria-describedby={`${tableId}-caption`}
        {...props}
      >
        {children}
      </table>
      
      {/* Fade effect for scroll indication */}
      <div 
        className="pointer-events-none absolute top-0 right-0 h-full w-6 bg-gradient-to-l from-white/80 dark:from-gray-900/80 to-transparent"
        aria-hidden="true"
      />
    </div>
  );
});

/**
 * Table header cell with proper styling
 */
export function TableHead(props: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th 
      className="px-4 py-2 text-left font-semibold bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-200 border-b border-gray-300 dark:border-gray-700 first:rounded-tl-lg last:rounded-tr-lg" 
      scope="col"
      role="columnheader"
      {...props} 
    />
  );
}

/**
 * Table row component
 */
export function TableRow(props: React.HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr 
      className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors" 
      {...props} 
    />
  );
}

/**
 * Table data cell with proper styling
 */
export function TableCell(props: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td 
      className="px-4 py-2 border-b border-gray-200 dark:border-gray-700 align-top bg-transparent" 
      role="cell"
      {...props} 
    />
  );
}

/**
 * Table body wrapper
 */
export function TableBody(props: React.HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody {...props} />;
}

/**
 * Table header wrapper
 */
export function TableHeader(props: React.HTMLAttributes<HTMLTableSectionElement>) {
  return <thead {...props} />;
}

export default TableWrapper;