import os
import sys

# Mock imports so we can test the parser standalone
sys.path.append(r"d:\_Projects\4dx\kodi-4dx")
from michsclasses import commands_parser

raw_lines = [
	"00:00:26,530,ORANGE,30",
	"00:00:31,630,ORANGE,10",
	"00:00:32.820,ORANGE,30",
	"01:28:29,720,ENDCREDITS"
]

parser = commands_parser.Commands(raw_lines=raw_lines)
print("Parsed commands:")
for ts, cmd in parser.commands:
	print(f"Timestamp: {ts}, Command: {cmd}")
