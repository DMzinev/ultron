"""
Mixed repository fixture - Genuinely risky core module.
High cyclomatic complexity, deeply nested logic, state mutation.
"""
from .models import ItemModel
from .exceptions import ValidationError, ProcessingError


class RiskyCoreEngine:
    def __init__(self):
        self.state = {}
        self.errors = []

    def evaluate_transaction(self, tx_id, records, flags, options):
        if not tx_id:
            raise ValidationError("Transaction ID required")
        if not records:
            return None

        accum = 0
        for rec in records:
            if rec.get("status") == "active":
                val = rec.get("amount", 0)
                if val > 1000:
                    if flags.get("strict"):
                        if val > 5000:
                            raise ProcessingError("Limit exceeded")
                        accum += val * 2
                    else:
                        accum += val
                elif val > 100:
                    for tag in rec.get("tags", []):
                        if tag == "priority":
                            accum += val * 3
                        elif tag == "promo":
                            accum += val // 2
                        elif tag == "taxable":
                            accum += int(val * 1.15)
                        else:
                            accum += val
                else:
                    if val < 0:
                        self.errors.append(f"Negative: {val}")
                    else:
                        accum += val
            elif rec.get("status") == "pending":
                if options.get("allow_pending"):
                    accum += rec.get("amount", 0) // 2
            else:
                self.errors.append("Invalid record status")

        return accum

    def process_batch(self, batch_list):
        out = []
        for b in batch_list:
            try:
                res = self.evaluate_transaction(
                    b.get("id"), b.get("items", []), b.get("flags", {}), b.get("opts", {})
                )
                out.append(res)
            except (ValidationError, ProcessingError) as err:
                self.errors.append(str(err))
                out.append(None)
        return out
