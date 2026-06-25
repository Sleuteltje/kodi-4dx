import time
import requests
import re
import sys
from bs4 import BeautifulSoup
from michsclasses import commands_parser
from michsclasses import home_assistant_api
from michsclasses import kodi
import asyncio

# Home Assistant API URL and authentication token
HA_API_URL = "http://192.168.1.153:8123/api"
HA_AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI0YzRlY2Y1YWMyYmE0ZTljYmQ4YzUyNjI0ODk1YmY3NCIsImlhdCI6MTY5NzE2MDIyNCwiZXhwIjoyMDEyNTIwMjI0fQ.ki7z9v6Gj6lsvIOyNOKQGonboqJ8sJjOU2IZrnyaa50"
HA_API_HEADERS = {"Authorization": "Bearer "+HA_AUTH_TOKEN}

# Fan entity ID
FAN_ENTITY_ID = "fan.mi_smart_standing_fan_pro"

#TIME DELAY FOR THE WIND TO ACTUALLY REACH YOU / STOP YOU in milliseconds
FAN_DELAY = -3500


#Set up Devices from Home Assistant
Api = home_assistant_api.HomeAssistantApi(HA_AUTH_TOKEN, HA_API_URL)
Fan = Api.Fan(FAN_ENTITY_ID)

#Set up Kodi
Kodi = kodi.Kodi()


# Function to send a fan command to Home Assistant
async def send_fan_command(command):
	if command == "OFF":
		response = await Fan.turn_off()
	elif command == "ECO":
		response = await Fan.eco_mode()
		#response = await Fan.turn_on(10)
	elif command == "LOW":
		response = await Fan.turn_on(25)
	elif command == "MED":
		response = await Fan.turn_on(50)
	elif command == "HIGH":
		response = await Fan.turn_on(100)
	elif isinstance(command, int):
		response = await Fan.turn_on(command)
	else:
		print("ERROR: Not a valid fan command!")
		return False

	if response.status == 200:
		print(f"Fan command sent: {command}")
		return True

	print("ERROR : Failed to send fan command.")
	print(response.text)
	return False    


def is_movie_skipped(old_current_time, current_time):
	if current_time < old_current_time:
		print("The movie was skipped backwards.. restoring entire commands")
		FanCommands.reset(current_time)
		if FanCommands.get_previous_command():
			asyncio.run(send_fan_command(FanCommands.get_previous_command())) #Do the previous command, because this might be a scene where the previous command is still active
			return True
	return False
	
# Execute the main function
if __name__ == "__main__":
	FanCommands = commands_parser.Commands("commands_legendsofguardians.txt")
	


	mainloop = True
	#commands = parse_commands("commands.txt")
	#nextCommandsToDo = commands
	#previousCommand = {0: "None"}
	#nextCommand = {0: "None"}

	old_current_time = 0
	#current_time = MPCHC.get_movie_time() - FAN_DELAY

	#current_file = Kodi.get_filename()
	#if 'player.Filename' in current_file:
	#	current_filename = current_file['player.Filename']



	print("Fan Commands: ")
	for key, value in FanCommands.commands:
		print(str(key)+" : "+value)


	Kodi.get_file()
	print(result)
	sys.exit(1)
	#main_loop()
	#send_fan_command('HIGH')



	while mainloop:
		#Check which file is playing and reload if needed




		old_current_time = current_time
		#current_time = MPCHC.get_movie_time() - FAN_DELAY
		current_time = Kodi.get_movie_time() - FAN_DELAY

		print("old_current_time: "+str(old_current_time)+" | current_time: "+str(current_time))


		print("Time in normal time: "+formatted_time(current_time))

		print("Previous Command: "+str(FanCommands.get_previous_command()))
		print("Next Command: "+str(FanCommands.get_next_command()))


		if is_movie_skipped(old_current_time, current_time):
			continue #The Movie was skipped backwards

		
		commands_to_execute = FanCommands.commands_to_execute(old_current_time, current_time)
		print("Commands to do: "+str(len(commands_to_execute)))

		for timestamp_to_do, command_to_do in commands_to_execute:
			FanCommands.remove_command(timestamp_to_do)
			FanCommands.set_previous_command({timestamp_to_do : command_to_do})
			asyncio.run(send_fan_command(command_to_do))
				

		time.sleep(0.1)



def formatted_time(milliseconds):
	return "{:02}:{:02}:{:02}:{:03}".format(
	    int((milliseconds / (1000 * 60 * 60)) % 24),  # hours
	    int((milliseconds / (1000 * 60)) % 60),       # minutes
	    int((milliseconds / 1000) % 60),              # seconds
	    int(milliseconds % 1000)                      # milliseconds
	)