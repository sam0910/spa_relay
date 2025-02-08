import machine
from app.smqtt import MQTTClient
import app.config as config
import uasyncio as asyncio
import time


class Start:
    def __init__(self, sta, ip, wdt, sta_name="ACESPA"):
        self.FIRM_VERSION = "2.0.3"
        self.FIRM_NOTE = "25,26,27,21,18,5,17,16,22,23,1,3,19,15,13,14"
        self.IP = ip
        self.DEVICE = ip.split(".")[-1]
        self.STA_NAME = sta_name
        self.station = sta
        self.mqtt = None
        self.rtc = machine.RTC()
        self.pins = [25, 26, 27, 21, 18, 5, 17, 16, 22, 23, 1, 3, 19, 15, 13, 14]
        self.READS = []
        self.RELAYS = []
        self.READS_STATUS = []

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
                await asyncio.sleep_ms(1000)
            except Exception as e:
                print("Exception in check_msg:" + str(e))
                time.sleep(20)
                machine.reset()
                continue

    def check_station(self):
        if not self.station.isconnected():
            # print("Failed to connect to network. Resetting...")
            time.sleep(20)
            machine.reset()
        return True

    async def ping(self):
        while True:
            try:
                self.check_station()
                timestamp = self.rtc.datetime()
                timestamp_str = str(timestamp[4]) + ":" + str(timestamp[5]) + ":" + str(timestamp[6])
                self.publish("AWAKE" + "@" + self.FIRM_VERSION + "@" + timestamp_str)

                await asyncio.sleep_ms(30000)
            except Exception as e:
                self.publish("Exception in pub:" + str(e))
                continue

    def mqtt_connect(self):
        try:
            print("Connecting to MQTT")
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
            print("MQTT Connected")
            return client

        except Exception as e:
            print("MQTT Connection Error: " + str(e))
            time.sleep(20)
            machine.reset()
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
        self.mqtt.subscribe("ping")
        self.publish("START {}@{}@{}@{}".format(self.IP, self.FIRM_VERSION, self.FIRM_NOTE, self.STA_NAME))

        for pin in self.pins:
            try:
                mpin = machine.Pin(pin, machine.Pin.OUT)
                mpin.value(1)
                self.RELAYS.append(mpin)
            except Exception as e:
                mpin = machine.Pin(0, machine.Pin.OUT)
                mpin.value(1)
                self.RELAYS.append(mpin)
                self.publish("PIN_INIT_ERROR: " + str(e))

        reads_pins = [32, 34, 35]
        for pin in reads_pins:
            try:
                mpin = machine.Pin(pin, machine.Pin.IN)
                self.READS.append(mpin)
                self.READS_STATUS.append(mpin.value())
            except Exception as e:
                mpin = machine.Pin(36, machine.Pin.IN)
                self.READS.append(mpin)
                self.READS_STATUS.append(0)
                self.publish("PIN_INIT_ERROR: " + str(e))

        asyncio.run(self.main())

    def check_reads(self):
        i = 0
        for read in self.READS:
            value = read.value()
            self.publish("READ@{}@{}".format(i, value))
            self.READS_STATUS[i] = value
            i += 1

    def subscribe_callback(self, topic, msg):
        msg = str(msg)
        topic = str(topic)
        msg = msg.replace("b'", "").replace("'", "")
        topic = topic.replace("b'", "").replace("'", "")
        msg = msg.lower()
        if topic == "ping":
            self.wdt.feed()
            return

        print(topic, msg)  # msg = b'on'
        # msg format: on@1@sleep@10@off@2@sleep@10@off@3....
        # msg format: on relay 1, sleep 10 sec, off relay 2, sleep 10 sec, off relay 3
        print("COMMAND RECEIVED: " + msg)

        commands = msg.split("@")
        i = 0
        try:
            while i < len(commands):
                if commands[i] == "reboot":
                    self.publish("REBOOT")
                    time.sleep(1)
                    machine.reset()

                elif commands[i] == "read":
                    self.publish("READ")
                    self.check_reads()

                elif commands[i] == "on":
                    if str(commands[i + 1]) == "all":
                        self.publish("ON(0)|ALL")
                        for relay in self.RELAYS:
                            relay.value(0)
                        i += 2
                        continue
                    relay = int(commands[i + 1]) - 1
                    self.publish("ON(0)|{}".format(commands[i + 1]))
                    self.RELAYS[relay].value(0)  # ON is 0
                    i += 2
                elif commands[i] == "off":
                    if str(commands[i + 1]) == "all":
                        self.publish("OFF(1)|ALL")
                        for relay in self.RELAYS:
                            relay.value(1)
                        i += 2
                        continue

                    relay = int(commands[i + 1]) - 1
                    self.RELAYS[relay].value(1)  # OFF is 1
                    self.publish("OFF(1)|{}".format(commands[i + 1]))
                    i += 2
                elif commands[i] == "sleep":
                    duration = int(commands[i + 1])
                    self.publish("SLEEP_MS|{}".format(commands[i + 1]))
                    time.sleep_ms(duration)
                    i += 2
                else:
                    i += 1

            self.publish(f"{msg}|DONE")
        except Exception as e:
            self.publish(f"ERROR_REBOOT: {msg} {e}")
            print("Exception in command: ", e)
            for relay in self.RELAYS:
                relay.value(1)
            machine.reset()
            return
