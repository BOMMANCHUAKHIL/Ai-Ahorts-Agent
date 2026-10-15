import modal
from src.orchestrator import ShortsOrchestrator

app = modal.App("shorts-agent")
image = modal.Image.debian_slim().pip_install_from_requirements("requirements.txt")

@app.function(
    image=image,
    schedule=modal.Cron("0 * * * *"),
    secrets=[modal.Secret.from_name("youtube-creds")],
    timeout=600
)
def run_cycle():
    ShortsOrchestrator().run_cycle()