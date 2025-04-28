import pygame
import pygame.camera
import os
import uuid
from dotenv import load_dotenv
load_dotenv()
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential
import psycopg2
import RPi.GPIO as GPIO
from time import sleep

GPIO.setmode(GPIO.BOARD)

GPIO.setup(11, GPIO.OUT)
GPIO.setup(13, GPIO.IN)
gate_pin = GPIO.PWM(11, 50)

def capture_image(type="vehicle"):
    """Captures an image using the webcam and saves it."""
    pygame.camera.init()
    cam = None
    
    image_name=uuid.uuid4()
    image_path = None
    if type == "vehicle":
        cam = pygame.camera.Camera("/dev/video0", (640,480))
        image_path = f"images/vehicle_reg_numbers/{image_name}.jpg"
    elif type == "meter":
        cam = pygame.camera.Camera("/dev/video1", (640,480))
#        cam = pygame.camera.Camera("/dev/video2", (640,480))
        image_path = f"images/meter_readings/{image_name}.jpg"
        
    cam.start()
    image = cam.get_image()
    pygame.image.save(image, image_path)
    cam.stop()
    return image_name

def get_vehicle_reg_number(image_path):
    try:
        endpoint = os.environ["VISION_ENDPOINT"]
        key = os.environ["VISION_KEY"]
    except KeyError:
        print("Missing environment variable 'VISION_ENDPOINT' or 'VISION_KEY'")
        exit()

    # Create an Image Analysis client
    client = ImageAnalysisClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key)
    )

    with open(image_path, "rb") as f:
        image_data = f.read()

    result = client.analyze(
        image_data=image_data,
        visual_features=[VisualFeatures.READ]
    )
    print(result)

    vehicle_reg_number=None
    if result.read is not None:
        if len(result.read.blocks) > 0:
            for line in result.read.blocks[0].lines:
                print(f"Line: '{line.text}'")
                vehicle_reg_number=line.text
        else:
            print("No vehicle detected!")
    else:
        print("OCR operation failed or timed out")
        
    return vehicle_reg_number

def get_db_connection():
    try:
        DB_HOST = os.environ["DB_HOST"]
        DB_NAME = os.environ["DB_NAME"]
        DB_PASSWORD = os.environ["DB_PASSWORD"]
        DB_PORT = os.environ["DB_PORT"]
        DB_USER = os.environ["DB_USER"]
        return psycopg2.connect(
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
        )
    except Exception as error:
        print("An exception occured when connectong to the DB: ", error)
        return False
def open_gate():
    gate_pin.start(0)
    gate_pin.ChangeDutyCycle(3)
    sleep(1)
    gate_pin.ChangeDutyCycle(12)
    sleep(1)
    # p.stop()
    gate_pin.stop()
    
def get_vehicle_status(vehicle_reg_number):
    conn = get_db_connection()
    if conn:
        print("DB connected.")
    else:
        print("Unable to connect DB")
    curr = conn.cursor()
    
    curr.execute("SELECT * FROM vehicles WHERE vehicle_no = %s", (vehicle_reg_number,))
    
    data = curr.fetchall()
    if len(data) > 0:
        return True
    return False

def get_meter_reading(image_path):
    try:
        endpoint = os.environ["VISION_ENDPOINT"]
        key = os.environ["VISION_KEY"]
    except KeyError:
        print("Missing environment variable 'VISION_ENDPOINT' or 'VISION_KEY'")
        exit()

    # Create an Image Analysis client
    client = ImageAnalysisClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key)
    )

    with open(image_path, "rb") as f:
        image_data = f.read()

    result = client.analyze(
        image_data=image_data,
        visual_features=[VisualFeatures.READ]
    )

    rupees = None
    litres = None
    if result.read is not None:
        print(result.read.blocks[0].lines)
        rupees = float(result.read.blocks[0].lines[1].text.replace(' ', '')) / 10
        litres = float(result.read.blocks[0].lines[3].text.replace(' ', ''))
        for line in result.read.blocks[0].lines:
            print(f"Line: '{line.text}'")
            vehicle_reg_number=line.text
    else:
        print("OCR operation failed or timed out")
        
    return rupees, litres

def main():
    while True:
        if GPIO.input(13):
            print("Object detected")
            image_name = capture_image("vehicle")
            if image_name is None:
                print("no image name")
            image_path=f"images/vehicle_reg_numbers/{image_name}.jpg"
            vehicle_reg_number=get_vehicle_reg_number(image_path)
            print(vehicle_reg_number)
            vehicle_status=get_vehicle_status(vehicle_reg_number)
            print(vehicle_status)
            if vehicle_status:
                open_gate()
                meter_reading_0_image_name = capture_image("meter")
                meter_reading_0_image_path = f"images/meter_readings/{meter_reading_0_image_name}.jpg"
                amount, litres = get_meter_reading(meter_reading_0_image_path)
                print("amount: ", amount)
                print("litres: ", litres)
            else:
                print("Not a registered vehicle")
        else:
            print("No object")
                
                
if __name__ == "__main__":
    main()



def get_available_camera(index=0):
    pygame.camera.init()
    camlist = pygame.camera.list_cameras()
    if len(camlist) > index:
        return camlist[index]
    else:
        return None


def capture_image(type="vehicle"):
    pygame.camera.init()
    cam = None

    image_name = uuid.uuid4()
    image_path = None

    if type == "vehicle":
        cam_path = get_available_camera(0)  # First working camera
        image_path = f"images/vehicle_reg_numbers/{image_name}.jpg"
    elif type == "meter":
        cam_path = get_available_camera(1)  # Second working camera
        image_path = f"images/meter_readings/{image_name}.jpg"

    if cam_path is None:
        print(f"No camera available for type: {type}")
        return None

    cam = pygame.camera.Camera(cam_path, (640, 480))
    cam.start()
    image = cam.get_image()
    pygame.image.save(image, image_path)
    cam.stop()
    return image_name

    


