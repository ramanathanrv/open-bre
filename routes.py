import os
from flask import render_template, request, redirect, url_for, flash
from app import app, db                 # Import existing app and db
from forms import CreditPolicyForm
from models.credit_policy import CreditPolicy
import google.generativeai as genai
import json
import logging, sys
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

@app.route('/creditpolicy/create', methods=['GET', 'POST'])
def create_policy():
    form = CreditPolicyForm()
    if request.method == 'POST' and form.validate():
        policy_json = request.form.get('policyJSON')
        try:
            policy_json = json.dumps(json.loads(policy_json))  # validate JSON
        except:
            flash("Invalid JSON", "danger")
            return render_template('policy/form.html', form=form, action='Create', policyJSON=policy_json)
        
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
    
    return render_template('form.html', form=form, action='Create', policyJSON='{}')

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
