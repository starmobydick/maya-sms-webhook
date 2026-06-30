"""
Maya SMS demo webhook.

Receives inbound SMS from Twilio at /sms and runs a controlled
5-question demo flow. Does NOT write to any real customer CRM.

DEPLOY (Replit):
  1. Create a new Python Repl.
  2. Save this file as main.py.
  3. Create a file called requirements.txt with:
        flask
        twilio
  4. Run. Replit gives you a public URL like:
        https://maya-sms-demo.<your-name>.repl.co
  5. In Twilio Console -> Phone Numbers -> Manage -> Active Numbers
     -> click (507) 677-3559 -> "Messaging" section -> set:
        "A MESSAGE COMES IN" -> Webhook -> https://<your-url>/sms
     -> Method: HTTP POST -> Save.

That's it. Anyone who texts (507) 677-3559 now hits this webhook
and gets the demo flow. No real customer data touched.
"""

import os
from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

CALENDLY = "https://calendly.com/duy-agentsvietnam/30min"

# In-memory per-sender state. Key = sender phone (E.164).
# For production with high volume, replace with Redis or a database
# so state survives server restarts and scales across instances.
demo_state = {}


def demo_reply(state, body):
    """Advance the 5-step demo conversation and return the reply text."""
    step = state["step"]

    # Step 0 - waiting for the keyword QUOTE
    if step == 0:
        if "quote" in body.lower():
            state["step"] = 1
            return (
                "Hey! Thanks for reaching out. Quick Q so I can get you booked "
                "- is this for your home or a commercial property?"
            )
        return (
            "Hi! I'm Maya, an AI SMS booking agent for HVAC shops. "
            "Text the word QUOTE to see how I qualify a lead and book "
            "an appointment in under 60 seconds."
        )

    # Step 1 - asked service type, now ask the problem
    if step == 1:
        state["service_type"] = body
        state["step"] = 2
        return "Got it. What's going on with your system? (e.g. AC not cooling, no heat, install quote)"

    # Step 2 - asked problem, now ask ZIP
    if step == 2:
        state["problem"] = body
        state["step"] = 3
        return "Sorry to hear that. What's your ZIP code? I'll confirm we cover your area."

    # Step 3 - asked ZIP, now offer slots
    if step == 3:
        state["zip"] = body
        state["step"] = 4
        return (
            "Perfect - we cover that area. We can have a tech out tomorrow "
            "10-12 or 2-4. Which works?"
        )

    # Step 4 - asked for slot, now confirm + pitch
    if step == 4:
        state["slot"] = body
        state["step"] = 5
        return (
            "Booked! In production, you'd get a confirmation text and the "
            "appointment would land on the dispatcher's calendar with full "
            "context (service type, problem description, full SMS thread).\n\n"
            "That was Maya - the AI SMS booking agent for HVAC shops.\n\n"
            "To deploy her on your shop with your real calendar, service area, "
            f"and pricing, book a 30-min setup call:\n{CALENDLY}"
        )

    # Step 5+ - demo complete, allow restart
    state["step"] = 0
    state.pop("service_type", None)
    state.pop("problem", None)
    state.pop("zip", None)
    state.pop("slot", None)
    return (
        f"Want to see the flow again? Text QUOTE to restart.\n"
        f"Ready to deploy on your shop? {CALENDLY}"
    )


@app.route("/sms", methods=["POST"])
def sms_webhook():
    from_number = request.form.get("From", "")
    body = request.form.get("Body", "").strip()

    # Initialize state for new senders
    if from_number not in demo_state:
        demo_state[from_number] = {"step": 0}

    reply_text = demo_reply(demo_state[from_number], body)

    resp = MessagingResponse()
    resp.message(reply_text)
    return Response(str(resp), mimetype="application/xml")


@app.route("/")
def home():
    return (
        "<h2>Maya SMS demo webhook is running.</h2>"
        "<p>Twilio should POST to <code>/sms</code>.</p>"
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
