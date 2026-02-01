import { useState, useRef, useEffect } from "react";
import { ChevronLeftIcon, XMarkIcon, ChevronUpDownIcon } from "@heroicons/react/24/outline";
import { Dialog, Transition } from "@headlessui/react";
import { Fragment } from "react";
import PropTypes from "prop-types";

interface SideDrawerProps {
  children: React.ReactNode;
  defaultWidth?: number;
  minWidth?: number;
  maxWidth?: number;
  title?: string;
  isOpen?: boolean;
  onOpenChange?: (isOpen: boolean) => void;
}

export default function SideDrawer({
  children,
  defaultWidth = 320,
  minWidth = 200,
  maxWidth = 960,
  title = "Side Panel",
  isOpen: controlledIsOpen,
  onOpenChange,
}: SideDrawerProps) {
  // Use internal state if component is uncontrolled
  const [internalIsOpen, setInternalIsOpen] = useState(false);
  
  // Determine if we're in controlled or uncontrolled mode
  const isControlled = controlledIsOpen !== undefined;
  const isOpen = isControlled ? controlledIsOpen : internalIsOpen;
  
  const [width, setWidth] = useState(defaultWidth);
  const [isResizing, setIsResizing] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);
  const resizeHandleRef = useRef<HTMLDivElement>(null);

  // Handle toggle function
  const handleToggle = () => {
    if (isControlled) {
      // If controlled, call the callback
      onOpenChange?.(!isOpen);
    } else {
      // If uncontrolled, update internal state
      setInternalIsOpen(!isOpen);
    }
  };

  // Handle close function
  const handleClose = () => {
    if (isControlled) {
      // If controlled, call the callback
      onOpenChange?.(false);
    } else {
      // If uncontrolled, update internal state
      setInternalIsOpen(false);
    }
  };

  // Handle resize functionality
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing || !drawerRef.current) return;
      
      const drawerRect = drawerRef.current.getBoundingClientRect();
      const newWidth = Math.max(minWidth, Math.min(maxWidth, drawerRect.right - e.clientX));
      
      setWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      // Allow Escape key to close the drawer
      if (e.key === "Escape" && isOpen) {
        handleClose();
      }
    };

    if (isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    }

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isResizing, minWidth, maxWidth, isOpen, handleClose]);

  const handleResizeStart = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  };

  return (
    <div className="flex h-full relative shrink-0">
      {/* Toggle button - only visible when drawer is closed */}
      {!isOpen && (
        <button
          onClick={handleToggle}
          className="absolute top-1/2 left-0 z-20 flex h-16 w-6 -translate-y-1/2 translate-x-1 items-center justify-center rounded-r-lg border border-whitePurple-100/60 bg-white text-purple-500 shadow-md shadow-whitePurple-50/60 transition hover:bg-whitePurple-100/80 hover:text-purple-600 focus:outline-none focus:ring-2 focus:ring-purple-300 dark:border-whitePurple-200/30 dark:bg-white/10 dark:text-purple-200 dark:shadow-purple-900/30"
          aria-label="Open side panel"
          aria-expanded={false}
          aria-controls="side-drawer-panel"
        >
          <ChevronLeftIcon className="h-4 w-4" aria-hidden="true" />
        </button>
      )}

      {/* Drawer */}
      <Transition
        show={isOpen}
        as={Fragment}
        enter="transform transition ease-in-out duration-300"
        enterFrom="translate-x-full"
        enterTo="translate-x-0"
        leave="transform transition ease-in-out duration-300"
        leaveFrom="translate-x-0"
        leaveTo="translate-x-full"
      >
        <div
          id="side-drawer-panel"
          ref={drawerRef}
          className="dark:bg-gray-900 bg-white border-l dark:border-gray-800 border-gray-200 h-full overflow-y-auto flex flex-col shrink-0"
          style={{ width: `${width}px` }}
          role="complementary"
          aria-label={title}
        >
          {/* Close button in top right */}
          <button
            onClick={handleClose}
            className="absolute top-3 right-3 z-20 text-gray-400 hover:text-white p-1 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            aria-label="Close side panel"
          >
            <XMarkIcon className="h-5 w-5" aria-hidden="true" />
          </button>
          
          {/* Resize handle */}
          <div
            ref={resizeHandleRef}
            className="absolute top-0 left-0 w-1 h-full cursor-ew-resize hover:bg-blue-400/30 z-10 group"
            onMouseDown={handleResizeStart}
            aria-hidden="true"
            title="Drag to resize panel"
          >
            <div className="absolute inset-0 group-hover:bg-blue-400/30"></div>
            
            {/* Chevron icon anchored just inside drawer */}
            {isOpen && (
              <div className="absolute left-full top-1/2 -translate-y-1/2 translate-x-2 z-20 pointer-events-none">
                <ChevronUpDownIcon
                  className="h-8 w-8 text-gray-300 group-hover:text-lime-500 dark:text-gray-700 dark:group-hover:text-lime-400 rotate-90"
                  aria-hidden="true"
                />
              </div>
            )}
          </div>
          
          {/* Content */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-4 pt-6">
              {children}
            </div>
          </div>

          {/* Accessibility note for screen readers */}
          <div className="sr-only">
            Use the resize handle on the left edge to adjust panel width. Press Escape to close the panel.
          </div>
        </div>
      </Transition>
    </div>
  );
}

SideDrawer.propTypes = {
  children: PropTypes.node.isRequired,
  defaultWidth: PropTypes.number,
  minWidth: PropTypes.number,
  maxWidth: PropTypes.number,
  title: PropTypes.string,
  isOpen: PropTypes.bool,
  onOpenChange: PropTypes.func,
};
