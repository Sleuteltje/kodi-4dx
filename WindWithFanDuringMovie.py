import time
import requests
import re
import sys
from bs4 import BeautifulSoup
from michsclasses import commands_parser
from michsclasses import home_assistant_api
from michsclasses import mpc_hc
from michsclasses import kodi
from michsclasses import commands_executer
import asyncio
import os

import configparser

# Load configuration from config.ini
config = configparser.ConfigParser()
config.read('config.ini')
HA_API_URL = config['HomeAssistant'].get('url', 'http://192.168.1.153:8123/api')
HA_WEBHOOK_ID = config['HomeAssistant'].get('webhook_id', '')
HA_AUTH_TOKEN = config['HomeAssistant'].get('auth_token', '')

tracks_to_load = {}
if 'Tracks' in config:
	for track_name, delay_str in config['Tracks'].items():
		tracks_to_load[track_name] = int(delay_str)

WLED_IPS = []
if 'WLED' in config and 'ips' in config['WLED']:
	ips_str = config['WLED']['ips']
	WLED_IPS = [ip.strip() for ip in ips_str.split(',') if ip.strip()]

# Set up Home Assistant API Connection
# Token is optional for webhooks
Api = home_assistant_api.HomeAssistantApi(HA_API_URL, HA_WEBHOOK_ID, HA_AUTH_TOKEN)

active_tracks = []
for track_name, delay in tracks_to_load.items():
	Executer = commands_executer.TrackExecuter(track_name, Api, delay, wled_ips=WLED_IPS)
	CmdExecuter = commands_executer.CommandsExecuter(Executer)
	active_tracks.append(CmdExecuter)

# Set up Kodi
Kodi = kodi.Kodi()

print(f"Loaded 4DX Engine with tracks: {', '.join(tracks_to_load)}")
print("Waiting for Kodi playback...")

# Execute the main function
if __name__ == "__main__":
	mainloop = True
	while mainloop:
		# Fetch Kodi state ONCE per loop to prevent spamming the Kodi API
		# (5 tracks * 2 requests = 10 requests per loop previously!)
		movie_filename, directory = Kodi.get_file()
		kodi_time = Kodi.get_movie_time()
		
		for Track in active_tracks:
			Track.sync_with_movie(movie_filename, directory, kodi_time)
			
		# Extremely short sleep for minimal latency (10ms)
		# Since the HTTP requests above also take some ms, this ensures the engine is blazing fast.
		time.sleep(0.01)


