import machine
from app.smqtt import MQTTClient
import app.config as config
import uasyncio as asyncio


class Start:
    def __init__(self, sta, ip, wdt):
        self.FIRM_VERSION = "1.0.4"
        self.IP = ip
        self.DEVICE = ip.split(".")[-1]
        self.station = sta
        self.mqtt = None
        self.rtc = machine.RTC()
        self.RELAY1 = machine.Pin(25, machine.Pin.OUT)
        self.RELAY1.value(1)  # Initialize as OFF
        self.RELAY2 = machine.Pin(26, machine.Pin.OUT)
        self.RELAY2.value(1)  # Initialize as OFF
        self.RELAY3 = machine.Pin(27, machine.Pin.OUT)
        self.RELAY3.value(1)  # Initialize as OFF
        self.RELAY4 = machine.Pin(21, machine.Pin.OUT)
        self.RELAY4.value(1)  # Initialize as OFF

        self.wdt = wdt
        self.wdt.feed()

        # print("......IP:", self.DEVICE)

    def publish(self, msg):
        # print("   publish :" + str(msg))
        self.mqtt.publish("ping", self.DEVICE + "@" + str(msg))

    async def check_msg(self):
        while True:
            # creat task exception
            try:
                self.mqtt.check_msg()
                await asyncio.sleep_ms(3000)
            except Exception as e:
                self.publish("Exception in sub:" + e)
                continue

    def check_station(self):
        if not self.station.isconnected():
            # print("Failed to connect to network. Resetting...")
            machine.reset()
        return True

    async def ping(self):
        while True:
            try:
                self.check_station()
                timestamp = self.rtc.datetime()
                timestamp_str = str(timestamp[4]) + ":" + str(timestamp[5]) + ":" + str(timestamp[6])
                self.publish(timestamp_str)
                self.wdt.feed()
                await asyncio.sleep_ms(30000)
            except Exception as e:
                self.publish("Exception in pub:" + e)
                continue

    def mqtt_connect(self):
        try:
            client_id = machine.unique_id()
            mac_address = "".join("{:02x}".format(byte) for byte in client_id)

            client = MQTTClient(
                mac_address,
                config.mqtt_server,
                1883,
                "acespa",
                config.mqtt_pw,
            )
            client.connect()
            # print("MQTT Connected")
            return client

        except Exception as e:
            # print("MQTT Connection Error: " + str(e))
            return False

    async def main(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.check_msg())
        loop.create_task(self.ping())
        loop.run_forever()

    def run(self):
        self.mqtt = self.mqtt_connect()
        self.mqtt.set_callback(self.subscribe_callback)
        self.mqtt.subscribe("cmd/" + self.DEVICE, 0)
        self.publish("START {}/{}".format(self.IP, self.FIRM_VERSION))
        asyncio.run(self.main())

    def subscribe_callback(self, topic, msg):
        msg = str(msg)
        # print("msg: " + msg)  # msg = b'on'
        msg = msg.replace("b'", "").replace("'", "")

        if msg.startswith("on"):
            relaynum = msg.split("@")
            if len(relaynum) == 1:
                self.publish("answer@on@1")
                self.RELAY1.value(0)  # ON is 0

            elif relaynum[1] == "3":
                self.publish("answer@on@3")
                self.RELAY3.value(0)  # ON is 0

            elif relaynum[1] == "2":
                self.publish("answer@on@2")
                self.RELAY2.value(0)  # ON is 0

            elif relaynum[1] == "1":
                self.publish("answer@on@1")
                self.RELAY1.value(0)  # ON is 0

            elif relaynum[1] == "4":
                self.publish("answer@on@4")
                self.RELAY4.value(0)  # ON is 0

        if msg.startswith("off"):
            relaynum = msg.split("@")
            if len(relaynum) == 1:
                self.publish("answer@off@1")
                self.RELAY1.value(1)  # OFF is 1

            elif relaynum[1] == "3":
                self.publish("answer@off@3")
                self.RELAY3.value(1)  # OFF is 1

            elif relaynum[1] == "2":
                self.publish("answer@off@2")
                self.RELAY2.value(1)  # OFF is 1

            elif relaynum[1] == "1":
                self.publish("answer@off@1")
                self.RELAY1.value(1)  # OFF is 1

            elif relaynum[1] == "4":
                self.publish("answer@off@4")
                self.RELAY4.value(1)  # OFF is 1
