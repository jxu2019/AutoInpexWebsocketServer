from websocket_server import WebsocketServer
from datetime import datetime
from picamera import PiCamera
import threading
from streaming import *
import os
import random
import string
import platform
import cloudinary
from cloudinary.uploader import upload
from cloudinary.utils import cloudinary_url
import json
import websocket
from threading import Timer, Thread, Event
import uuid


def writeLog(message):
    file = open("/home/pi/log.log", "a")
    now = datetime.now()
    file.write(str(now) + " " + message + "\n")
    file.flush()
    file.close()


def setHostname(newhostname):
    try:
        with open('/etc/hosts', 'r') as file:
            data = file.readlines()
        data[5] = '127.0.1.1       ' + newhostname
        with open('temp.txt', 'w') as file:
            file.writelines(data)
        os.system('sudo mv temp.txt /etc/hosts')
        with open('/etc/hostname', 'r') as file:
            data = file.readlines()
        data[0] = newhostname
        with open('temp.txt', 'w') as file:
            file.writelines(data)
        os.system('sudo mv temp.txt /etc/hostname')
    except Exception as e:
        print(str(e))
        writeLog(str(e))
        return ""


def get_ip_address():
    ip_address = ''
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_address = s.getsockname()[0]
    s.close()
    return ip_address


def readData():
    file = open("/home/pi/AutoInspex_Config.txt", "r")
    data = file.read()
    file.close()
    uname = platform.uname()
    data = data + "IP:" + get_ip_address() + "\n"
    data = data + "hostname:" + socket.gethostname() + "\n"
    data = data + ":" + platform.platform() + "\n"
    return data


def readJsonData():
    try:
        file = open("/home/pi/AutoInspex_Config.txt", "r")
        configdata = file.read()
        file.close()
        arrayObj = configdata.split("\n")
        for line in arrayObj:
            lineArray = line.split(":")
            if(lineArray[0] == "HousingID"):
                HousingID = lineArray[1]
            elif(lineArray[0] == "SerialNumber"):
                SerialNumber = lineArray[1]
            elif(lineArray[0] == "LensID"):
                LensID = lineArray[1]
            elif(lineArray[0] == "SensorID"):
                SensorID = lineArray[1]
            elif(lineArray[0] == "AutoInspexID"):
                AutoInspexID = lineArray[1]
            elif(lineArray[0] == "CameraPosition"):
                CameraPosition = lineArray[1]
        retData = {"Status": "Active","HousingID": HousingID, "SerialNumber": SerialNumber, "LensID": LensID, "SensorID": SensorID, "RingPosition": CameraPosition +
                   "", "AutoInspexID": AutoInspexID, "IPAddress": get_ip_address(), "PiOSVersion": platform.platform(), "PiVersion": "PI 4", "OS_ID": "1"}
        print(retData)
        retJson = json.dumps(retData)
        writeLog(retJson)
        return retJson
    except Exception as e:
        print(str(e))
        writeLog(str(e))
        return ""


def new_client(client, server):
    writeLog("New client connected and was given id %d" % client['id'])

# Called for every client disconnecting


def client_left(client, server):
    writeLog("Client(%d) disconnected" % client['id'])


def upload_file(file_to_upload, publicID, folderName):
    cloudinary.config(cloud_name="carpixstaging", api_key="562496914617253",
                      api_secret="lvqpgDrvwO9OSiTwrjvhr8ozOI4")
    if file_to_upload:
        upload_result = upload(file_to_upload, folder=folderName, public_id=publicID.replace(
            ".jpg", ""), unique_filename=True, overwrite=True)
        thumbnail_url1, options = cloudinary_url(
            upload_result['public_id'], format="jpg")
        return thumbnail_url1


# Called when a client sends a message
camera = PiCamera()
output = StreamingOutput()


