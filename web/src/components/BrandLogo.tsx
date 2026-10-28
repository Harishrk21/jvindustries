type Props = {
  /** header | hero | mark */
  variant?: "header" | "hero" | "mark";
  className?: string;
};

export function BrandLogo({ variant = "header", className = "" }: Props) {
  return (
    <img
      src="/brand/jv-logo.png"
      alt="JV Industries"
      className={`brand-logo brand-logo-${variant} ${className}`.trim()}
      decoding="async"
    />
  );
}
