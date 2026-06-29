from michsclasses import commands_parser
import asyncio
import os
import threading
import time
import socket
import struct

try:
	from lifxlan import Light
except ImportError:
	Light = None

class CommandsExecuter:

	def __init__(self, DeviceExecuter, movie_filename = None, filename = None):
		self.DeviceExecuter = DeviceExecuter
		self.movie_filename = None
		self.directory = ""
		self.old_movie_filename = None
		self.Parser = None
		
		self.filename = filename
		if self.filename is None:
			self.filename = self.DeviceExecuter.get_filename()
		self.current_time = 0 				#in milliseconds
		self.old_current_time = 0			#in milliseconds
		
		
		self.load_file()

	def load_file(self, filepath=None):
		import zipfile
		
		# Always reset Parser when loading a new file so old commands don't leak
		self.Parser = None

		if filepath:
			self.Parser = commands_parser.Commands(file_path=filepath)
			print("Loaded Parser through filepath")
			return self.Parser

		if self.movie_filename is None:
			return None

		movie_filename_without_extension, file_extension = os.path.splitext(self.movie_filename)
		
		# 1. Try to load from .4dz zip file
		zip_path = os.path.join(self.directory, movie_filename_without_extension + '.4dz')
		if os.path.exists(zip_path):
			try:
				with zipfile.ZipFile(zip_path, 'r') as z:
					# Find the correct file inside the zip based on self.filename (e.g. 'wind')
					target_name = self.filename.lower()
					for z_filename in z.namelist():
						if target_name in z_filename.lower():
							with z.open(z_filename) as f:
								self.Parser = commands_parser.Commands(raw_lines=f.readlines())
								print(f"Loaded {z_filename} from {zip_path}")
								return self.Parser
			except Exception as e:
				print(f"Error loading zip {zip_path}: {e}")

		# 2. Fallback to old behavior and standalone files
		possible_filenames = []
		if self.filename.endswith('.txt') or self.filename.endswith('.4dx'):
			possible_filenames.append(self.filename)
		else:
			# If it's just a track name (e.g. "wind")
			possible_filenames.append(f"{movie_filename_without_extension}.{self.filename}.4dx") # e.g. movie.wind.4dx
			possible_filenames.append(f"{self.filename}.4dx") # e.g. wind.4dx
			possible_filenames.append(f"{self.filename.capitalize()}.txt") # e.g. Wind.txt
			possible_filenames.append(f"{self.filename}.txt") # e.g. wind.txt

		# Check legacy 4D folder first
		for fname in possible_filenames:
			path = os.path.join(self.directory, f'4D {movie_filename_without_extension}', fname)
			if os.path.exists(path):
				self.Parser = commands_parser.Commands(file_path=path)
				print(f"Loaded commands file through 4D directory: {fname}")
				return self.Parser

		# Check movie directory next
		for fname in possible_filenames:
			path = os.path.join(self.directory, fname)
			if os.path.exists(path):
				self.Parser = commands_parser.Commands(file_path=path)
				print(f"Loaded commands file next to movie: {fname}")
				return self.Parser

		print("WARNING: Could not load Parser! Could not find commands file for: "+self.filename)
		return None

	def sync_with_movie(self, movie_filename, directory, kodi_time):
		self.old_movie_filename = self.movie_filename
		self.old_current_time = self.current_time

		self.movie_filename = movie_filename
		self.directory = directory
		
		# If nothing is playing, just return gracefully
		if self.movie_filename is None:
			if self.old_movie_filename is not None:
				print("Movie playback stopped.")
			return

		if kodi_time is False:
			return

		delay = 0
		if hasattr(self.DeviceExecuter, 'get_delay'):
			delay = self.DeviceExecuter.get_delay()

		self.current_time = kodi_time - delay

		if self.old_movie_filename != self.movie_filename:
			print(f"Playing Movie has been switched to: {self.movie_filename}")
			self.load_file()
			if self.Parser:
				self.Parser.delete_past_commands(self.current_time)
			print("New file loaded..")
			return

		if not self.Parser:
			# We already warned during load_file that no track was found. 
			# Return silently to prevent log spam every 0.1 seconds.
			return False

		if self.movie_skipped():
			return
		self.execute_commands()		


	def execute_commands(self):
		commands_to_execute = self.Parser.commands_to_execute(self.old_current_time, self.current_time)
		print("Currently playing movie: "+self.movie_filename)
		print("old_current_time: "+str(self.old_current_time)+" | current_time: "+str(self.current_time))
		print("Time in normal time: "+self.formatted_time(self.current_time))
		print("Previous Command: "+str(self.Parser.get_previous_command()))
		print("Next Command: "+str(self.Parser.get_next_command()))
		print("Commands to do: "+str(len(commands_to_execute)))
		print("-------------------------------------------------")

		for timestamp_to_do, command_to_do in commands_to_execute:
			self.execute_command(timestamp_to_do, command_to_do)
		return commands_to_execute

	def execute_command(self, timestamp_to_do, command_to_do):
		self.Parser.remove_command(timestamp_to_do)
		self.Parser.set_previous_command({timestamp_to_do : command_to_do})
		return self.call_deviceexecuter_method(command_to_do)

	def call_deviceexecuter_method(self, command):
		# If the device executer has a generic execute_action method (for percentages)
		if hasattr(self.DeviceExecuter, 'execute_action'):
			return self.DeviceExecuter.execute_action(command)
		
		# Fallback to old behavior for string commands like HIGH, LOW
		if command is not None and isinstance(command, str):
			if hasattr(self.DeviceExecuter, command) and callable(getattr(self.DeviceExecuter, command)):
				return getattr(self.DeviceExecuter, command)()
		print(f"Error: Could not execute command '{command}' on DeviceExecuter.")
		return False

	def movie_skipped(self):
		if self.movie_skipped_backwards() or self.movie_skipped_forwards():
			print("The movie was skipped.. restoring entire commands")
			self.Parser.reset(self.current_time)
			previous_command = self.Parser.get_previous_command()
			if previous_command:
				method_name = next(iter(previous_command.values()), None)
				print(f"method name: {method_name}")
				self.call_deviceexecuter_method(method_name) #Do the previous command, because this might be a scene where the previous command is still active
			return True #The Movie was skipped
		return False

	def movie_skipped_backwards(self):
		return self.current_time < self.old_current_time

	def movie_skipped_forwards(self):
		return (self.current_time - self.old_current_time) > 1000 #more then 1 second difference
	


	def directorypath_from_filepath(self, filepath):
		directorypath = os.path.dirname(filepath) # Extract the directory path

		if not os.path.exists(directorypath):
			return None

		return os.path.abspath(directorypath)

	def filename_from_filepath(self, filepath):
		filename = os.path.basename(filepath)
		return filename

	def formatted_time(self, milliseconds):
		return "{:02}:{:02}:{:02}:{:03}".format(
			int((milliseconds / (1000 * 60 * 60)) % 24),  # hours
			int((milliseconds / (1000 * 60)) % 60),       # minutes
			int((milliseconds / 1000) % 60),              # seconds
			int(milliseconds % 1000)                      # milliseconds
		)


