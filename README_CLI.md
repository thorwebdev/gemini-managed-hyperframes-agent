# HyperFrames Video Agent — CLI Operations Guide

This guide explains how to provision, register, and run the **HyperFrames Video Agent** using the **Gemini API CLI (`gemini-api`)** instead of the Python SDK orchestration scripts.

---

## Prerequisites

1. Ensure you have the `gemini-api` CLI installed and available in your system path.
2. Export your API Key:
   ```bash
   export GEMINI_API_KEY="your-api-key"
   ```

---

## Step 1: Provision & Setup the Environment

Run a remote interaction session using the base agent to upload the 3-part installation scripts and run them sequentially. This installs Chrome, the headless shell, FFmpeg, and the `hyperframes` CLI.

Execute the following command in your terminal from the project directory:

```bash
gemini-api run \
  --agent "antigravity-preview-05-2026" \
  --network-allowlist "*" \
  --tool code_execution \
  --tool google_search \
  --source "inline:/workspace/setup_1_chrome.sh:$(cat setup_1_chrome.sh)" \
  --source "inline:/workspace/setup_2_headless_and_cli.sh:$(cat setup_2_headless_and_cli.sh)" \
  --source "inline:/workspace/setup_3_skills_and_verify.sh:$(cat setup_3_skills_and_verify.sh)" \
  "Set up the HyperFrames environment by running these 3 scripts in order. Run each one separately with bash:
1. bash /workspace/setup_1_chrome.sh
2. bash /workspace/setup_2_headless_and_cli.sh
3. bash /workspace/setup_3_skills_and_verify.sh

Run them one at a time. After all 3 complete, confirm the final verification output shows all tools installed.

IMPORTANT: For any later hyperframes commands, always set HYPERFRAMES_BROWSER_PATH=/usr/bin/chrome-headless-shell first."
```

> [!IMPORTANT]
> When the command runs, look at the top of the interaction stream or CLI output for the **Environment ID** (e.g., `env-1234567890abcdef`). You will need this ID for the next steps.

To double check that the environment is set up correctly, you can run the following command:

```bash
gemini-api run \
  --agent "antigravity-preview-05-2026" \
  --environment <environment-id> \
  "Check and print the status of the environment by running:
   echo '=== Verification ==='
   ffmpeg -version | head -n 1
   google-chrome-stable --version
   chrome-headless-shell --version
   hyperframes --help | head -n 1
   ls -la /workspace/.cache/libs/gsap.min.js
   ls -la /.agents/skills/
  "

```

---

---

## Step 2: Register/Create the Custom Managed Agent

Deploy the custom managed agent to the platform. The CLI reads the agent's definition from [agent.yaml](file:///Users/schaeff/Documents/code/interactions-api/managed-agents/video-agent/agent.yaml) and automatically attaches [AGENTS.md](file:///Users/schaeff/Documents/code/interactions-api/managed-agents/video-agent/AGENTS.md) as the system instruction.

Make sure to replace `<environment-id>` with the Environment ID from Step 1.

#### Option A: Create a new agent
```bash
gemini-api agents create --path . --base-env <environment-id>
```

#### Option B: Update an existing agent (If already registered)
If you get a `409: Requested entity already exists` error, use the `update` command to link the new base environment to the existing agent:
```bash
gemini-api agents update --path . --base-env <environment-id>
```
*(Or delete it first with `gemini-api agents delete hyperframes-video-agent --force` and recreate it).*

---

## Step 3: Run the Video Generation Call

Invoke the custom agent using `gemini-api run`. You do **not** need to specify the `--environment` flag here. The platform will automatically fork a fresh, isolated container instance from your snapshotted base environment:

