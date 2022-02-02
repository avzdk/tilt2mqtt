# tilt2mqtt
Reads the Tilt bluetooth hydrometer and send values to MQTT
 
Reads all awailable tilt hydrometers and send data to MQTT.
Runs perfect on a Raspberry Pi Zero W.

Get you tilt form https://tilthydrometer.com/ and keep and eye on your beer fermenting.

#sudo apt-get install libbluetooth-dev
#sudo pip3 install pybluez
#sudo apt-get install python-dev
#https://github.com/atlefren/pytilt
#https://www.reddit.com/r/Homebrewing/comments/ar18wy/tilt_hydrometer_python_code/
#sudo setcap cap_net_raw+eip /usr/bin/python3.7