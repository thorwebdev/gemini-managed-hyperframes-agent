import os
import sys
from google import genai

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        sys.exit(1)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Read AGENTS.md
    agents_file_path = os.path.join(script_dir, "AGENTS.md")
    if not os.path.exists(agents_file_path):
        print(f"Error: {agents_file_path} does not exist.")
        sys.exit(1)
        
    with open(agents_file_path, "r") as f:
        system_instructions = f.read()

    # 2. Read environment ID from hyperframes_env_id.txt
    env_file_path = os.path.join(script_dir, "hyperframes_env_id.txt")
    if not os.path.exists(env_file_path):
        print(f"Error: {env_file_path} does not exist. Run setup first.")
        sys.exit(1)

    with open(env_file_path, "r") as f:
        env_id = f.read().strip()

    print(f"Registering custom agent 'hyperframes-video-agent'...")

    client = genai.Client(api_key=api_key)

    # 3. Check if agent already exists and delete it first to allow update
    try:
        existing_agent = client.agents.get(id="hyperframes-video-agent")
        if existing_agent:
            print("Agent 'hyperframes-video-agent' already exists. Deleting to update...")
            client.agents.delete(id="hyperframes-video-agent")
    except Exception:
        # Does not exist, proceed
        pass

    # 4. Register the custom agent
    try:
        agent = client.agents.create(
            id="hyperframes-video-agent",
            base_agent="antigravity-preview-05-2026",
            system_instruction=system_instructions,
        )
        print(f"Successfully registered custom agent!")
        print(f"  Agent ID:               {agent.id}")
        print(f"  Base Agent:             {agent.base_agent}")
        print(f"  System Instruction size:{len(agent.system_instruction)} bytes")
    except Exception as e:
        print(f"Error registering custom agent: {e}")
        sys.exit(1)

    # 5. Execute a live validation run using the custom agent
    print(f"\nExecuting validation interaction using agent 'hyperframes-video-agent' inside environment: {env_id}...")
    prompt = "Run the diagnostic check command: `export HYPERFRAMES_BROWSER_PATH=/usr/bin/chrome-headless-shell && hyperframes doctor` and return the full output."

    try:
        stream = client.interactions.create(
            agent="hyperframes-video-agent",
            input=prompt,
            environment=env_id,
            stream=True
        )

        for event in stream:
            if event.event_type == "step.start":
                print(f"\n--- Step {event.index}: {event.step.type} ---")
            elif event.event_type == "step.delta":
                delta = event.delta
                if delta.type == "text":
                    print(delta.text, end="", flush=True)
                elif delta.type == "thought_summary":
                    content = delta.content
                    text = ""
                    if hasattr(content, 'text'):
                        text = content.text
                    elif isinstance(content, dict) and 'text' in content:
                        text = content['text']
                    elif isinstance(content, str):
                        text = content
                    print(text, end="", flush=True)
                elif delta.type == "code_execution_call":
                    code = ""
                    if hasattr(delta, 'arguments') and delta.arguments:
                        if hasattr(delta.arguments, 'code'):
                            code = delta.arguments.code
                        elif isinstance(delta.arguments, dict) and 'code' in delta.arguments:
                            code = delta.arguments['code']
                        elif isinstance(delta.arguments, str):
                            code = delta.arguments
                    if not code and hasattr(delta, 'code'):
                        code = delta.code
                    if code:
                        print(f"\n>>> Executing Code:\n{code}\n<<<")
                elif delta.type == "code_execution_result":
                    output = ""
                    if hasattr(delta, 'result') and delta.result:
                        output = delta.result
                    elif hasattr(delta, 'output') and delta.output:
                        output = delta.output
                    if output:
                        print(output, end="", flush=True)
            elif event.event_type == "interaction.completed":
                print(f"\n\n=== Interaction Completed! Status: {event.interaction.status} ===")
                if event.interaction.status == "completed":
                    print("Agent validation succeeded!")
                else:
                    print(f"Agent validation finished with status: {event.interaction.status}")

    except Exception as e:
        print(f"Error executing verification interaction: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
