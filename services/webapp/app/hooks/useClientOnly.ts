import { useState, useEffect } from "react";

/**
 * A hook that returns a boolean indicating whether the component is mounted
 * and a value that is only set on the client side.
 * 
 * @param initialValue The initial value to use during SSR
 * @returns A tuple containing the value and a boolean indicating if the component is mounted
 */
export function useClientOnly<T>(initialValue: T): [T, boolean] {
  const [value, setValue] = useState<T>(initialValue);
  const [isMounted, setIsMounted] = useState(false);
  
  useEffect(() => {
    setIsMounted(true);
  }, []);
  
  return [value, isMounted];
}
