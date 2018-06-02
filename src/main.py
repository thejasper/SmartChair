from smartchair import *
        
chair = SmartChair('JASD')

rangeFinder = HCSR04(trigger_pin=2, echo_pin=5)
chairSensorsInterface = ChairSensorsInterface(chair, rangeFinder)

print('Initialising visualiser TFT')
smartChairVisualiserTFT = SmartChairVisualiserTFT(chair)

print('Initialising reporter Hass.io')
smartChairReporterHassio = SmartChairReporterHassio(chair, '192.168.0.2')

print('Initialising reporter ThingSpeak')
smartChairReporterThingSpeak = SmartChairReporterThingSpeak(chair)
