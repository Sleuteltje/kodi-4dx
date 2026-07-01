import re
import os

class ProjectParser:
	def __init__(self, filepath):
		self.filepath = filepath
		self.blocks = []
		self._parse()

	def _parse(self):
		if not os.path.exists(self.filepath):
			print(f"ERROR: Project file {self.filepath} not found!")
			return

		with open(self.filepath, 'r', encoding='utf-8') as f:
			lines = f.readlines()
			
		current_block = None
		
		for raw_line in lines:
			line = raw_line.strip()
			if not line or line.startswith('##'):
				continue
				
			# Check for block header e.g. [TRIVIA] REPEAT, IMG:2000
			block_match = re.match(r'^\[([a-zA-Z0-9_-]+)\](.*)$', line)
			if block_match:
				block_name = block_match.group(1).upper()
				options_str = block_match.group(2).strip().replace(',', ' ')
				
				# Parse global options
				options = {
					"REPEAT": False,
					"IMG": None,
					"DURATION": None,
					"MUSIC": None
				}
				
				# Extract key:val or flags
				opt_tokens = re.findall(r'(\w+)(?:[:=]("[^"]*"|\S+))?', options_str)
				for key, val in opt_tokens:
					key = key.upper()
					if val == '': val = None
					if val and val.startswith('"') and val.endswith('"'):
						val = val[1:-1]
						
					if key == "REPEAT":
						options["REPEAT"] = True
					elif key == "IMG":
						options["IMG"] = int(val) if val else 0
					elif key == "DURATION":
						options["DURATION"] = int(val) if val else 0
					elif key == "MUSIC":
						options["MUSIC"] = val
						
				current_block = {
					"type": block_name,
					"options": options,
					"items": []
				}
				self.blocks.append(current_block)
				continue
				
			if current_block is None:
				continue # Items without a block are ignored
				
			# Parse item line e.g. REPEAT F:/trivia.jpeg 5000 + "F:/bg.mp3"
			item_repeat = False
			item_music = None
			item_duration = None
			
			if line.upper().startswith("REPEAT "):
				item_repeat = True
				line = line[7:].strip()
				
			if "+" in line:
				parts = line.split("+", 1)
				line = parts[0].strip()
				music_part = parts[1].strip()
				if music_part.startswith('"') and music_part.endswith('"'):
					item_music = music_part[1:-1]
				else:
					item_music = music_part
			
			# Extract file path and optional duration
			item_file = line
			
			# Check for quotes
			if line.startswith('"'):
				end_quote = line.find('"', 1)
				if end_quote != -1:
					item_file = line[1:end_quote]
					rest = line[end_quote+1:].strip()
					if rest.isdigit():
						item_duration = int(rest)
			else:
				# No quotes, check for trailing number
				last_space = line.rfind(' ')
				if last_space != -1:
					last_word = line[last_space+1:]
					if last_word.isdigit():
						item_duration = int(last_word)
						item_file = line[:last_space].strip()
						
			# Apply global IMG duration only if it's an image and no specific duration was set
			if item_duration is None:
				ext = os.path.splitext(item_file)[1].lower()
				if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
					item_duration = current_block["options"]["IMG"]
			
			current_block["items"].append({
				"file": item_file,
				"duration": item_duration,
				"repeat": item_repeat,
				"music": item_music
			})

	def get_blocks(self):
		return self.blocks
