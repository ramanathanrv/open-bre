import os
from flask import render_template, request, redirect, url_for, flash, current_app, jsonify
from app import app, db                 # Import existing app and db
from forms import CreditPolicyForm
from models.credit_policy import CreditPolicy
import google.generativeai as genai
import json
import logging, sys
from bre_engine import BREEngine
from werkzeug.exceptions import BadRequest, NotFound
from models.events import convert_to_d3js_format, convert_to_d3js_from_json

# Configure logging once (Flask will inherit this)
logger = logging.getLogger("nbre")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

@app.route('/creditpolicy')
def list_policies():
    policies = CreditPolicy.query.all()
    return render_template('policy/list.html', policies=policies)

def load_policy_from_db(policy_id):
    """
    Try to load CreditPolicy from DB (SQLAlchemy). Returns None if not found or model missing.
    """
    if CreditPolicy is None:
        return None
    try:
        # Using Flask-SQLAlchemy model query interface
        policy = CreditPolicy.query.get(policy_id)
        return policy
    except Exception:
        # DB not configured or query failed
        return None


@app.route("/run_policy", methods=["POST"])
def run_policy_route():
    """
    POST /run_policy
    Body:
    {
        "policy_id": 1,
        "applicant": { ... }               # applicant dict (same shape used by BRE)
    }
    Response: application/json
    {
      "policy_id": 1,
      "final_decision": "ELIGIBLE" | "REJECTED",
      "reason": null | "some reason",
      "execution_log": [ "...", "..."],
      "status": "ok"
    }
    """
    # parse JSON body
    try:
        payload = request.get_json(force=True)
    except BadRequest:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    envelope = payload

    policy_id = envelope.get("policy_id")
    applicant = envelope.get("applicant")

    if policy_id is None or applicant is None:
        return jsonify({"status": "error", "message": "envelope must contain policy_id and applicant"}), 400

    # Load policy from DB, fallback to sample file
    policy_obj = load_policy_from_db(policy_id)
    if policy_obj is None:
        # fallback: sample1.json in project root
        policy_obj = load_sample_policy_from_file("sample1.json")
        if policy_obj is None:
            return jsonify({"status": "error", "message": "Policy not found and sample1.json missing"}), 404

    # instantiate engine and run
    try:
        engine = BREEngine(policy_obj, applicant)
        result = engine.run()
    except Exception as exc:
        current_app.logger.exception("BRE execution error")
        return jsonify({"status": "error", "message": "BRE execution failed", "detail": str(exc)}), 500

    # Compose response
    response = {
        "policy_id": policy_id,
        "final_decision": result.get("final_decision"),
        "reason": result.get("reason"),
        "execution_log": result.get("execution_log", []),
        "status": "ok"
    }
    return jsonify(response), 200

@app.route('/creditpolicy/create', methods=['GET', 'POST'])
def create_policy():
    form = CreditPolicyForm()
    # validate_on_submit() is True only on a successful POST submission
    if form.validate_on_submit():
        policy_json_str = request.form.get('policyJSON')
        try:
            # Validate and normalize JSON for storage
            policy_json = json.dumps(json.loads(policy_json_str))
        except (json.JSONDecodeError, TypeError):
            flash("Invalid JSON format.", "danger")
            # Re-render form with user's invalid data
            d3_data = {}
            try:
                d3_data = convert_to_d3js_from_json(policy_json_str)
            except Exception:
                d3_data = convert_to_d3js_from_json('{}')
            return render_template('policy/form.html', form=form, action='Create', policyJSON=policy_json_str, policyJSON_d3=d3_data)

        cp = CreditPolicy(
            name=form.name.data,
            version=form.version.data,
            status=form.status.data,
            policyJSON=policy_json
        )
        db.session.add(cp)
        db.session.commit()
        flash("Credit Policy created successfully!", "success")
        return redirect(url_for('list_policies'))

    # This block handles GET requests and POSTs that fail validation (including pre-fill from copilot).
    policy_json_str = '{}'
    if request.method == 'POST':
        policy_json_str = request.form.get('policyJSON', '{}')

    pretty_json, d3_data = policy_json_str, {}
    try:
        parsed = json.loads(policy_json_str)
        pretty_json = json.dumps(parsed, indent=2)
        d3_data = convert_to_d3js_from_json(json.dumps(parsed))
    except (json.JSONDecodeError, TypeError):
        if request.method == 'POST' and policy_json_str.strip() not in ['{}', '']:
            flash("Could not parse policy JSON to render graph.", "warning")
        d3_data = convert_to_d3js_from_json('{}')

    return render_template('policy/form.html', form=form, action='Create', policyJSON=pretty_json, policyJSON_d3=d3_data)

