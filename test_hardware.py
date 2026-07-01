import time
import socket
import struct
import configparser
import json
import urllib.request
import urllib.error
import sys
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

def test_unified_color(config):
	print("\n--- TEST: UNIFIED COLOR (WLED & LIFX TEGELIJK) ---")
	wled_ips, lifx_ips, lifx_bulbs, sock = setup_unified(config)
	
	def set_all(r, g, b, h, s, v, k):
		packet = bytearray([2, 2]) + bytearray([r, g, b] * 300)
		for ip in wled_ips:
			try:
				sock.sendto(packet, (ip, 21324))
			except:
				pass
		for bulb in lifx_bulbs:
			try:
				bulb.set_color([h, s, v, k], duration=0, rapid=True)
				bulb.set_power(65535, duration=0, rapid=True)
			except:
				pass

	print("1. Kleuren check (Rood, Groen, Blauw, Paars - elk 1s)")
	set_all(255, 0, 0, 0, 65535, 65535, 3500) # Rood
	time.sleep(1)
	set_all(0, 255, 0, 21845, 65535, 65535, 3500) # Groen
	time.sleep(1)
	set_all(0, 0, 255, 43690, 65535, 65535, 3500) # Blauw
	time.sleep(1)
	set_all(128, 0, 128, 50000, 65535, 65535, 3500) # Paars
	time.sleep(1)
	
	print("\nTest voltooid! WLED en LIFX worden afgesloten / idle.")
	for ip in wled_ips:
		sock.sendto(bytearray([2, 0]), (ip, 21324))
	for bulb in lifx_bulbs:
		try:
			bulb.set_power(0, duration=0, rapid=True)
		except:
			pass
	print("Klaar.")

def setup_unified(config):
	wled_ips = []
	if 'WLED' in config and 'ips' in config['WLED']:
		wled_ips = [ip.strip() for ip in config['WLED']['ips'].split(',') if ip.strip()]
	
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	
	lifx_ips = []
	if 'LIFX' in config and 'ips' in config['LIFX']:
		lifx_ips = [ip.strip() for ip in config['LIFX']['ips'].split(',') if ip.strip()]
	
	lifx_bulbs = []
	if Light and lifx_ips:
		print("LIFX lampen ontdekken...")
		discovery_packet = bytearray([
			0x24, 0x00, 0x00, 0x34, 0x00, 0x00, 0x00, 0x00,
			0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
			0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
			0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
			0x02, 0x00, 0x00, 0x00
		])
		dsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		dsock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		dsock.settimeout(2.0)
		for ip in lifx_ips:
			try:
				dsock.sendto(discovery_packet, (ip, 56700))
				data, addr = dsock.recvfrom(1024)
				mac = bytearray(data[8:16])
				mac_hex = ':'.join(f'{b:02x}' for b in mac[:6])
				lifx_bulbs.append(Light(mac_hex, ip))
			except:
				pass
		dsock.close()
		
	return wled_ips, lifx_ips, lifx_bulbs, sock

