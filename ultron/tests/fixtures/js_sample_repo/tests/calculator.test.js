// Test file for Calculator class using directory-relative imports
import { Calculator } from "../src/calculator.js";

export function testCalculatorBasic() {
  const calc = new Calculator(0);
  const res = calc.execute("add", 10);
  if (res !== 10) {
    throw new Error(`Expected 10, got ${res}`);
  }
  return true;
}

export function testCalculatorDivideByZero() {
  const calc = new Calculator(10);
  const res = calc.execute("divide", 0);
  if (res !== 0) {
    throw new Error(`Expected 0 after catch, got ${res}`);
  }
  return true;
}
