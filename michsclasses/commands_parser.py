#Class to keep track of the commands that need to be done
import re

class Commands:

	def __init__(self, file_path=None, raw_lines=None):
		self.commands = []
		self.orig_commands = []
		self.previous_command = None
		self.next_command = None

		if file_path:
			self.load_file(file_path)
		elif raw_lines:
			self.load_lines(raw_lines)

	def load_file(self, file_path):
		self.commands = []
		with open(file_path, "r") as file:
			self.load_lines(file.readlines())

	def load_lines(self, lines):
		for line in lines:
			if type(line) is bytes:
				line = line.decode('utf-8')
			
			line = line.strip()
			if not line:
				continue
			if line.startswith('[') or line.startswith('#'):
				continue

			try:
				parts = line.split(',')
				if len(parts) >= 3 and ":" in parts[0] and parts[1].isdigit():
					# Handles old format: 00:00:12,500,COMMAND
					timestamp_str = parts[0] + "." + parts[1]
					command_str = ",".join(parts[2:])
				elif len(parts) >= 2:
					# Handles 00:00:12.500,COMMAND or 12500,COMMAND
					timestamp_str = parts[0]
					command_str = ",".join(parts[1:])
				else:
					# Try to catch typos where a dot was used instead of a comma: 3541788.FLASH(20)
					dot_match = re.match(r'^(\d+)\.(.+)$', line)
					if dot_match:
						timestamp_str = dot_match.group(1)
						command_str = dot_match.group(2)
					else:
						continue

				command_str = command_str.strip()
				timestamp_str = timestamp_str.replace(',', '.')

				# Check if timestamp is pure integer (milliseconds)
				if timestamp_str.isdigit():
					timestampmilliseconds = int(timestamp_str)
				else:
					# Fallback to old format HH:MM:SS.mmm
					pattern = r'(\d{2}):(\d{2}):(\d{2})\.(\d+)'
					match = re.match(pattern, timestamp_str)

					if not match:
						print("ERROR: Timestamp not in expected format! : "+timestamp_str)
						continue

					hours, minutes, seconds, milliseconds = match.groups()
					# Pad milliseconds to 3 digits (e.g. '62' -> '620', '6' -> '600')
					milliseconds = milliseconds.ljust(3, '0')[:3]
					
					timestampmilliseconds = (int(hours) * 60 * 60 * 1000) + (int(minutes) * 60 * 1000) + (int(seconds) * 1000 ) + int(milliseconds)
				
				# Convert command to integer if it's a pure percentage number
				if command_str.isdigit():
					command_str = int(command_str)

				self.commands.append((timestampmilliseconds, command_str))
			except Exception as e:
				print("ERROR: Parsing line failed! : "+line+" | Error: "+str(e))
		
		# Sort commands by timestamp to be safe
		self.commands.sort(key=lambda x: x[0])
		self.orig_commands = self.commands.copy()
		return self.commands

	def reset(self, timestamp=0):
		self.commands = self.orig_commands.copy()
		self.delete_past_commands(timestamp)

	def delete_past_commands(self, timestamp):
		new_commands = []
		for key, value in self.commands:
			if timestamp > key:
				self.previous_command = {key : value}
			else:
				new_commands.append((key, value))
		
		self.commands = new_commands
		return self.commands

	def commands_to_execute(self, timestamp_start, timestamp_end):
		commands_to_do = []

		for timestampmilliseconds, command in self.commands:
			if timestamp_start <= timestampmilliseconds <= timestamp_end:
				commands_to_do.append((timestampmilliseconds, command))
			elif timestampmilliseconds > timestamp_end:
				break #Skip the rest since it will all be bigger then currenttime

		return commands_to_do

	def remove_command(self, key):
		for i, (ts, cmd) in enumerate(self.commands):
			if ts == key:
				del self.commands[i]
				return True
		return False

	def set_previous_command(self, command):
		self.previous_command = command

	def get_previous_command(self):
		return self.previous_command

	def get_next_command(self):
		if not len(self.commands):
			return None
		return self.commands[0]