import machine
from smqtt import MQTTClient
import app.secrets as secrets
import uasyncio as asyncio


class Start:
    def __init__(self, sta, ip, wdt):
        self.DEVICE = ip.replace(".", "")
        self.station = sta
        self.mqtt = None
        self.rtc = machine.RTC()
        self.RELAY1 = machine.Pin(25, machine.Pin.OUT)
        self.RELAY1.value(0)
        self.RELAY2 = machine.Pin(27, machine.Pin.OUT)
        self.RELAY2.value(0)
        self.wdt = wdt
        self.wdt.feed()

        print("......IP:", self.DEVICE)

    def publish(self, msg):
        print("   publish :" + str(msg))
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
            print("Failed to connect to network. Resetting...")
            machine.reset()
        return True

    async def ping(self):
        while True:
            try:
                self.check_station()

                timestamp = self.rtc.datetime()
                timestamp_str = (
                    str(timestamp[4])
                    + ":"
                    + str(timestamp[5])
                    + ":"
                    + str(timestamp[6])
                )
                self.publish(timestamp_str)
                self.wdt.feed()
                await asyncio.sleep_ms(10000)
            except Exception as e:
                self.publish("Exception in pub:" + e)
                continue

    def mqtt_connect(self):
        try:
            client_id = machine.unique_id()
            mac_address = "".join("{:02x}".format(byte) for byte in client_id)

            client = MQTTClient(
                mac_address,
                secrets.mqtt_server,
                1883,
                "acespa",
                secrets.mqtt_pw,
            )
            client.connect()
            print("MQTT Connected")
            return client

        except Exception as e:
            print("MQTT Connection Error: " + str(e))
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
        self.publish("start")
        asyncio.run(self.main())

    def subscribe_callback(self, topic, msg):
        msg = str(msg)
        print("msg: " + msg)  # msg = b'on'
        msg = msg.replace("b'", "").replace("'", "")

        if msg.startswith("on"):
            relaynum = msg.split("@")
            if len(relaynum) == 1:
                self.publish("answer@on@1")
                self.RELAY1.value(1)

            elif relaynum[1] == "2":
                self.publish("answer@on@2")
                self.RELAY2.value(1)

            elif relaynum[1] == "1":
                self.publish("answer@on@1")
                self.RELAY1.value(1)

        if msg.startswith("off"):
            relaynum = msg.split("@")
            if len(relaynum) == 1:
                self.publish("answer@off@1")
                self.RELAY1.value(0)

            elif relaynum[1] == "2":
                self.publish("answer@off@2")
                self.RELAY2.value(0)

            elif relaynum[1] == "1":
                self.publish("answer@off@1")
                self.RELAY1.value(0)
