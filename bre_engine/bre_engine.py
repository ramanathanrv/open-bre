import json
import operator


class BREEngine:
    """
    Executes a JSON-based Credit Policy (BRE) against an applicant.
    First parameter: CreditPolicy SQLAlchemy model instance
    Second parameter: applicant data dictionary
    """

    OPERATORS = {
        "==": operator.eq,
        "!=": operator.ne,
        ">": operator.gt,
        ">=": operator.ge,
        "<": operator.lt,
        "<=": operator.le,
        "in": lambda a, b: a in b,
        "not in": lambda a, b: a not in b,
    }

    def __init__(self, credit_policy, applicant_data):
        """
        credit_policy: SQLAlchemy CreditPolicy model
        applicant_data: Python dict
        """
        self.policy = json.loads(credit_policy.policyJSON)
        self.applicant_data = applicant_data
        self.execution_log = []

    # ----------------------------------------------------------------------
    # Utility Methods
    # ----------------------------------------------------------------------

    def get_value(self, field_path):
        """Extract nested values (e.g. applicant.age)"""
        parts = field_path.split(".")
        value = self.applicant_data
        for p in parts:
            if value is None or p not in value:
                return None
            value = value[p]
        return value

    def evaluate_conditions(self, conditions):
        """Evaluate all conditions of a rule."""
        for cond in conditions:
            left = self.get_value(cond["field"])
            op = self.OPERATORS[cond["operator"]]
            right = cond["value"]
            if not op(left, right):
                return False
        return True

    def find_rule(self, rule_id):
        """Find rule anywhere in the policy."""
        for chain in self.policy["chains"]:
            for ruleset in chain["rulesets"]:
                for rule in ruleset["rules"]:
                    if rule["id"] == rule_id:
                        return rule
        return None

    # ----------------------------------------------------------------------
    # Rule Evaluation Logic
    # ----------------------------------------------------------------------

    def execute_rule(self, rule):
        """Execute a single rule and return next rules if applicable."""
        self.execution_log.append(f"Evaluating rule: {rule['id']} — {rule.get('name', '')}")

        passed = self.evaluate_conditions(rule.get("conditions", []))
        action = rule["action"]["on_true"] if passed else rule["action"]["on_false"]

        if not passed:
            reason = action.get("reason", "Failed condition")
            self.execution_log.append(f"❌ FAIL: {reason}")
            return {"status": "FAIL", "reason": reason, "next_rules": []}

        self.execution_log.append("✅ PASS")

        # Handle branching
        if passed and action.get("branches"):
            for br in action["branches"]:
                if self.evaluate_conditions(br.get("conditions", [])):
                    self.execution_log.append(f"➡ Branch taken: {br['name']}")
                    return {"status": "PASS", "next_rules": br.get("next_rules", [])}

        # Normal transitions
        return {"status": "PASS", "next_rules": action.get("next_rules", [])}

    # ----------------------------------------------------------------------
    # Chain Execution
    # ----------------------------------------------------------------------

    def execute_chain(self, chain):
        """Execute a chain by BFS traversal starting from first rule."""
        rulesets = chain["rulesets"]
        first_rule = rulesets[0]["rules"][0]
        queue = [first_rule["id"]]
        visited = set()

        while queue:
            rule_id = queue.pop(0)
            if rule_id in visited:
                continue
            visited.add(rule_id)

            rule = self.find_rule(rule_id)
            if not rule:
                self.execution_log.append(f"⚠ Missing rule: {rule_id}")
                continue

            result = self.execute_rule(rule)

            if result["status"] == "FAIL":
                return result

            for nxt in result["next_rules"]:
                queue.append(nxt)

        return {"status": "PASS"}

    # ----------------------------------------------------------------------
    # Public Method: Execute Entire Policy
    # ----------------------------------------------------------------------

    def run(self):
        """Execute all BRE chains and return final decision."""
        self.execution_log.append("========== EXECUTING LOAN BRE ==========")

        for chain in self.policy["chains"]:
            self.execution_log.append(f"\n=== Executing chain: {chain['name']} ===")
            result = self.execute_chain(chain)

            if result["status"] == "FAIL":
                self.execution_log.append("\nFINAL DECISION: ❌ REJECTED")
                return {
                    "final_decision": "REJECTED",
                    "reason": result.get("reason"),
                    "execution_log": self.execution_log
                }

        # All chains passed → return terminal node decision
        terminal = self.policy["terminal_nodes"][0]
        final_decision = terminal.get("decision", "ELIGIBLE")

        self.execution_log.append(f"\nFINAL DECISION: ✅ {final_decision}")

        return {
            "final_decision": final_decision,
            "reason": None,
            "execution_log": self.execution_log
        }
