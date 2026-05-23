import { cn } from "@/lib/utils";

export function Card({
  className,
  children,
  title,
}: {
  className?: string;
  children: React.ReactNode;
  title?: string;
}) {
  return (
    <div className={cn("panel p-5", className)}>
      {title && <h2 className="section-label mb-3">{title}</h2>}
      {children}
    </div>
  );
}

export function Button({
  className,
  variant = "primary",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger";
}) {
  const variants = {
    primary: "btn-cyan",
    secondary:
      "inline-flex items-center justify-center rounded border border-harness-border bg-harness-card px-4 py-2 text-sm font-medium text-slate-300 hover:bg-white/5",
    danger:
      "inline-flex items-center justify-center rounded bg-red-600/90 px-4 py-2 text-sm font-medium text-white hover:bg-red-600",
  };
  return <button className={cn(variants[variant], className)} {...props} />;
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className="w-full rounded border border-harness-border bg-harness-bg px-4 py-3 font-mono text-sm text-slate-100 placeholder:text-slate-600 focus:border-harness-cyan focus:outline-none focus:ring-1 focus:ring-harness-cyan/30"
      {...props}
    />
  );
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className="w-full rounded border border-harness-border bg-harness-bg px-4 py-2.5 text-sm text-slate-100 focus:border-harness-cyan focus:outline-none focus:ring-1 focus:ring-harness-cyan/30"
      {...props}
    />
  );
}
