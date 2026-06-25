# 4D Theater Script
A script that recreates a 4D theater experience by controlling Home Assistant devices coupled with the playback of a movie using MPC-HC.

## Configuration
Set FAN_ENTITY_ID to the entity ID from your home assistant setup.
Set your Home Assistant Token & other settings.
Set your MPC-HC variables page URL.

## Movie setup
For now it only reads commands.txt to send fan commands. Make sure it is in the same directory as the script. If copied from HTFanControl the top headers should be removed so it's commands line for line.

## Fan Instructions
Instructions for the fan are based on [HTFanControl](https://github.com/nicko88/HTFanControl)
Community made tracks for the fan can be found there to be copied and used in this script. 
