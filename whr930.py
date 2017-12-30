#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Interface with a StorkAir WHR930

Publish every 10 seconds the status on a MQTT topic
Listen on MQTT topic for commands to set the ventilation level
"""
import paho.mqtt.client as mqtt
import time
import serial

def debug_msg(message):
    if debug == True:
        print '{0} DEBUG: {1}'.format(time.strftime("%d-%m-%Y %H:%M:%S", time.gmtime()), message)

def warning_msg(message):
    print '{0} WARNING: {1}'.format(time.strftime("%d-%m-%Y %H:%M:%S", time.gmtime()), message)

def info_msg(message):
    print '{0} INFO: {1}'.format(time.strftime("%d-%m-%Y %H:%M:%S", time.gmtime()), message)

def on_message(client, userdata, message):
    if message.topic == 'house/2/attic/wtw/set_ventilation_level':
        if int(message.payload) >= 0 and int(message.payload) <= 3:
            set_ventilation_level(message.payload)
        else:
            warning_msg('Received a message on topic {0} with a wrong payload: {1}'.format(message.topic, message.payload))
    else:
        debug_msg("message received: topic: {0}, payload: {1}, userdata: {2}".format(message.topic, message.payload, userdata))

def publish_message(msg, mqtt_path):                                                                      
    mqttc.publish(mqtt_path, payload=msg, qos=0, retain=False)
    time.sleep(0.1)
    debug_msg('published message {0} on topic {1} at {2}'.format(msg, mqtt_path, time.asctime(time.localtime(time.time()))))

def serial_command(cmd):
    data = []
    ser.write(cmd)
    time.sleep(1)

    while ser.inWaiting() > 0:
        data.append(ser.read(1).encode('hex'))

    if len(data) > 0:
        return data
    else:
        return None

def set_ventilation_level(nr):
    info_msg('Setting ventilation to {0}'.format(nr))

    if nr == '0':
        ser.write("\x07\xF0\x00\x99\x01\x01\x48\x07\x0F")
    elif nr == '1':
        ser.write("\x07\xF0\x00\x99\x01\x02\x49\x07\x0F")
    elif nr == '2':
        ser.write("\x07\xF0\x00\x99\x01\x03\x4A\x07\x0F")
    elif nr == '3':
        ser.write("\x07\xF0\x00\x99\x01\x04\x4B\x07\x0F")

def get_temp():
    data = serial_command("\x07\xF0\x00\x0F\x00\xBC\x07\x0F")

    if data == None:
        warning_msg('get_temp function could not get serial data')
    else:
        OutsideAirTemp = int(data[7], 16) / 2.0 - 20
        SupplyAirTemp = int(data[8], 16) / 2.0 - 20
        ReturnAirTemp = int(data[9], 16) / 2.0 - 20
        ExhaustAirTemp = int(data[10], 16) / 2.0 - 20

        publish_message(msg=OutsideAirTemp, mqtt_path='house/2/attic/wtw/outside_air_temp')
        publish_message(msg=SupplyAirTemp, mqtt_path='house/2/attic/wtw/supply_air_temp')
        publish_message(msg=ReturnAirTemp, mqtt_path='house/2/attic/wtw/return_air_temp')
        publish_message(msg=ExhaustAirTemp, mqtt_path='house/2/attic/wtw/exhaust_air_temp')

        debug_msg('OutsideAirTemp: {0}, SupplyAirTemp: {1}, ReturnAirTemp: {2}, ExhaustAirTemp: {3}'.format(OutsideAirTemp, SupplyAirTemp, ReturnAirTemp, ExhaustAirTemp))

def get_fan_status():
    data = serial_command("\x07\xF0\x00\xCD\x00\x7A\x07\x0F")

    if data == None:
        warning_msg('get_fan_status function could not get serial data')
    else:
        ReturnAirLevel = int(data[13], 16)
        SupplyAirLevel = int(data[14], 16)
        FanLevel = int(data[15], 16) - 1

        publish_message(msg=FanLevel, mqtt_path='house/2/attic/wtw/ventilation_level')
        debug_msg('ReturnAirLevel: {}, SupplyAirLevel: {}, FanLevel: {}'.format(ReturnAirLevel, SupplyAirLevel, FanLevel))
        
def recon():
    try:
        mqttc.reconnect()
        info_msg('Successfull reconnected to the MQTT server')
        topic_subscribe()
    except:
        warning_msg('Could not reconnect to the MQTT server. Trying again in 10 seconds')
        time.sleep(10)
        recon()
        
def topic_subscribe():
    try:
        mqttc.subscribe("house/2/attic/wtw/set_ventilation_level", 0)
        info_msg('Successfull subscribed to the MQTT topics')
    except:
        warning_msg('There was an error while subscribing to the MQTT topic(s), trying again in 10 seconds')
        time.sleep(10)
        topic_subscribe()

def on_connect(client, userdata, flags, rc):
    topic_subscribe()
    
def on_disconnect(client, userdata, rc):
    if rc != 0:
        warning_msg('Unexpected disconnection from MQTT, trying to reconnect')
        recon()

### 
# Main
###
debug = False
lock_mqtt_publish = False

# Connect to the MQTT broker
mqttc = mqtt.Client('whr930')
mqttc.username_pw_set(username="myuser",password="mypass")

# Define the mqtt callbacks
mqttc.on_connect = on_connect
mqttc.on_message = on_message
mqttc.on_disconnect = on_disconnect

# Connect to the MQTT server
mqttc.connect('myhost/ip', port=1883, keepalive=45)

# Subcribe to the MQTT topics
#topic_subscribe()

# Open the serial port
ser = serial.Serial(port = '/dev/ttyUSB0', baudrate = 9600, bytesize = serial.EIGHTBITS, parity = serial.PARITY_NONE, stopbits = serial.STOPBITS_ONE)

mqttc.loop_start()
while True:
    try:
        if lock_mqtt_publish == False:
            get_temp()
            get_fan_status()

        time.sleep(10)
        pass
    except KeyboardInterrupt:
        mqttc.loop_stop()
        ser.close()
        break
    
# End of program