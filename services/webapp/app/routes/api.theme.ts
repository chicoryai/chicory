import { json, type ActionFunctionArgs } from "@remix-run/node";
import { setTheme } from "~/utils/theme.server";

export async function action({ request }: ActionFunctionArgs) {
  const formData = await request.formData();
  const theme = formData.get("theme");
  
  if (theme !== "light" && theme !== "dark") {
    return json({ success: false, message: "Invalid theme" }, { status: 400 });
  }
  
  const themeValue = theme as "light" | "dark";
  const cookieValue = await setTheme(themeValue);
  
  return json(
    { success: true },
    { headers: { "Set-Cookie": cookieValue } }
  );
}