def message_received(client, server, message):
    try:
        print(message)
        writeLog(str(message))
        data = json.loads(str(message))
        file = open("/home/pi/AutoInspex_Config.txt", "r")
        configdata = file.read()
        file.close()
        arrayObj = configdata.split("\n")
        for line in arrayObj:
            lineArray = line.split(":")
            if(lineArray[0] == "HousingID"):
                HousingID = lineArray[1]
            elif(lineArray[0] == "SerialNumber"):
                SerialNumber = lineArray[1]
            elif(lineArray[0] == "IP"):
                IP = lineArray[1]
            elif(lineArray[0] == "AutoInspexID"):
                AutoInspexID = lineArray[1]
                print("AutoInspexID:"+AutoInspexID)
            elif(lineArray[0] == "CameraPosition"):
                CameraPosition = lineArray[1]
                print("CameraPosition:"+CameraPosition)

        if len(data["vinCode"]) > 0 and data["autoInspexID"] == AutoInspexID:
            try:
                camera.stop_recording()
            except Exception as e:
                print(str(e))
                writeLog(str(e))

            camera.resolution = (1024, 786)

            imageFileName = AutoInspexID+"." + \
                data["vinCode"]+"."+CameraPosition + '.jpg'
            camera.capture(imageFileName, use_video_port=True)
            print("Snapshot is taken for:" + imageFileName)

            folderName = data["serviceType"]+"-"+data["sellingMethod"]+"-"+data["vinCode"] + \
                "-"+data["vehicleId"]+"-"+data["imageType"] + \
                "-"+str(uuid.uuid1()).replace("-", "")
            url = upload_file(imageFileName, imageFileName, folderName)
            print("url:" + url)

            retData = {"vinCode": data["vinCode"], "vehicleId": data["vehicleId"], "autoInspexID": data["autoInspexID"],
                       "uuid": data["uuid"], "sequenceNo": CameraPosition+"", "inspexIQConnectionId": data["inspexIQConnectionId"], "image_url": url}
            retJson = json.dumps(retData)
            writeLog(retJson)

            print(retJson)
            server.send_message(client, retJson)
            if os.path.exists(imageFileName):
                os.remove(imageFileName)
            try:
                camera.resolution = (400, 300)
                camera.framerate = 10
                camera.start_recording(output, format='mjpeg')
            except Exception as e:
                print(str(e))
                writeLog(str(e))
        else:
            retData = {"vinCode": data["vinCode"], "vehicleId": data["vehicleId"], "autoInspexID": data["autoInspexID"], "uuid": data["uuid"], "sequenceNo": CameraPosition,
                       "inspexIQConnectionId": data["inspexIQConnectionId"], "image_url": "", "error": "AutoInspexID does not match with configuraiton"+AutoInspexID}
            retJson = json.dumps(retData)
            server.send_message(client, retJson)
            writeLog(retJson)
            print(retJson)
    except PiCameraNotRecording as e:
        print(str(e))
        print("Rebooting....")
        os.system("sudo reboot")
    except Exception as e:
        os.system("sudo pm2 restart all")
        print(str(e))
        writeLog(str(e))


class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            ip_address = ''
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
            s.close()
            content = PAGE.replace("{IP}",  ip_address)
            print(content)
            content = content.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header(
                'Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()


def startStreaming():
    try:
        camera.resolution = (400, 300)
        camera.framerate = 10
        camera.start_recording(output, format='mjpeg')
        address = ('', 8000)
        httpserver = StreamingServer(address, StreamingHandler)
        httpserver.serve_forever()
    except Exception as e:
        os.system("sudo pm2 delete all")
        os.system("sudo pm2 start /home/pi/AutoInpexWebsocketServer/server.py --interpreter python3 -f ")
        print(str(e))
        writeLog(str(e))
    finally:
        camera.stop_recording()


statusData = ""


def SendPIStatus():
    try:
        websocket.enableTrace(False)
        global statusData
        if statusData == "":
            statusData = readJsonData()
        ws = websocket.create_connection("ws://192.168.0.11:6001")
        ws.send(statusData)
        ws.close()
        os.system("sudo free -h && sudo sysctl -w vm.drop_caches=3 && sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches && free -h")
    except Exception as e:
        print(str(e))
        writeLog(str(e))


class perpetualTimer():
    def __init__(self, t, hFunction):
        self.t = t
        self.hFunction = hFunction
        self.thread = Timer(self.t, self.handle_function)

    def handle_function(self):
        self.hFunction()
        self.thread = Timer(self.t, self.handle_function)
        self.thread.start()

    def start(self):
        self.thread.start()

    def cancel(self):
        self.thread.cancel()


if __name__ == "__main__":

    tStreaming = threading.Thread(target=startStreaming)
    hostname = ''.join(random.SystemRandom().choice(
        string.ascii_letters + string.digits) for _ in range(10))
    writeLog("hostname: "+hostname)

    if hostname == "raspberrypi":
        writeLog('reset hostname to:'+hostname)
        setHostname(hostname)
    writeLog('starting websocket sever at port 5001...')

    tSendStatus = perpetualTimer(60*2, SendPIStatus)
    PORT: int = 5001
    server = WebsocketServer(PORT)
    server.set_fn_new_client(new_client)
    server.set_fn_client_left(client_left)
    server.set_fn_message_received(message_received)
    writeLog("The server is started.")
    tStreaming.start()
    tSendStatus.start()
    server.run_forever()
