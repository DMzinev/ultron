// Root entrypoint with imports and re-exports
import { Calculator } from "./calculator.js";
import { logMessage } from "./legacy_logger.cjs";

export * from "./math.js";
export { Calculator, logMessage };

export function initializeApp() {
  const calc = new Calculator(10);
  calc.execute("add", 5);
  return calc;
}
