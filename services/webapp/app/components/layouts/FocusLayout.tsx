import { type ReactNode } from "react";

interface FocusLayoutProps {
    /** The main content area (middle column) */
    children: ReactNode;
    /** The left sidebar or navigation (optional) */
    sidebar?: ReactNode;
    /** The right panel or details view (optional) */
    panel?: ReactNode;
    /** Fixed header element */
    header?: ReactNode;
    /** Fixed footer element */
    footer?: ReactNode;
    className?: string;
}

/**
 * FocusLayout
 * A specialized layout for "Application" interfaces (Chat, IDE, Maps).
 *
 * Architecture:
 * - Root: h-full, overflow-hidden (fills parent)
 * - Header/Footer: flex-shrink-0
 * - Content: flex-1 with min-h-0 to allow shrinking
 */
export function FocusLayout({
    children,
    sidebar,
    panel,
    header,
    footer,
    className = ""
}: FocusLayoutProps) {
    return (
        <div className={`h-full flex flex-col overflow-hidden bg-white dark:bg-gray-900 ${className}`}>
            {/* Header - fixed at top */}
            {header && (
                <header className="flex-shrink-0 z-20">
                    {header}
                </header>
            )}

            {/* Content area - fills remaining space */}
            <div className="flex-1 min-h-0 flex overflow-hidden">
                {/* Left Sidebar */}
                {sidebar && (
                    <aside className="hidden md:block w-64 lg:w-72 border-r border-gray-200 dark:border-gray-800 overflow-y-auto bg-gray-50 dark:bg-gray-950/30">
                        {sidebar}
                    </aside>
                )}

                {/* Main content */}
                <main className="flex-1 min-w-0 overflow-hidden">
                    {children}
                </main>

                {/* Right Panel */}
                {panel && (
                    <aside className="hidden lg:block w-80 border-l border-gray-200 dark:border-gray-800 overflow-y-auto bg-gray-50 dark:bg-gray-950/30">
                        {panel}
                    </aside>
                )}
            </div>

            {/* Footer - fixed at bottom */}
            {footer && (
                <footer className="flex-shrink-0 z-20 bg-white dark:bg-gray-900">
                    {footer}
                </footer>
            )}
        </div>
    );
}
