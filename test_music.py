# test_music.py
import os
import json
from src.orchestrator import ShortsOrchestrator

# Pretend a state file exists (starting from zero)
os.makedirs("output", exist_ok=True)
with open("output/state.json", "w") as f:
    json.dump({"counter": 0, "music_index": 0}, f)

print("── Cycle 1 ──")
orch = ShortsOrchestrator()
print("music_index:", orch.music_index)
print("next music :", orch._next_music())
orch._save_state()

print("\n── Cycle 2 (new instance, like main.py does) ──")
orch2 = ShortsOrchestrator()
print("music_index:", orch2.music_index)
print("next music :", orch2._next_music())
orch2._save_state()

print("\n── Cycle 3 ──")
orch3 = ShortsOrchestrator()
print("music_index:", orch3.music_index)
print("next music :", orch3._next_music())
orch3._save_state()

print("\n── state.json contents ──")
print(open("output/state.json").read())