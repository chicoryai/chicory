import type { ImgHTMLAttributes } from "react";

interface MCPGatewayIconProps extends ImgHTMLAttributes<HTMLImageElement> {
  size?: number;
}

export default function MCPGatewayIcon({
  className = "",
  size = 24,
  alt = "MCP Gateway",
  ...props
}: MCPGatewayIconProps) {
  const baseClass = "dark:invert";
  const combinedClass = [baseClass, className].filter(Boolean).join(" ");

  return (
    <img
      height={size}
      width={size}
      src="https://unpkg.com/@lobehub/icons-static-svg@latest/icons/mcp.svg"
      className={combinedClass || undefined}
      alt={alt}
      {...props}
    />
  );
}
