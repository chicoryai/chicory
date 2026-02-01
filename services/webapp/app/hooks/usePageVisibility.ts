import React, { useEffect, useState } from "react";
import { useRevalidator } from "@remix-run/react";

/**
 * Hook to revalidate data when the page becomes visible after being idle
 *
 * This helps recover from idle-state errors by automatically refreshing data
 * when the user returns to the tab after being away.
 *
 * @param options Configuration options
 * @param options.revalidateOnVisible Whether to revalidate when page becomes visible (default: true)
 * @param options.minIdleTime Minimum time in ms before revalidating (default: 60000 = 1 minute)
 */
export function usePageVisibility(options?: {
  revalidateOnVisible?: boolean;
  minIdleTime?: number;
}) {
  const { revalidateOnVisible = true, minIdleTime = 60000 } = options || {};
  const revalidator = useRevalidator();

  useEffect(() => {
    if (!revalidateOnVisible) return;

    let hiddenTime: number | null = null;

    const handleVisibilityChange = () => {
      if (document.hidden) {
        // Page became hidden - record the time
        hiddenTime = Date.now();
      } else {
        // Page became visible - check if we should revalidate
        if (hiddenTime !== null) {
          const idleTime = Date.now() - hiddenTime;

          // Only revalidate if the page was hidden for longer than minIdleTime
          if (idleTime >= minIdleTime) {
            console.log(`[usePageVisibility] Revalidating after ${Math.round(idleTime / 1000)}s idle time`);
            revalidator.revalidate();
          }

          hiddenTime = null;
        }
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [revalidateOnVisible, minIdleTime, revalidator]);
}

/**
 * Hook to detect when the page becomes visible
 *
 * @returns Boolean indicating if the page is currently visible
 */
export function useIsPageVisible(): boolean {
  const [isVisible, setIsVisible] = useState(() => {
    if (typeof document === "undefined") return true;
    return !document.hidden;
  });

  useEffect(() => {
    const handleVisibilityChange = () => {
      setIsVisible(!document.hidden);
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  return isVisible;
}
