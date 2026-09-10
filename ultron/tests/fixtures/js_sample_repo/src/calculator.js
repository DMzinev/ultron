// Calculator module orchestrating math and utils
import { add, subtract, divide, clamp } from "./math.js";
import { formatResult, isPositive } from "./utils.ts";

export class Calculator {
  constructor(initialValue = 0) {
    this.value = initialValue;
    this.history = [];
  }

  execute(operation, operand) {
    switch (operation) {
      case "add":
        this.value = add(this.value, operand);
        break;
      case "subtract":
        this.value = subtract(this.value, operand);
        break;
      case "divide":
        try {
          this.value = divide(this.value, operand);
        } catch (err) {
          this.value = 0;
        }
        break;
      default:
        this.value = operand;
    }
    this.history.push({ op: operation, val: operand, res: this.value });
    return this.value;
  }

  batchProcess(operations) {
    let i = 0;
    while (i < operations.length) {
      const item = operations[i];
      if (item) {
        this.execute(item.op, item.val);
      }
      i++;
    }
    return formatResult(this.value);
  }
}
