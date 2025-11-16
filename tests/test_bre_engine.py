import json
import pytest

from bre_engine import BREEngine


# -------------------------------------------------------------------
# Dummy SQLAlchemy-like CreditPolicy class for testing purposes
# -------------------------------------------------------------------
class CreditPolicy:
    def __init__(self, name, policyJSON):
        self.name = name
        self.policyJSON = policyJSON
        self.policyJSON_d3 = None
        self.status = "DRAFT"
        self.version = 1


# -------------------------------------------------------------------
# Load the BRE policy JSON (your sample)
# -------------------------------------------------------------------
@pytest.fixture
def sample_policy_json():
    with open("tests/sample1.json") as f:
        return f.read()


@pytest.fixture
def sample_policy(sample_policy_json):
    return CreditPolicy(name="Loan Policy Test", policyJSON=sample_policy_json)


# -------------------------------------------------------------------
# Sample Applicant Data
# -------------------------------------------------------------------
@pytest.fixture
def applicant_data():
    return {
        "applicant": {
            "age": 28,
            "nationality": "INDIAN",
            "employment_type": "SALARIED",
            "monthly_income": 55000,
            "employment_tenure_months": 18,
            "business_vintage_years": None,
            "annual_income": None,
            "credit_score": 745,
            "fraud_flag": False
        }
    }


# -------------------------------------------------------------------
# Test Case
# -------------------------------------------------------------------
def test_bre_engine_execution(sample_policy, applicant_data):
    """
    Tests BREEngine with sample applicant and policy.
    Ensures final decision is ELIGIBLE.
    """

    engine = BREEngine(sample_policy, applicant_data)
    result = engine.run()

    print("\n".join(result["execution_log"]))

    assert result["final_decision"] == "ELIGIBLE"
    assert result["reason"] is None
    assert "Age Check" in "\n".join(result["execution_log"])
    assert "Credit Score Check" in "\n".join(result["execution_log"])

@pytest.fixture
def applicant_low_income():
    """Salaried applicant but income below the required 30K — should fail."""
    return {
        "applicant": {
            "age": 30,
            "nationality": "INDIAN",
            "employment_type": "SALARIED",
            "monthly_income": 20000,            # < 30K -> should fail
            "employment_tenure_months": 12,
            "business_vintage_years": None,
            "annual_income": None,
            "credit_score": 760,
            "fraud_flag": False
        }
    }


def test_bre_engine_rejects_low_income(sample_policy, applicant_low_income):
    """
    Ensure BREEngine rejects a salaried applicant whose monthly income < 30K.
    """
    engine = BREEngine(sample_policy, applicant_low_income)
    result = engine.run()

    # debug printing (pytest captures by default; run with -s to see)
    print("\n".join(result["execution_log"]))

    assert result["final_decision"] == "REJECTED"
    # The engine returns the failing reason in result["reason"]
    assert result["reason"] == "Income < 30K"

    log_output = "\n".join(result["execution_log"])
    assert "Income Check" in log_output
    assert "Income < 30K" in log_output