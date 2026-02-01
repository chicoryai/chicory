import { createContext, useContext, useState, useEffect } from "react";
import { useFetcher } from "@remix-run/react";

export type Theme = "light" | "dark";

type ThemeContextType = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  isLoading: boolean;
};

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({
  children,
  specifiedTheme,
}: {
  children: React.ReactNode;
  specifiedTheme: Theme | null;
}) {
  const [theme, setTheme] = useState<Theme>(() => {
    // Initialize with the server-provided theme or system preference
    if (specifiedTheme) {
      return specifiedTheme;
    }
    
    // Check for system preference if no theme is specified
    if (typeof window !== "undefined") {
      const systemPreference = window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
      return systemPreference;
    }
    
    return "light"; // Default fallback
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const fetcher = useFetcher();

  // Apply theme class to document
  useEffect(() => {
    document.documentElement.classList.remove("light", "dark");
    document.documentElement.classList.add(theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  // Listen for system preference changes
  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = () => {
      // Only change if user hasn't explicitly set a preference
      const storedTheme = localStorage.getItem("theme");
      if (!storedTheme) {
        setTheme(mediaQuery.matches ? "dark" : "light");
      }
    };
    
    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  // Function to change theme and persist to cookie
  const changeTheme = (newTheme: Theme) => {
    setIsLoading(true);
    setTheme(newTheme);
    
    // Save to cookie via action
    fetcher.submit(
      { theme: newTheme },
      { method: "post", action: "/api/theme" }
    );
    
    setIsLoading(false);
  };

  const value = {
    theme,
    setTheme: changeTheme,
    isLoading,
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

// Custom hook to use the theme context
export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}