def test_unified_lightning(config, gap_ms=500):
	gap_s = gap_ms / 1000.0
	print(f"\n--- TEST: UNIFIED LIGHTNING (WLED & LIFX TEGELIJK) [Pauzes: {gap_ms}ms] ---")
	
	# --- Init ---
	wled_ips, lifx_ips, lifx_bulbs, sock = setup_unified(config)
	
	def send_wled(r, g, b):
		# Protocol 2 (DRGB), Timeout 2 sec
		packet = bytearray([2, 2]) + bytearray([r, g, b] * 300)
		for ip in wled_ips:
			try:
				sock.sendto(packet, (ip, 21324))
			except:
				pass

	def set_all(r, g, b, h, s, v, k):
		send_wled(r, g, b)
		for bulb in lifx_bulbs:
			try:
				bulb.set_color([h, s, v, k], duration=0, rapid=True)
			except:
				pass

	print("\n-- PRE-WARMING LIFX --")
	# We force power ON invisibly so we don't suffer hardware fades later
	for bulb in lifx_bulbs:
		try:
			bulb.set_color([0,0,0,6500], duration=0, rapid=True)
			bulb.set_power(65535, duration=0, rapid=True)
		except:
			pass
	time.sleep(0.5)

	# 1. Wit 1 sec, dan Zwart
	print("\n1. Wit aan voor 1 seconde, dan uit (zwart)")
	set_all(255, 255, 255, 0, 0, 65535, 6500)
	time.sleep(1)
	set_all(0, 0, 0, 0, 0, 0, 6500)
	time.sleep(1)

	print("Wacht 2 seconden...")
	time.sleep(2)

	# 3. 1 snelle flits (50ms wit, dan 0.5s wachten, dan zwart)
	print("3. Eén enkele super snelle flits (50ms)")
	set_all(255, 255, 255, 0, 0, 65535, 6500)
	time.sleep(0.05)
	set_all(0, 0, 0, 0, 0, 0, 6500)

	print("Wacht 2 seconden...")
	time.sleep(2)

	# 4. 4 snelle flitsen met gap pauze
	print(f"4. Vier snelle flitsen achter elkaar ({gap_ms}ms pauzes)")
	for i in range(4):
		set_all(255, 255, 255, 0, 0, 65535, 6500)
		time.sleep(0.05) # Flash duration
		set_all(0, 0, 0, 0, 0, 0, 6500)
		time.sleep(gap_s) # Gap duration

	print("Wacht 2 seconden...")
	time.sleep(2)

	# 5. Tragere intensere flits
	print("5. Eén tragere, zware bliksemschicht (200ms)")
	set_all(255, 255, 255, 0, 0, 65535, 6500)
	time.sleep(0.2)
	set_all(0, 0, 0, 0, 0, 0, 6500)

	print("Wacht 2 seconden...")
	time.sleep(2)

	# 6. 4 tragere flitsen met gap pauze
	print(f"6. Vier zware bliksemschichten (200ms) met ({gap_ms}ms) pauzes ertussen")
	for i in range(4):
		set_all(255, 255, 255, 0, 0, 65535, 6500)
		time.sleep(0.2) # Flash duration
		set_all(0, 0, 0, 0, 0, 0, 6500)
		time.sleep(gap_s) # Gap duration

	print("Wacht 2 seconden...")
	time.sleep(2)

	# 7. 4 flitsen van zwak naar sterk
	print(f"7. Vier flitsen (GROEN) opbouwend in intensiteit (25%, 50%, 75%, 100%) met {gap_ms}ms pauze")
	intensities = [0.25, 0.50, 0.75, 1.0]
	for pct in intensities:
		wled_val = int(255 * pct)
		lifx_val = int(65535 * pct)
		set_all(0, wled_val, 0, 21845, 65535, lifx_val, 6500)
		time.sleep(0.05) # Flash duration
		set_all(0, 0, 0, 0, 0, 0, 6500)
		time.sleep(gap_s) # Gap duration

	print("\nTest voltooid! WLED en LIFX worden afgesloten / idle.")
	# WLED Exit realtime mode
	for ip in wled_ips:
		sock.sendto(bytearray([2, 0]), (ip, 21324))
	# LIFX Power Off
	for bulb in lifx_bulbs:
		try:
			bulb.set_power(0, duration=0, rapid=True)
		except:
			pass
	print("Klaar.")

def main():
	config = load_config()
	
	# Check for command line arguments
	if len(sys.argv) > 1:
		choice = sys.argv[1]
		gap_ms = 50
		if len(sys.argv) > 2:
			try:
				gap_ms = int(sys.argv[2])
			except ValueError:
				pass
				
		if choice == "1":
			test_ha_wind(config)
		elif choice == "2":
			test_ha_color(config)
		elif choice == "3":
			test_unified_lightning(config, gap_ms)
		return # Exit immediately after running the argument
		
	while True:
		print("====================================")
		print("      4DX Hardware Test Script")
		print("====================================")
		print("1. Test Home Assistant Webhook (WIND)")
		print("2. Test Home Assistant Webhook (COLOR)")
		print("3. Test UNIFIED LIGHTNING (WLED & LIFX Tegelijk)")
		print("4. Test UNIFIED COLOR (WLED & LIFX Tegelijk)")
		print("0. Afsluiten")
		
		choice = input("Maak een keuze: ")
		if choice == "1":
			test_ha_wind(config)
		elif choice == "2":
			test_ha_color(config)
		elif choice == "3":
			test_unified_lightning(config)
		elif choice == "4":
			test_unified_color(config)
		elif choice == "0":
			break
		else:
			print("Ongeldige keuze.")

if __name__ == "__main__":
	main()
