"""Launch script that prints share URL immediately"""
import gradio as gr
from app import create_interface
import sys
import os

# Set UTF-8 encoding for Windows console
if os.name == 'nt':
    os.system('chcp 65001 >nul')

print("=" * 60, flush=True)
print("SignSpeak AI - Starting with public share link...", flush=True)
print("=" * 60, flush=True)

try:
    interface = create_interface()
    print("\nLaunching with public share link...", flush=True)

    # Launch with share=True
    interface.launch(
        share=True,
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        quiet=False
    )
except Exception as e:
    print(f"\nError: {e}", flush=True)
    sys.exit(1)
