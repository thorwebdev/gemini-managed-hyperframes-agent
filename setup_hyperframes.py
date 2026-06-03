import os
import sys
from google import genai

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # Read the 3 setup scripts from the same directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    setup_scripts = [
        ("setup_1_chrome.sh", "/workspace/setup_1_chrome.sh"),
        ("setup_2_headless_and_cli.sh", "/workspace/setup_2_headless_and_cli.sh"),
        ("setup_3_skills_and_verify.sh", "/workspace/setup_3_skills_and_verify.sh"),
    ]

    sources = []
    for filename, target in setup_scripts:
        path = os.path.join(script_dir, filename)
        try:
            with open(path, "r") as f:
                content = f.read()
        except Exception as e:
            print(f"Error: Could not read {filename} from {path}: {e}")
            sys.exit(1)
        sources.append({
            "type": "inline",
            "content": content,
            "target": target
        })

    print("Creating streaming interaction with Antigravity agent to set up base environment...")
    try:
        # Mount all 3 setup scripts as inline sources and instruct the agent
        # to run them sequentially. Each script is scoped to fit under the
        # 300s sandbox command timeout.
        stream = client.interactions.create(
            agent="antigravity-preview-05-2026",
            input=(
                "Set up the HyperFrames environment by running these 3 scripts in order. "
                "Run each one separately with bash:\n"
                "1. bash /workspace/setup_1_chrome.sh\n"
                "2. bash /workspace/setup_2_headless_and_cli.sh\n"
                "3. bash /workspace/setup_3_skills_and_verify.sh\n\n"
                "Run them one at a time. After all 3 complete, confirm the final "
                "verification output shows all tools installed.\n\n"
                "IMPORTANT: For any later hyperframes commands, always set "
                "HYPERFRAMES_BROWSER_PATH=/usr/bin/chrome-headless-shell first."
            ),
            environment={
                "type": "remote",
                "sources": sources
            },
            stream=True
        )
        
        first_interaction_id = None
        env_id = None
        setup_completed_found = False
        
        # For accumulating arguments of function calls
        func_call_name = None
        func_call_id = None
        func_args_accumulated = ""

        current_step_type = None
        current_step_index = None

        for event in stream:
            if event.event_type == "interaction.created":
                first_interaction_id = event.interaction.id
                env_id = event.interaction.environment_id
                print(f"\n=== Interaction Created ===")
                print(f"ID: {first_interaction_id}")
                print(f"Environment ID: {env_id}")
                
            elif event.event_type == "interaction.status_update":
                print(f"\n[Status Update]: {event.status}")
                
            elif event.event_type == "step.start":
                step = event.step
                current_step_type = step.type
                current_step_index = event.index
                print(f"\n\n--- Step {event.index}: {step.type} ---")
                
                if step.type == "function_call":
                    func_call_id = step.id
                    func_call_name = step.name
                    func_args_accumulated = ""
                    print(f"  [Client Function Call Requested]")
                    print(f"  ID: {func_call_id}")
                    print(f"  Function: {func_call_name}")
                elif step.type == "google_search_call":
                    print(f"  [Google Search Call]")
                    print(f"  ID: {step.id}")
                elif step.type == "google_search_result":
                    call_id = getattr(step, 'call_id', None)
                    print(f"  [Google Search Result for Call ID: {call_id}]")
                elif step.type == "code_execution_call":
                    print(f"  [Running Code Execution...]")
                elif step.type == "code_execution_result":
                    print(f"  [Code Execution Result]")
                elif step.type == "function_result":
                    call_id = getattr(step, 'call_id', None)
                    func_name = getattr(step, 'name', None)
                    print(f"  [Client Function Result Submitted]")
                    print(f"  Call ID: {call_id}")
                    print(f"  Function: {func_name}")
                    
            elif event.event_type == "step.delta":
                delta = event.delta
                
                if delta.type == "text":
                    print(delta.text, end="", flush=True)
                    if "=== Setup Completed ===" in delta.text:
                        setup_completed_found = True
                        
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
                    
                elif delta.type == "arguments_delta":
                    func_args_accumulated += delta.arguments
                    print(delta.arguments, end="", flush=True)
                    
                elif delta.type == "google_search_call":
                    queries = []
                    if hasattr(delta, 'arguments') and delta.arguments:
                        if hasattr(delta.arguments, 'queries'):
                            queries = delta.arguments.queries
                        elif isinstance(delta.arguments, dict):
                            queries = delta.arguments.get('queries', [])
                    if queries:
                        print(f"  Queries: {queries}")
                    else:
                        print(f"  Search Delta: {delta}")
                        
                elif delta.type == "google_search_result":
                    is_error = getattr(delta, 'is_error', None)
                    print(f"  Search status: (Error: {is_error})")
                        
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
                    else:
                        print(f"\n[Code Call Delta]: {delta}")
                        
                elif delta.type == "code_execution_result":
                    output = ""
                    if hasattr(delta, 'result') and delta.result:
                        output = delta.result
                    elif hasattr(delta, 'output') and delta.output:
                        output = delta.output
                    
                    if output:
                        print(output, end="", flush=True)
                    else:
                        print(f"\n[Code Result Delta]: {delta}")
                else:
                    # Generic fallback for other delta types
                    print(f"\n[Delta {delta.type}]: {delta}")
                    
            elif event.event_type == "step.stop":
                if current_step_type == "function_call" and func_args_accumulated:
                    print(f"\n  [Full Arguments Accumulated]: {func_args_accumulated}")
                print(f"\n--- Step {event.index} Stop ---")
                current_step_type = None
                current_step_index = None
                
            elif event.event_type == "interaction.completed":
                print(f"\n\n=== Interaction Completed! Status: {event.interaction.status} ===")
                if event.interaction.status == "completed" or setup_completed_found:
                    print("Setup succeeded!")
                    if env_id:
                        env_id_path = os.path.join(script_dir, "hyperframes_env_id.txt")
                        with open(env_id_path, "w") as f:
                            f.write(env_id)
                        print(f"Saved environment ID to {env_id_path}: {env_id}")
                else:
                    print(f"Setup finished with status: {event.interaction.status}")
                    
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