@app.route('/creditpolicy/copilot/<int:id>', methods=['GET'])
def edit_policy(id):
    cp = CreditPolicy.query.get_or_404(id)
    pretty_policy = json.dumps(json.loads(cp.policyJSON or '{}'), indent=2)
    return render_template('policy/copilot.html', policy=cp, policyJson=pretty_policy)


@app.route('/creditpolicy/edit/<int:id>', methods=['GET', 'POST'])
def copilot_edit_policy(id):
    cp = CreditPolicy.query.get_or_404(id)
    form = CreditPolicyForm(obj=cp)
    if request.method == 'POST' and form.validate():
        policy_json = request.form.get('policyJSON')
        try:
            policy_json = json.dumps(json.loads(policy_json))
        except:
            flash("Invalid JSON", "danger")
            return render_template('policy/form.html', form=form, action='Edit', policyJSON=policy_json)

        cp.name = form.name.data
        cp.version = form.version.data
        cp.status = form.status.data
        cp.policyJSON = policy_json
        db.session.commit()
        flash("Credit Policy updated successfully!", "success")
        return redirect(url_for('list_policies'))

    pretty_json = json.dumps(json.loads(cp.policyJSON or '{}'), indent=2)
    return render_template('policy/form.html', form=form, action='Save', policyJSON=pretty_json, policyJSON_d3=cp.policyJSON_d3)

@app.route('/creditpolicy/delete/<int:id>', methods=['POST'])
def delete_policy(id):
    cp = CreditPolicy.query.get_or_404(id)
    db.session.delete(cp)
    db.session.commit()
    flash("Credit Policy deleted successfully!", "success")
    return redirect(url_for('list_policies'))

from flask import Blueprint, request, jsonify

# assuming you have 'app' initialized already
# if you're using blueprints:
# copilot_bp = Blueprint("copilot", __name__)


@app.route("/api/copilot", methods=["POST"])
def api_copilot():
    data = request.get_json(force=True)
    user_message = data.get("message", "")
    policy = data.get("policy", {})

    model_name = "gemini-2.5-flash"   # update to a supported model
    model = genai.GenerativeModel(model_name)

    prompt = f"""
You are an AI copilot for editing credit policies.
The policy is represented as JSON below:
{json.dumps(policy, indent=2)}

User instruction:
"{user_message}"

Task:
- Provide a JSON-formatted response:
  {{
    "reply": "...",
    "updated_policy": {{...}},
    "diff": [
       {{"path": "...","old": ..., "new": ...}}
    ],
    "diff_summary": "..."
  }}
"""

    # --- Log the request ---
    logger.info({
        "event": "LLM_REQUEST",
        "model": model_name,
        "user_message": user_message,
        "policy_summary": {k: list(v.keys()) if isinstance(v, dict) else v for k, v in policy.items()}
    })

    try:
        response = model.generate_content(
            [prompt],
            generation_config=genai.GenerationConfig(response_mime_type="application/json")
        )
        text = response.text.strip()
        logger.info({"event": "LLM_RESPONSE_RAW", "text": text[:500]})  # truncate long content

        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Model response not valid JSON; returning fallback.")
            result = {
                "reply": text,
                "updated_policy": policy,
                "diff": [],
                "diff_summary": "Unstructured response from model."
            }

        # --- Log structured response ---
        logger.info({
            "event": "LLM_RESPONSE_PARSED",
            "reply_summary": result.get("reply", "")[:120],
            "diff_count": len(result.get("diff", []))
        })


        return jsonify(result)
    except Exception as e:
        return jsonify({
            "error": str(e),
            "reply": "Error processing request.",
            "diff": [],
            "diff_summary": "Error"
        }), 500

@app.route("/api/toD3", methods=["POST"])
def api_to_d3_format():
    try:
        req = request.get_json(force=True)
        policy = req.get("policy", {})
        # Assuming convert_to_d3js_format expects a dict or JSON object
        d3_format = convert_to_d3js_from_json(json.dumps(policy))
        return d3_format, 200
    except Exception as e:
        app.logger.exception("Error converting policy to D3 format")
        return jsonify({"error": str(e)}), 500