```bash
gemini-api run \
  --agent "hyperframes-video-agent" \
  "You are tasked with creating a premium developer marketing video about 'Managed Agents in the Gemini API'.

First, you MUST read these three sources to understand the exact architecture, features, and product messaging:
1. https://ai.google.dev/gemini-api/docs/agent-environment.md.txt (Persistent remote sandboxes, source types, credentials)
2. https://ai.google.dev/gemini-api/docs/managed-agents-quickstart.md.txt (Sessions, streaming, multi-turn persistence)
3. https://blog.google/innovation-and-ai/technology/developers-tools/managed-agents-gemini-api/ (Official announcement blog)

Construct a premium, landscape-oriented developer marketing video (1920x1080, 15-20 seconds) saved at '/workspace/marketing-video' and rendered to '/workspace/marketing-video/output.mp4'. Make sure you write the actual HTML/CSS/GSAP animations into index.html (do not leave it blank).

Visual & Animation Design Contract (Non-Negotiable):
- Audio / Narration: None. Generate a completely silent video. Do not attempt to use TTS or generate audio narration.
- Aesthetic Preset: Use the 'Swiss Pulse' premium style: dark mode background (\`#0c0c0e\`), a single electric blue accent (\`#3385FF\`), bold 'Outfit' headlines (900 weight, uppercase, -0.03em letter-spacing), and a subtle, drifting tech-grid SVG noise/grain overlay (0.05 opacity).
- Grid-Locked Wireframes & Shaders: Display a beautiful dynamic backdrop like a slowly rotating HTML Canvas digital web pattern or floating translucent blurred orbs to act as a modern background shader.
- Kinetic Code Snippet: Present a realistic Python code block (e.g., \`client.interactions.create(...)\` with remote environment sources or network settings) inside a clean monospace pre block. Animate line-by-line reveals using timed opacity or slide shifts synced precisely to the video timeline.

Compile, lint, and render the video composition. Once completed, upload the final video file '/workspace/marketing-video/output.mp4' to Litterbox using curl, and print the direct video download URL clearly in your final response so I can review the masterpiece."
```

---

## 💡 Troubleshooting & Gotchas

### 1. Setup Timeout During Step 1 (600s Server Limit)
The total Turn Timeout for a single API interaction is 600s (10 minutes). If compiling Chrome and the headless shell takes too long, the setup script might time out before executing the 3rd script (`setup_3_skills_and_verify.sh`), resulting in missing skills or GSAP.
* **Workaround:** Run the scripts sequentially inside the same environment ID to spread the execution budget:
  ```bash
  # Run setup part 2 inside the environment
  gemini-api run --agent "antigravity-preview-05-2026" --environment <env-id> \
    --source "inline:/workspace/setup_2_headless_and_cli.sh:$(cat setup_2_headless_and_cli.sh)" \
    "bash /workspace/setup_2_headless_and_cli.sh"
  
  # Run setup part 3 inside the environment
  gemini-api run --agent "antigravity-preview-05-2026" --environment <env-id> \
    --source "inline:/workspace/setup_3_skills_and_verify.sh:$(cat setup_3_skills_and_verify.sh)" \
    "bash /workspace/setup_3_skills_and_verify.sh"
  ```

### 2. Rendered Video is Completely Black
A black video means headless Chrome initialized the canvas/body, but the animation timeline never ran (leaving elements at their initial `opacity: 0` or hidden state).
* **Cause A: External CDN usage.** Headless Chrome rejects external CDN HTTPS requests inside the sandbox proxy jail. Always load GSAP locally:
  ```html
  <script src="/workspace/.cache/libs/gsap.min.js"></script>
  ```
* **Cause B: Missing workspace symlink.** Compositions that reference absolute `/workspace` paths (like the GSAP local mirror above) will 404 unless the project directory has an active symlink mapping back to `/workspace`:
  ```bash
  ln -sf /workspace /workspace/marketing-video/workspace
  ```
* **Cause C: Timeline ID mismatch.** The timeline registered on `window.__timelines["<id>"] = tl` must match the root composition element's `data-composition-id="<id>"` in your HTML (e.g. `main` or `root`).
* **Cause D: Blank template index.html.** Verify that the agent actually wrote the custom code inside `index.html` instead of leaving a boilerplate blank skeleton.

### 3. TTS (Speech Synthesis) Fails / Banned
On-device TTS (using Kokoro ONNX) is **banned** in the sandbox environment because the container lacks the CPU and memory resources to run it efficiently, causing out-of-memory errors and Turn Timeouts.
* **Workaround:** Always instruct the agent to generate completely silent videos (no audio narration/tracks).



