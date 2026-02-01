import { useState, useEffect, useRef } from "react";
import { useClientOnly } from "./useClientOnly";

const SIDEBAR_STORAGE_KEY = "sidebar:isOpen";

interface UseSidebarOptions {
  /**
   * Default state of the sidebar (open or closed)
   */
  defaultOpen?: boolean;
  /**
   * Width breakpoint to automatically close the sidebar (in pixels)
   */
  closeBreakpoint?: number;
  /**
   * Width breakpoint to automatically open the sidebar (in pixels)
   */
  openBreakpoint?: number;
}

/**
 * A hook that manages sidebar state with responsive behavior.
 * Safely handles SSR by only applying responsive logic on the client.
 */
export function useSidebar({
  defaultOpen = true,
  closeBreakpoint = 768,
  openBreakpoint = 1024
}: UseSidebarOptions = {}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [, isMounted] = useClientOnly(false);
  const persistedPreferenceRef = useRef(defaultOpen);

  useEffect(() => {
    if (!isMounted) return;

    try {
      const stored = window.localStorage.getItem(SIDEBAR_STORAGE_KEY);
      if (stored !== null) {
        const preference = stored === "true";
        persistedPreferenceRef.current = preference;
        setIsOpen(preference);
        return;
      }
    } catch (error) {
      console.warn("Failed to read sidebar preference from storage", error);
    }

    persistedPreferenceRef.current = defaultOpen;
    setIsOpen(defaultOpen);
  }, [defaultOpen, isMounted]);
  
  // Only run this effect on the client
  useEffect(() => {
    if (!isMounted) return;
    
    const handleResize = () => {
      if (window.innerWidth < closeBreakpoint) {
        setIsOpen(false);
      } else if (window.innerWidth >= openBreakpoint) {
        setIsOpen(persistedPreferenceRef.current);
      }
    };
    
    window.addEventListener('resize', handleResize);
    handleResize(); // Set initial state
    
    return () => window.removeEventListener('resize', handleResize);
  }, [isMounted, closeBreakpoint, openBreakpoint]);
 
  const persistPreference = (nextState: boolean) => {
    persistedPreferenceRef.current = nextState;
    if (!isMounted) {
      return;
    }
    try {
      window.localStorage.setItem(SIDEBAR_STORAGE_KEY, String(nextState));
    } catch (error) {
      console.warn("Failed to persist sidebar preference", error);
    }
  };

  const setOpenState = (nextState: boolean, persist = false) => {
    setIsOpen(nextState);
    if (persist) {
      persistPreference(nextState);
    }
  };

  const toggleSidebar = () => setOpenState(!isOpen, true);
  const openSidebar = () => setOpenState(true, true);
  const closeSidebar = () => setOpenState(false, true);
  
  return { 
    isOpen, 
    toggleSidebar,
    openSidebar,
    closeSidebar
  };
}
