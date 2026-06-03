import os
import sys
from google import genai

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        sys.exit(1)

    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Read environment ID from hyperframes_env_id.txt
    env_file_path = os.path.join(script_dir, "hyperframes_env_id.txt")
    if not os.path.exists(env_file_path):
        print(f"Error: {env_file_path} does not exist. Run setup first.")
        sys.exit(1)

    with open(env_file_path, "r") as f:
        env_id = f.read().strip()

    print(f"Invoking 'hyperframes-video-agent' inside environment: {env_id}...")

    client = genai.Client(api_key=api_key)

    # A high-level, rich developer-focused prompt delegating design, research, and rendering to the custom agent
    user_prompt = (
        "You are tasked with creating a premium developer marketing video about 'Managed Agents in the Gemini API'.\n\n"
        "First, you MUST read these three sources to understand the exact architecture, features, and product messaging:\n"
        "1. https://ai.google.dev/gemini-api/docs/agent-environment.md.txt (Persistent remote sandboxes, source types, credentials)\n"
        "2. https://ai.google.dev/gemini-api/docs/managed-agents-quickstart.md.txt (Sessions, streaming, multi-turn persistence)\n"
        "3. https://blog.google/innovation-and-ai/technology/developers-tools/managed-agents-gemini-api/ (Official announcement blog)\n\n"
        "Construct a premium, landscape-oriented developer marketing video (1920x1080, 15-20 seconds) "
        "saved at '/workspace/marketing-video' and rendered to '/workspace/marketing-video/output.mp4'.\n\n"
        "Visual & Animation Design Contract (Non-Negotiable):\n"
        "- Aesthetic Preset: Use the 'Swiss Pulse' premium style: dark mode background (`#0c0c0e`), "
        "a single electric blue accent (`#3385FF`), bold 'Outfit' headlines (900 weight, uppercase, -0.03em letter-spacing), "
        "and a subtle, drifting tech-grid SVG noise/grain overlay (0.05 opacity).\n"
        "- Grid-Locked Wireframes & Shaders: Display a beautiful dynamic backdrop like a slowly rotating "
        "HTML Canvas digital web pattern or floating translucent blurred orbs to act as a modern background shader.\n"
        "- Kinetic Code Snippet: Present a realistic Python code block (e.g., `client.interactions.create(...)` "
        "with remote environment sources or network settings) inside a clean monospace pre block. "
        "Animate line-by-line reveals using timed opacity or slide shifts synced precisely to the video timeline.\n"
        "Compile, lint, and render the video composition. Once completed, upload the final video file '/workspace/marketing-video/output.mp4' "
        "to Litterbox using curl, and print the direct video download URL clearly in your final response so I can review the masterpiece."
    )

    try:
        stream = client.interactions.create(
            agent="hyperframes-video-agent",
            input=user_prompt,
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
                    print("Video creation succeeded!")
                else:
                    print(f"Video creation finished with status: {event.interaction.status}")

    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
