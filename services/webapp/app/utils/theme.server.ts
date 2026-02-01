import { createCookie } from "@remix-run/node";

// Define theme types
export type Theme = "light" | "dark";

// Create a cookie for storing theme preference
export const themeCookie = createCookie("theme", {
  path: "/",
  httpOnly: true,
  sameSite: "lax",
  secure: process.env.NODE_ENV === "production",
  // Cookie will expire after 1 year
  maxAge: 60 * 60 * 24 * 365,
});

// Get the theme from the request
export async function getTheme(request: Request): Promise<Theme | null> {
  const cookieHeader = request.headers.get("Cookie");
  const theme = await themeCookie.parse(cookieHeader);
  if (theme === "light" || theme === "dark") {
    return theme;
  }
  return null;
}

// Set the theme in the response headers
export async function setTheme(theme: Theme) {
  return await themeCookie.serialize(theme);
}
