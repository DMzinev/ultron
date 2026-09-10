// Utility TypeScript module with interfaces, optional properties, and ternary expressions
export interface FormattingOptions {
  prefix?: string;
  decimals?: number;
  verbose?: boolean;
}

export function formatResult(value: number, options?: FormattingOptions): string {
  const prefix = options?.prefix ? options.prefix : "Result:";
  const decimals = options?.decimals !== undefined ? options.decimals : 2;
  const formatted = value.toFixed(decimals);
  return `${prefix} ${formatted}`;
}

export function isPositive(value: number): boolean {
  return value > 0 ? true : false;
}
