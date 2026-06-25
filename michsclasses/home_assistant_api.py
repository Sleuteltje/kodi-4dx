# home_assistant_api.py
# Python Class to help connect with Home Assistant API
# (c) 2023 M. Roffel - mroffel.nl
import requests
import threading


class Light:
	def __init__(self, entity_id, ApiClient):
		self.ApiClient = ApiClient
		self.entity_id = entity_id

	async def turn_on(self):
		data = {
			"entity_id": self.entity_id,
		}

		print("Turning light on: "+str(self.entity_id))
		return self.ApiClient.call_api_link('/services/light/turn_on', data)


class Scene:
	def __init__(self, scene_id, ApiClient):
		self.ApiClient = ApiClient;
		self.scene_id = scene_id

	def turn_on(self):
		return self.ApiClient.call_api_link('/services/scene/turn_on', {"entity_id": self.scene_id})


## Fan Device
class Fan:
	def __init__(self, entity_id, ApiClient):
		self.ApiClient = ApiClient
		self.entity_id = entity_id

	def turn_on(self, percentage=100, mode="Normal"):
		data = {
			"entity_id": self.entity_id,
			"percentage": percentage,
			"preset_mode": mode
		}

		print("Setting Fan speed: "+str(percentage))
		return self.ApiClient.call_api_link('/services/fan/turn_on', data)		

	def turn_off(self):
		data = {
			"entity_id": self.entity_id,
		}

		print("Turning Fan off")
		return self.ApiClient.call_api_link('/services/fan/turn_off', data)

	def set_preset_mode(self, mode="Normal"):
		data = {
			"entity_id": self.entity_id,
			"preset_mode": mode,
		}    

		print("Setting Fan to preset_mode "+mode)
		return self.ApiClient.call_api_link('/services/fan/set_preset_mode', data)

	#Helpers
	def eco_mode(self, percentage=20):
		return self.turn_on(percentage, "Nature")





class HomeAssistantApi:
	def __init__(self, APIURL, webhook_id, token=None):
		self.HEADERS = {
			"content-type": "application/json",
		}
		if token:
			self.HEADERS["Authorization"] = "Bearer " + token
			
		self.APIURL = APIURL
		self.webhook_id = webhook_id


	#Easiest way to see what the command is in Home Assistant is to create a new script
	#At action choose "Call Service"
	#In the dropdown start typing for the type of device, for instance: fan
	#All the options will be visible, pick one
	#Choose the device as the entity 
	#Type/pick something for the payload for instance "set_percentage" to "25"
	#Now click view in YAML and it's now very easy to see the correct values for everything
	#So for the fan, set percentage it is:
	#url: /services/fan/set_percentage
	#data: {set_percentage: 25}
	#(For that example it also works to send that data to /services/fan/set_percentage)
	def _do_post(self, link, data):
		try:
			response = requests.post(self.APIURL+link, headers=self.HEADERS, json=data, timeout=5)
			if response.status_code != 200:
				print("ERROR : Failed to send HA command.")
				print(response.text)
		except Exception as e:
			print(f"Network error calling HA API: {e}")

	def call_api_link(self, link, data):
		# Fire and forget using a background thread so the main loop never blocks
		threading.Thread(target=self._do_post, args=(link, data)).start()
		return True

	def send_webhook(self, payload):
		if not self.webhook_id:
			print("ERROR: No webhook_id configured!")
			return False
		# Sends a payload to a Home Assistant Webhook
		link = f"/webhook/{self.webhook_id}"
		threading.Thread(target=self._do_post, args=(link, payload)).start()
		return True

	def Fan(self, entity_id):
		return Fan(entity_id, self)

	def Scene(self, scene_id):
		return Scene(scene_id, self)