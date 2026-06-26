import time
import socket
import struct
import configparser
import json
import urllib.request
import urllib.error
try:
	from lifxlan import Light
except ImportError:
	Light = None

def load_config():
	config = configparser.ConfigParser()
	config.read('config.ini')
	return config

def send_ha_webhook(config, track, command, intensity=0, duration=0, data=""):
	if 'HomeAssistant' not in config:
		print("Geen [HomeAssistant] sectie in config.")
		return
	url = config['HomeAssistant'].get('url', '')
	webhook_id = config['HomeAssistant'].get('webhook_id', '')
	token = config['HomeAssistant'].get('auth_token', '')
	
	if not url or not webhook_id:
		print("HA URL of webhook_id ontbreekt in config.")
		return
		
	endpoint = f"{url}/webhook/{webhook_id}"
	payload = {
		"track": track,
		"command": command,
		"intensity": intensity,
		"duration": duration,
		"data": data
	}
	
	print(f"-> Sending Webhook: {payload}")
	
	req = urllib.request.Request(endpoint, data=json.dumps(payload).encode('utf-8'))
	req.add_header('Content-Type', 'application/json')
	if token:
		req.add_header('Authorization', f'Bearer {token}')
		
	try:
		urllib.request.urlopen(req, timeout=5)
	except Exception as e:
		print(f"HA Webhook error: {e}")

def test_ha_wind(config):
	print("\n--- TEST: Home Assistant (WIND) ---")
	speeds = [1, 20, 50, 100]
	for speed in speeds:
		print(f"Setting wind to {speed}%")
		send_ha_webhook(config, "wind", "SET_SPEED", intensity=speed)
		time.sleep(2)
	print("Turning wind OFF")
	send_ha_webhook(config, "wind", "TURN_OFF")
	print("Test complete.\n")

def test_ha_color(config):
	print("\n--- TEST: Home Assistant (COLOR) ---")
	colors = ["red", "blue", "green", "white"]
	for color in colors:
		print(f"Setting color to {color}")
		send_ha_webhook(config, "color", "SET_COLOR", data=color)
		time.sleep(2)
	print("Turning color OFF (black)")
	send_ha_webhook(config, "color", "TURN_OFF")
	print("Test complete.\n")

def test_wled_lightning(config):
	print("\n--- TEST: WLED Direct UDP (LIGHTNING) ---")
	if 'WLED' not in config or 'ips' not in config['WLED']:
		print("Geen WLED ips in config.")
		return
	ips = [ip.strip() for ip in config['WLED']['ips'].split(',') if ip.strip()]
	
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	
	def send_wled(packet):
		for ip in ips:
			try:
				sock.sendto(packet, (ip, 21324))
			except:
				pass

	val = 255
	packet_white = bytearray([2, 2]) + bytearray([val, val, val] * 300) # Timeout 2s
	packet_black = bytearray([2, 2]) + bytearray([0, 0, 0] * 300)
	packet_exit = bytearray([2, 0]) # Exit realtime mode
	
	print("1. WLED 100% White voor 1 seconde...")
	send_wled(packet_white)
	time.sleep(1)
	
	print("2. WLED Off... lightning in 3... 2... 1...")
	send_wled(packet_exit)
	time.sleep(3)
	
	print("3. Lightning effect (4 flashes)...")
	for i in range(4):
		print(f"   Flash {i+1}!")
		send_wled(packet_white)
		time.sleep(0.05) # 50ms flash
		send_wled(packet_black) # Force render black before exiting
		time.sleep(0.1) # Wait between flashes
	
	send_wled(packet_exit) # Exit to idle ONLY after all flashes are done
	print("Test complete.\n")

def test_lifx_lightning(config):
	print("\n--- TEST: LIFX Direct UDP (LIGHTNING) ---")
	if 'LIFX' not in config or 'ips' not in config['LIFX']:
		print("Geen LIFX ips in config.")
		return
	ips = [ip.strip() for ip in config['LIFX']['ips'].split(',') if ip.strip()]
	
	if not Light:
		print("lifxlan library is niet geïnstalleerd!")
		return
		
	bulbs = []
	for ip in ips:
		print(f"Ontdekken van MAC voor {ip}...")
		# Quick discovery logic to get MAC
		discovery_packet = bytearray([
			0x24, 0x00, 0x00, 0x34, 0x00, 0x00, 0x00, 0x00,
			0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
			0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
			0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
			0x02, 0x00, 0x00, 0x00
		])
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		sock.settimeout(2.0)
		sock.sendto(discovery_packet, (ip, 56700))
		try:
			data, addr = sock.recvfrom(1024)
			mac = bytearray(data[8:16])
			mac_hex = ':'.join(f'{b:02x}' for b in mac[:6])
			print(f"Gevonden: {mac_hex}")
			bulbs.append(Light(mac_hex, ip))
		except:
			print("MAC discovery mislukt!")
	
	if not bulbs:
		return
		
	for bulb in bulbs:
		try:
			original_power = bulb.get_power()
			original_color = bulb.get_color()
			
			print("0. LIFX Pre-warming (invisible power-on if it was off)...")
			if original_power == 0:
				# Set color to Black (Brightness 0) instantly so the power-on fade is invisible
				bulb.set_color([0, 0, 0, 6500], duration=0, rapid=True)
				bulb.set_power(65535, duration=0, rapid=True)
				time.sleep(0.3) # Wait for the physical bulb to finish its invisible power-on fade
			
			print("1. LIFX 100% White voor 1 seconde...")
			bulb.set_color([0, 0, 65535, 6500], duration=0, rapid=True)
			time.sleep(1)
			
			print("2. LIFX Off (Black)... lightning in 3... 2... 1...")
			bulb.set_color([0, 0, 0, 6500], duration=0, rapid=True)
			time.sleep(3)
			
			print("3. Lightning effect (4 flashes)...")
			for i in range(4):
				print(f"   Flash {i+1}!")
				# Instant White
				bulb.set_color([0, 0, 65535, 6500], duration=0, rapid=True)
				time.sleep(0.05)
				# Instant Black
				bulb.set_color([0, 0, 0, 6500], duration=0, rapid=True)
				time.sleep(0.1)
				
			print("4. Herstellen naar originele staat...")
			bulb.set_color(original_color, duration=500, rapid=True)
			if original_power == 0:
				time.sleep(0.5)
				bulb.set_power(0, duration=0, rapid=True)
				
		except Exception as e:
			print(f"LIFX fout: {e}")
			
	print("Test complete.\n")

def main():
	config = load_config()
	while True:
		print("====================================")
		print("      4DX Hardware Test Script")
		print("====================================")
		print("1. Test Home Assistant Webhook (WIND)")
		print("2. Test Home Assistant Webhook (COLOR)")
		print("3. Test WLED Direct UDP (LIGHTNING)")
		print("4. Test LIFX Direct UDP (LIGHTNING)")
		print("0. Afsluiten")
		
		choice = input("Maak een keuze: ")
		if choice == "1":
			test_ha_wind(config)
		elif choice == "2":
			test_ha_color(config)
		elif choice == "3":
			test_wled_lightning(config)
		elif choice == "4":
			test_lifx_lightning(config)
		elif choice == "0":
			break
		else:
			print("Ongeldige keuze.")

if __name__ == "__main__":
	main()
