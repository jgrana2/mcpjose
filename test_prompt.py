import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from langchain_agent.whatsapp_runner import WhatsAppAgentLoop

class MockMessage:
    def __init__(self, body, from_number):
        self.body = body
        self.from_number = from_number
        self.caption = ""
        self.type = "text"
        self.media_id = None

class MockLoop(WhatsAppAgentLoop):
    def __init__(self):
        # Bypass init logic for test
        pass

loop = MockLoop()
msg = MockMessage("Hello world", "+573001234567")
prompt = loop._build_prompt(msg)
print("PROMPT IS:\n")
print(prompt)
