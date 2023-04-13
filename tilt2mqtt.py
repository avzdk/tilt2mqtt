#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#Last Modified: 2022/02/02 10:23:05
import blescan
import logging
import logging.handlers
import configparser
import requests
import sys
import os
import json
import argparse
import datetime
import time
import uuid
import bluetooth._bluetooth as bluez

conf = configparser.ConfigParser()
conf.read(['tilt2mqtt.ini','tilt2mqtt_local.ini'])

log = logging.getLogger(__name__)
logging.basicConfig(
    level=conf["LOG"]["LEVEL"],
    format="%(levelname)s %(module)s.%(funcName)s %(message)s",
)
log.info(f"Starting service loglevel={conf['LOG']['LEVEL']} ")



scriptname=os.path.basename(__file__)

import paho.mqtt.client as mqtt
mqtt_client = mqtt.Client(scriptname)

INTERVAL = int(conf["TILT"]["Interval"])
log.info(f"Checking every {INTERVAL} second")





class lineCalibration():

    def __init__(self,p1,p2):
        self.p1=p1
        self.p2=p2
        self.x1, self.y1 = p1
        self.x2, self.y2 = p2
    
    @property
    def a(self):
        return(self.y2-self.y1)/(self.x2-self.x1)
    
    @property
    def b(self):
        return self.y1 - self.a*self.x1

    def y(self,x):
        return (self.b+self.a*x)


class TiltMonitor():

	TILTS = {
		'a495bb10c5b14b44b5121370f02d74de': 'red',
		'a495bb20c5b14b44b5121370f02d74de': 'green',
		'a495bb30c5b14b44b5121370f02d74de': 'black',
		'a495bb40c5b14b44b5121370f02d74de': 'purple',
		'a495bb50c5b14b44b5121370f02d74de': 'orange',
		'a495bb60c5b14b44b5121370f02d74de': 'blue',
		'a495bb70c5b14b44b5121370f02d74de': 'yellow',
		'a495bb80c5b14b44b5121370f02d74de': 'pink',
	}

	
	def __init__(self,pause,callback):
		
		self.pause = pause
		self.callback=callback
		log.info(f"Retrieving data every {pause} seconds")

	def distinct(self,objects):
		seen = set()
		unique = []
		for obj in objects:
			if obj['uuid'] not in seen:
				unique.append(obj)
				seen.add(obj['uuid'])
		return unique

	def to_celsius(self,fahrenheit):
		return round((fahrenheit - 32.0) / 1.8, 2)

	def calibrate_SG(self,sg,tilt):
		#Dette bør flyttes til .ini
		# dette er formentlig orange
		#1001 -> 999 målt 1001 er 999 (ved 16 grader)
		#1010 -> 1010 målt med alc 1010 er 1010
		#1072 -> 1074 er målt refractometer 1074 
		if tilt=="orange": 
			lc=lineCalibration((1000,1000),(1072,1074))
			return lc.y(sg)
		if tilt=="purple": 
			#997 -> 1000 målt 998 burde være 1000 
			# kun en værdi indtil videre
			lc=lineCalibration((1000,1000),(1074,1074))
			return lc.y(sg)

	def calibrate_Tc(self,t,tilt):
			#Dette bør flyttes til .ini
			#Kalibrering af celcius
			# dette er formentlig orange
			#målt 18.33 er 18.0
			#målt 21.67 er 21.5
			#målt 16.1 er 16.0
		if tilt=="orange": 
			return t-0.3	
		if tilt=="purple": 
			#malt 20.8 burde være 20.0
			# kun en værdi så antager det er forskydning
			lc=lineCalibration((20.8,20),(21.8,21))
			return lc.y(t)

	def run(self):		
		self.dev_id = 0

		try:
			self.sock = bluez.hci_open_dev(self.dev_id)
		
		except:
			log.error('error accessing bluetooth device...')
			sys.exit(1)
		blescan.hci_le_set_scan_parameters(self.sock)
		blescan.hci_enable_le_scan(self.sock)

		while True:
				
				tilt_found=False
				log.debug("check tilts for data")
				
				a=blescan.parse_events(self.sock, 100)
				
				beacons = self.distinct(a)
				
				for beacon in beacons:
					
					if beacon['uuid'] in self.TILTS.keys():
						tilt_found=True
						data ={
							'tilt': self.TILTS[beacon['uuid']],
							'time': str(datetime.datetime.now()),
							'temperature': self.to_celsius(beacon['major']),
							'temperature_cal': self.calibrate_Tc( self.to_celsius(beacon['major']),self.TILTS[beacon['uuid']]),
							'sg': beacon['minor'],
							'sg_cal': self.calibrate_SG(beacon['minor'],self.TILTS[beacon['uuid']]),
							'measurementID' : str(uuid.uuid4())
						}
						log.debug(data)		
						self.callback(data)
				if not tilt_found: log.warning("Ingen tilt fundet")
				time.sleep(self.pause)

class BFproxy:
    def __init__(self,url):
        self.url=url
        
    def postdata(self,name,sg,t):
        if sg >1.2 : log.error("SG is to big. should be < 1,2")
        data={"name": name, "temp": t,"temp_unit": "C", "gravity": sg,"gravity_unit": "G"}
        r = requests.post(self.url, data).json()
        log.debug(f"{data}  -> {r}")
        if r['result']=='ignored':
            log.warning("Data ignored")
        return r		

def tiltCallback(data):
	data['msg_uuid']=str(uuid.uuid4())
	data['time_send']=str(datetime.datetime.now())	
	mqtt_client.connect(conf['MQTT']['Ip'])		
	response=mqtt_client.publish(conf['MQTT']['channel']+"/"+data['tilt'],json.dumps(data),1,True)
	log.debug(f"Succes: {response.rc}" )

	mqtt_client.disconnect()

	bf=BFproxy(conf["BREWFATHER"]["LoggingURL"])
	r=bf.postdata(data['tilt'],data['sg_cal']/1000,data['temperature_cal'])
	


		
		
def main():
	t = TiltMonitor(INTERVAL,tiltCallback)
	t.run()

if __name__ == "__main__":
    main()

