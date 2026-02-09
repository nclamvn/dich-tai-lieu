import { cn } from "@/lib/utils";

export function Card({
  className,
  children,
  hover = false,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { hover?: boolean }) {
  return (
    <div
      className={cn(
        hover && "cursor-pointer",
        className,
      )}
      style={{
        background: "var(--bg-primary)",
        borderRadius: "var(--radius-lg)",
        border: "1px solid var(--border-default)",
      }}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("px-5 py-3.5", className)}
      style={{ borderBottom: "1px solid var(--border-default)" }}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardContent({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("px-5 py-4", className)} {...props}>
      {children}
    </div>
  );
}