class WindExecuter:

	def __init__(self, Fan):
		self.Fan = Fan

	def get_filename(self):
		return "wind"

	def execute_action(self, action):
		if isinstance(action, int):
			if action == 0:
				print("FAN TURNED OFF (0%)")
				return self.Fan.turn_off()
			else:
				print(f"FAN SET TO {action}%")
				return self.Fan.turn_on(action)
		elif isinstance(action, str):
			action_upper = action.upper()
			if hasattr(self, action_upper):
				return getattr(self, action_upper)()
		return False

	def OFF(self):
		print("FAN TURNED ON")
		return self.Fan.turn_off()

	def ECO(self):
		print("FAN TURNED ECO")
		return self.Fan.eco_mode()

	def LOW(self):
		print("FAN TURNED LOW")
		return self.Fan.turn_on(25)

	def MED(self):
		print("FAN TURNED MED")
		return self.Fan.turn_on(50)

	def HIGH(self):
		print("FAN TURNED HIGH")
		return self.Fan.turn_on(100)

class TrackExecuter:
	def __init__(self, track_name, ApiClient, delay=0, wled_ips=None, lifx_ips=None):
		self.track_name = track_name
		self.ApiClient = ApiClient
		self.delay = delay
		self.wled_ips = wled_ips if wled_ips else []
		self.lifx_ips = lifx_ips if lifx_ips else []
		self.lifx_macs = {}
		self.lifx_bulbs = []
		
		# Concurrency locks for overlapping lightning flashes
		self.wled_flash_count = 0
		self.wled_flash_lock = threading.Lock()
		self.lifx_flash_count = 0
		self.lifx_flash_lock = threading.Lock()
		self.lifx_state_cache = {}
		
		# Set up UDP socket for direct WLED control
		self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		
		if self.lifx_ips and self.track_name == "lightning":
			self._discover_lifx_macs()
			if Light:
				for ip in self.lifx_ips:
					mac = self.lifx_macs.get(ip)
					if mac:
						mac_hex = ':'.join(f'{b:02x}' for b in mac[:6])
						bulb = Light(mac_hex, ip)
						self.lifx_bulbs.append(bulb)

	def get_filename(self):
		return self.track_name

	def get_delay(self):
		return self.delay

	def execute_action(self, action):
		import re
		# Default payload structure
		payload = {
			"track": self.track_name,
			"command": "",
			"intensity": "",
			"duration": "",
			"data": ""
		}

		intensity_map = {
			"ECO": 20,
			"LOW": 25,
			"MED": 50,
			"HIGH": 100
		}

		if isinstance(action, int):
			# Just a percentage
			if action == 0:
				payload["command"] = "OFF"
				payload["intensity"] = 0
			else:
				payload["command"] = "ON"
				payload["intensity"] = action
		elif isinstance(action, str):
			# E.g. "OFF,0" or "FLASH(100, 1000)" or "BLUE,FLASH(10)" or "ORANGE,30"
			action_str = action.upper().strip()
			
			if action_str.startswith("OFF"):
				payload["command"] = "OFF"
				payload["intensity"] = 0
			elif action_str in intensity_map:
				payload["command"] = "ON"
				payload["intensity"] = intensity_map[action_str]
			else:
				# Check for FLASH command: FLASH(intensity, duration)
				flash_match = re.search(r'FLASH\((\d+)(?:,\s*(\d+))?\)', action_str)
				if flash_match:
					payload["command"] = "FLASH"
					payload["intensity"] = int(flash_match.group(1))
					if flash_match.group(2):
						payload["duration"] = int(flash_match.group(2))
					action_str = re.sub(r'FLASH\(\d+(?:,\s*\d+)?\)', '', action_str)
				
				# Check for plain intensity at the end of string (e.g. "BLUE, 100" or "ORANGE,30")
				brightness_match = re.search(r',\s*(\d+)$', action_str)
				if brightness_match and not payload["command"]: # If not already FLASH
					payload["command"] = "ON"
					payload["intensity"] = int(brightness_match.group(1))
					action_str = re.sub(r',\s*\d+$', '', action_str)

				# Clean up remaining string to use as "data" (e.g. "BLUE", "THUNDER(100)")
				action_str = action_str.strip(', ')
				if action_str:
					# If there wasn't a command set (e.g. it was just "STARTMOVIE" or "PAUSE")
					if not payload["command"] and not payload["intensity"]:
						payload["command"] = action_str
					else:
						payload["data"] = action_str
					
		# Send it!
		print(f"[{self.track_name.upper()}] Webhook Payload: {payload}")
		
		# Direct UDP for Lightning track
		if self.track_name == "lightning" and payload["command"] == "FLASH":
			duration = payload.get("duration")
			if not duration:
				duration = 30
			
			if self.wled_ips:
				self._send_wled_udp_flash(payload["intensity"], duration)
			if self.lifx_ips:
				self._send_lifx_udp_flash(payload["intensity"], duration)
			
		if hasattr(self.ApiClient, 'send_webhook'):
			return self.ApiClient.send_webhook(payload)
		return False

	def _send_wled_udp_flash(self, intensity_pct, duration_ms):
		if not self.wled_ips:
			return
		
		# For lightning, we always want a blinding white flash.
		# Intensity can be used in the future to decide HOW MANY lamps react.
		val = 255
		print(f"[{self.track_name.upper()}] Sending WLED UDP Flash: RGB({val},{val},{val}) for {duration_ms}ms (Intensity {intensity_pct}% used for logic later)")
		
		# DRGB Protocol (2): Timeout 2s (Byte 1), then R, G, B for each LED.
		# We send 300 LEDs worth of white to guarantee it covers the whole strip.
		packet_on = bytearray([2, 2]) + bytearray([val, val, val] * 300) # Increased timeout to 2s
		packet_black = bytearray([2, 2]) + bytearray([0, 0, 0] * 300)
		# Timeout 0 immediately ends realtime mode and returns to normal
		packet_off = bytearray([2, 0])
		
		def flash_thread():
			# Turn ON
			for ip in self.wled_ips:
				try:
					self.udp_sock.sendto(packet_on, (ip, 21324))
				except Exception as e:
					pass
					
			with self.wled_flash_lock:
				self.wled_flash_count += 1
			
			# Wait duration (Min 50ms to ensure ESP renders the frame)
			sleep_dur = max(0.05, duration_ms / 1000.0)
			time.sleep(sleep_dur)
			
			with self.wled_flash_lock:
				self.wled_flash_count -= 1
				
				# Always turn black to end the flash quickly without skipping frames
				for ip in self.wled_ips:
					try:
						self.udp_sock.sendto(packet_black, (ip, 21324))
					except Exception:
						pass
				
				if self.wled_flash_count == 0:
					# Give it 50ms to render the black frame, then exit realtime mode
					time.sleep(0.05)
					for ip in self.wled_ips:
						try:
							self.udp_sock.sendto(packet_off, (ip, 21324))
						except Exception as e:
							pass

		threading.Thread(target=flash_thread).start()

	def _discover_lifx_macs(self):
		print(f"[{self.track_name.upper()}] Discovering MAC addresses for LIFX bulbs...")
		discovery_packet = bytearray([
			0x24, 0x00, 0x00, 0x34, 0x00, 0x00, 0x00, 0x00,
			0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
			0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
			0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
			0x02, 0x00, 0x00, 0x00
		])
		
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		sock.settimeout(1.0)
		
		for ip in self.lifx_ips:
			try:
				sock.sendto(discovery_packet, (ip, 56700))
			except:
				pass
		
		end_time = time.time() + 2.0
		while time.time() < end_time:
			try:
				data, addr = sock.recvfrom(1024)
				ip = addr[0]
				if ip in self.lifx_ips and ip not in self.lifx_macs:
					self.lifx_macs[ip] = bytearray(data[8:16])
					mac_hex = ':'.join(f'{b:02x}' for b in self.lifx_macs[ip][:6])
					print(f"[{self.track_name.upper()}] Found LIFX bulb {ip} with MAC {mac_hex}")
			except socket.timeout:
				pass
		sock.close()

	def _send_lifx_udp_flash(self, intensity_pct, duration_ms):
		if not self.lifx_bulbs:
			return
		
		print(f"[{self.track_name.upper()}] Sending LIFX Flash via lifxlan for {duration_ms}ms")
		
		def lifx_thread(bulb, ip, duration):
			try:
				with self.lifx_flash_lock:
					if self.lifx_flash_count == 0:
						# First overlapping flash fetches the true idle state (takes ~50ms)
						original_power = bulb.get_power()
						original_color = bulb.get_color()
						self.lifx_state_cache[ip] = (original_power, original_color)
						
						# Pre-warm: If OFF, set to Black and turn ON to bypass slow hardware power-fade
						if original_power == 0:
							bulb.set_color([0, 0, 0, 6500], duration=0, rapid=True)
							bulb.set_power(65535, duration=0, rapid=True)
							time.sleep(0.15) # Wait for hardware fade to finish invisibly
							
					self.lifx_flash_count += 1
				
				# Force White instantly
				bulb.set_color([0, 0, 65535, 6500], duration=0, rapid=True)
				
				# Wait duration (Min 50ms)
				sleep_dur = max(0.05, duration / 1000.0)
				time.sleep(sleep_dur)
				
				with self.lifx_flash_lock:
					self.lifx_flash_count -= 1
					if self.lifx_flash_count == 0:
						# Only the last active flash restores the original idle state
						original_power, original_color = self.lifx_state_cache.get(ip, (0, [0,0,65535,3500]))
						if original_power == 0:
							# If it was off, just keep it black and power it off instantly
							bulb.set_color([0, 0, 0, 6500], duration=0, rapid=True)
							bulb.set_power(0, duration=0, rapid=True)
						else:
							# If it was on, fade back to the original color
							bulb.set_color(original_color, duration=200, rapid=True)
					else:
						# Not the last flash, so instantly turn Black for sharp gaps between flashes
						bulb.set_color([0, 0, 0, 6500], duration=0, rapid=True)
			except Exception as e:
				print(f"[{self.track_name.upper()}] LIFX Error: {e}")

		for bulb, ip in zip(self.lifx_bulbs, self.lifx_ips):
			threading.Thread(target=lifx_thread, args=(bulb, ip, duration_ms)).start()

