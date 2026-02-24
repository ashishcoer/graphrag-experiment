import os, json, time, yaml
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential

with open("config.yaml") as f:
    config = yaml.safe_load(f)

COST_LOG = Path(config.get("cost_tracking", {}).get("log_file", "results/api_costs.jsonl"))
COST_LOG.parent.mkdir(parents=True, exist_ok=True)

PRICING = {
    "gpt-4o-2024-05-13":        {"input": 2.50, "output": 10.00},
    "gpt-4o-mini-2024-07-18":   {"input": 0.15, "output": 0.60},
}

from openai import OpenAI
client = OpenAI()
MODEL = config["models"]["openai"]["generation_model"]
MINI_MODEL = config["models"]["openai"]["mini_model"]
TEMPERATURE = config["models"]["openai"]["temperature"]
MAX_TOKENS = config["models"]["openai"]["max_tokens"]

def log_cost(model, input_tokens, output_tokens, purpose=""):
    pricing = PRICING.get(model, {"input": 5.0, "output": 15.0})
    cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
    entry = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "model": model,
             "input_tokens": input_tokens, "output_tokens": output_tokens,
             "cost_usd": round(cost, 6), "purpose": purpose}
    with open(COST_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return cost

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=60))
def generate(prompt, system_prompt=None, model=None, purpose="generation"):
    model = model or MODEL
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(
        model=model, messages=messages, temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS, top_p=config["models"]["openai"].get("top_p", 0.95))
    text = response.choices[0].message.content
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    cost = log_cost(model, input_tokens, output_tokens, purpose)
    return {"text": text, "input_tokens": input_tokens,
            "output_tokens": output_tokens, "cost_usd": cost}

def generate_mini(prompt, system_prompt=None, purpose="evaluation"):
    return generate(prompt, system_prompt, model=MINI_MODEL, purpose=purpose)

def get_total_cost():
    total = 0.0
    if COST_LOG.exists():
        with open(COST_LOG) as f:
            for line in f:
                total += json.loads(line).get("cost_usd", 0)
    return total

def print_cost_summary():
    costs = {}
    if COST_LOG.exists():
        with open(COST_LOG) as f:
            for line in f:
                entry = json.loads(line)
                p = entry.get("purpose", "unknown")
                costs.setdefault(p, {"calls": 0, "cost": 0.0})
                costs[p]["calls"] += 1
                costs[p]["cost"] += entry.get("cost_usd", 0)
    print("\n--- API Cost Summary ---")
    total = 0
    for purpose, data in sorted(costs.items()):
        print(f"  {purpose:30s} {data['calls']:>6d} calls  ${data['cost']:.4f}")
        total += data["cost"]
    print(f"  {'TOTAL':30s} {'':>6s}       ${total:.4f}")