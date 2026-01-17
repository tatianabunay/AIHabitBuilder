import json
import uuid
from datetime import datetime
import boto3

# DynamoDB setup
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("HabitPlans")

# Bedrock setup
bedrock = boto3.client("bedrock-runtime")

MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"  # Use a supported model

def generate_habit_plan(goal):
    system_prompt = (
        "You are an expert habit-building coach. "
        "Break goals into small, realistic action steps. "
        "Identify common obstacles and provide practical solutions. "
        "Return ONLY valid JSON. Do not include any extra text."
    )

    user_prompt = f"""
User habit goal: {goal}

Return JSON with:
- goal
- action_steps (array with step number, action, reason)
- obstacles (array with issue and solution)
"""

    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 600,
            "temperature": 0.5,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        })
    )

    raw_body = response["body"].read()
    model_output = json.loads(raw_body)

    ai_text = model_output["content"][0]["text"]

    return json.loads(ai_text)


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        goal = body.get("goal")

        if not goal:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Goal is required"})
            }

        # Generate AI habit plan
        plan = generate_habit_plan(goal)

        # Store in DynamoDB
        plan_id = str(uuid.uuid4())

        table.put_item(
            Item={
                "plan_id": plan_id,
                "goal": goal,
                "created_at": datetime.utcnow().isoformat(),
                "plan": plan
            }
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "plan_id": plan_id,
                "plan": plan
            })
        }

    except Exception as e:
        print("Error:", e)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"})
        }
