import requests
import time
import os



# Movie filename you are interested in
target_movie_filename = "Top.Gun.Maverick.2022.IMAX.1080p.BluRay.DDP.7.1.DV.x265-LEGi0N.mkv"

class Kodi:

    def __init__(self):
        # Kodi settings
        self.kodi_url = "http://127.0.0.1:8082/jsonrpc"  # replace with your Kodi's IP address and port
        self.kodi_username = "kodi"
        self.kodi_password = "admin1234"
        self.filename = None
        self.directorypath = None


    def get_kodi_playing_info(self):
        # Get currently playing item from Kodi
        #payload = {
        #    "jsonrpc": "2.0",
        #    "method": "Player.GetActivePlayers",
        #    "id": 1,
        #}
        #response = requests.post(self.kodi_url, json=payload, auth=(self.kodi_username, self.kodi_password))
        #result = response.json()



        #if "result" in result and result["result"]:
        #    player_id = result["result"][0]["playerid"]
        player_id = 1

        # Get player properties, including the current item and time
        payload = {
            "jsonrpc": "2.0",
            "method": "Player.GetProperties",
            "params": {"playerid": player_id, "properties": ["time", "percentage", "speed", "position", "totaltime"]},
            "id": 1,
        }
        response = requests.post(self.kodi_url, json=payload, auth=(self.kodi_username, self.kodi_password))
        result = response.json()


        if "result" in result:
            return result["result"]
        
        return None

    def player_getitem_file(self):
        player_id = 1

        # Get player properties, including the current item and time
        payload = {
            "jsonrpc": "2.0",
            "method": "Player.GetItem",
            "params": {
                "playerid": player_id,
                "properties": ["file"]
            },
            "id": 1
        }

        response = requests.post(self.kodi_url, json=payload, auth=(self.kodi_username, self.kodi_password))
        result = response.json()
        if result and result.get('result', {}).get('item', {}).get('file') is not None:
            filename = result['result']['item']['file']
            return filename



    def get_movie_time(self):
        # Get currently playing info from Kodi
        playing_info = self.get_kodi_playing_info()

        if playing_info and "time" in playing_info:
            #current_filename = playing_info["item"]["file"]
            kodi_time = playing_info["time"]
            current_time = kodi_time["hours"] * 3600 + kodi_time["minutes"] * 60 + kodi_time["seconds"]
            current_time = current_time * 1000
            current_time = current_time + kodi_time["milliseconds"]
            return current_time
        else:
            print("Could not successfully parse time from Kodi!")
            return False


    def get_file(self):
        filepath = self.player_getitem_file()
        if not filepath:
            print("Get file() WARNING ")
            print(filepath)
            return None, None
        self.directorypath = self.directorypath_from_filepath(filepath)
        self.filename = self.filename_from_filepath(filepath)
        return self.filename, self.directorypath


    def directorypath_from_filepath(self, filepath):
        if not isinstance(filepath, (str, os.PathLike)):
            return None
        directorypath = os.path.dirname(filepath) # Extract the directory path

        if not os.path.exists(directorypath):
            return None
        
        return os.path.abspath(directorypath)

    def filename_from_filepath(self, filepath):
        if not isinstance(filepath, (str, os.PathLike)):
            return None
        filename = os.path.basename(filepath)
        return filename