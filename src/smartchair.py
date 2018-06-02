from hcsr04 import HCSR04
from machine import Timer, RTC
import m5stack
import display
from umqtt.robust import MQTTClient
from myconfig import *

class SmartChair:
    def __init__(self, owner):
        self.owner = owner
        self.occupied = False
        self.__observers = []

    def set_occupied(self, occupied):
        if occupied == self.occupied:
            return            
        self.occupied = occupied
        self.notify_occupied_changed()

    def register_observer(self, observer):
        self.__observers.append(observer)

    def notify_occupied_changed(self):
        for observer in self.__observers:
            observer.occupied_changed(self.occupied)
    

class ChairSensorsInterface:

    DISTANCE_THRESHOLD_OCCUPIED_CM = 30
    
    def __init__(self, chair, rangeFinder):
        self.chair = chair
        self.rangeFinder = rangeFinder
        self.timer = Timer(0)
        self.timer.init(period=1000, mode=Timer.PERIODIC, callback=self.on_timer_tick)

    def on_timer_tick(self, timer):
        try:
            distance = self.rangeFinder.distance_cm()            
            self.chair.set_occupied(distance > 5 and distance < self.DISTANCE_THRESHOLD_OCCUPIED_CM)
            print('Measured distance: ' + str(distance) + 'cm')
        except OSError as ex:
            print('ERROR getting distance:', ex)


class SmartChairVisualiserTFT:
    def __init__(self, chair):
        self.chair = chair
        self.chair.register_observer(self)
        self.tft = display.TFT()
        self.tft.init(self.tft.M5STACK, width=240, height=320, rst_pin=33, backl_pin=32, miso=19, mosi=23, clk=18, cs=14, dc=27, bgr=True, backl_on=1)
        self.tft.font(self.tft.FONT_DejaVu18, transparent = False)
        self.display_header(self.chair.owner)
        self.occupied_changed(self.chair.occupied)

    def display_header(self, text):
        maxx, maxy = self.tft.screensize()
        self.tft.clear()
        self.tft.font(self.tft.FONT_DejaVu18, transparent = False)
        _,miny = self.tft.fontSize()
        miny += 5
        self.tft.rect(0, 0, maxx-1, miny-1, self.tft.OLIVE, self.tft.DARKGREY)
        self.tft.text(self.tft.CENTER, 2, text, self.tft.CYAN, transparent=True)
        self.tft.setwin(0, miny, maxx, maxy)

    def occupied_changed(self, occupied):
        if occupied:
            self.tft.text(0, 30, 'Seat occupied!    ')
        else:
            self.tft.text(0, 30, 'Hello, take a seat')


class SmartChairReporterHassio:
    def __init__(self, chair, host):
        self.chair = chair
        self.chair.register_observer(self)
        self.client = MQTTClient(client_id='SmartChair', 
                                 server=host, 
                                 user=hassio_mqtt_user, 
                                 password=hassio_mqtt_pwd, 
                                 port = 1883,
                                 ssl = False)
        status = self.client.connect()
        if status != 0:
            print('Could not connect to MQTT broker')

    def occupied_changed(self, occupied):
        payload = 'occupied' if occupied else 'not_occupied'
        self.client.publish('home/firstfloor/desk/smartchair', bytes(payload, 'utf-8')) 


class SmartChairReporterThingSpeak:
    def __init__(self, chair):
        self.chair = chair
        self.client = MQTTClient(client_id='SmartChair', 
                                 server='mqtt.thingspeak.com', 
                                 user=thingspeak_mqtt_user, 
                                 password=thingspeak_mqtt_pwd, 
                                 port = 1883,
                                 ssl = False)
        status = self.client.connect()
        if status != 0:
            print('Could not connect to MQTT broker')
        self.timer = Timer(1)
        self.timer.init(period=1000*60, mode=Timer.PERIODIC, callback=self.on_timer_tick)

    def on_timer_tick(self, timer):
        credentials = bytes("channels/{:s}/publish/{:s}".format(thingspeak_channel_id, thingspeak_channel_api_key), 'utf-8')  
        payload = 'field1=' + ('1' if self.chair.occupied else '0') + '\n'
        self.client.publish(credentials, bytes(payload, 'utf-8') ) 
        print('thingspeak publish')
        
