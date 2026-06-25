# Python script to communicate with MPC-HC
import requests
from bs4 import BeautifulSoup

class MPCHC:
	def __init__(self, url):
		self.url = url

	# Function to get the current movie time from MPC-HC
	def get_movie_time(self):
		try:
			response = requests.get(self.url)
			if response.status_code == 200:
				soup = BeautifulSoup(response.text, 'html.parser')
				#current_time = soup.find("p", {"id": "positionstring"}).text
				#time_int = int(''.join(filter(str.isdigit, current_time+'000')))
				current_time = soup.find("p", {"id": "position"}).text
				time_int = int(''.join(filter(str.isdigit, current_time)))
				return time_int
		except Exception as e:
			print(f"Error while getting movie time: {str(e)}")
		return 0