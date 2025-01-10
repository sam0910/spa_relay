import time, machine, network, gc, app.secrets as secrets
from app.ota_updater import OTAUpdater


wdt = machine.WDT(timeout=30000)  # enable it with a timeout of 2s
IP = "0.0.0.0"
STA_IF = None


def connet_wifi():
    global IP
    global STA_IF
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print("connecting to network...")
        sta_if.active(True)
        sta_if.connect("ACESPA", "acespa04")
        for _ in range(40):
            if sta_if.isconnected():
                break
            print("Waiting for connection...")
            wdt.feed()
            time.sleep(0.5)
        else:
            print("Failed to connect to network. Resetting...")
            machine.reset()

    print("network config:", sta_if.ifconfig())
    IP = sta_if.ifconfig()[0]
    print("...IP:", IP)
    STA_IF = sta_if
    wdt.feed()


def connectToWifiAndUpdate():
    wdt.feed()
    time.sleep(0.2)
    print("Memory free", gc.mem_free())
    connet_wifi()
    # headers={"Authorization": "token {}".format(secrets.token)},
    otaUpdater = OTAUpdater(
        "https://github.com/sam0910/spa_relay.git", main_dir="app", github_src_dir="src", secrets_file="secrets.py"
    )

    wdt.feed()
    try:
        hasUpdated = otaUpdater.install_update_if_available()
        if hasUpdated:
            machine.reset()
        else:
            del otaUpdater
            gc.collect()
            wdt.feed()
    except Exception as e:
        print("Exception in OTAUpdater:", e)
        machine.reset()


def startApp():
    wdt.feed()
    import app.start

    start = app.start.Start(STA_IF, IP, wdt)
    start.run()


connectToWifiAndUpdate()
startApp()
