#Importing necessary libraries
import cv2  #OpenCV for computer vision tasks
import mediapipe as mp  #Provides pre-trained models for tasks
import paho.mqtt.client as paho #MQTT library
from paho import mqtt

#---------------------------MQTT________________________________
def send_to_MQTT(text):
    # a single publish, this can also be done in loops, etc.
    client.publish("home", payload=text, qos=1)

def on_connect(client, userdata, flags, rc, properties=None):
    print("CONNACK received with code %s." % rc)

def on_publish(client, userdata, mid, properties=None):
    print("mid: " + str(mid))

def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))

def on_message(client, userdata, msg):
    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

# Initialize the MQTT broker
client = paho.Client(client_id="", userdata=None, protocol=paho.MQTTv5)
client.on_connect = on_connect

# enable TLS for secure connection
client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
# set username and password
client.username_pw_set(<MQTT_USERNAME>, <MQTT_PASSWORD>)
# connect to HiveMQ Cloud on port 8883 (default for MQTT)
client.connect(<MQTT_CLUSTER_ID>, 8883)

# setting callbacks, use separate functions like above for better visibility
client.on_subscribe = on_subscribe
client.on_message = on_message
client.on_publish = on_publish

#last sent value
last_sent_value = None
#---------------------------------------------------------------

#Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands()    #Instance of "hands" class from MediaPipe

#Open Webcam
cap = cv2.VideoCapture(0)   #Opens camera and assigns to cap

#Adaptive Learning Parameters
recognition_threshold = 0.050
user_feedback = None

#Loop to continuously capture frames from the webcam
while cap.isOpened():

    #If the frame is successfully read, it continues, otherwise the loop breaks
    ret, frame = cap.read()
    if not ret:
        break

    #Convert BGR to RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    #Process Frame with MediaPipe Hands
    results = hands.process(rgb_frame)

    #Check if Hand Detected
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:

            #Draw Hand Landmarks
            for point in hand_landmarks.landmark:
                height, width, _ = frame.shape
                cx, cy = int(point.x * width), int(point.y * height)
                cv2.circle(frame, (cx, cy), 5, (255, 0, 0), -1)

            #Calculate Distance between Thumb and Index Finger Tips
            thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
            index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]

            distance = ((thumb_tip.x - index_tip.x)**2 + (thumb_tip.y - index_tip.y)**2)**0.5

            #Ensure the threshold stays within a reasonable range
            recognition_threshold = max(0.01, min(0.5, recognition_threshold))

            #Determine Hand Gesture using the updated recognition threshold
            if distance < recognition_threshold:
                hand_gesture = "Closed Fingers"
                x = 0

            elif recognition_threshold < distance < 0.6:
                hand_gesture = "Opened Fingers"
                x = 1

            #MQTT loop start
            client.loop_start()

            current_value = x

            if current_value != last_sent_value:
                send_to_MQTT(x)
                last_sent_value = current_value

            #MQTT loop end
            client.loop_stop()

            #Print Hand Gesture
            print(hand_gesture)

            #Add Gesture Name and Adaptive Learning Information to Frame
            info_text = f"Threshold: {recognition_threshold:.5} | Last Feedback: {user_feedback}"
            cv2.putText(frame, hand_gesture, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, info_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    #user feekback
    key = cv2.waitKey(1)
    if key == ord('1'):
        user_feedback = input("Feedback:")

        # Adapt Recognition Threshold
        if user_feedback == "Correct":
            recognition_threshold -= 0.001
        elif user_feedback == "Incorrect":
            recognition_threshold += 0.001

        print(user_feedback)
        print("Recognition Threshold value updated")
        print("Current Recognition Threshold value : ", recognition_threshold)

    #Display Frame
    cv2.imshow('Hand Gesture Recognition', frame)

    #Break the Loop on 'Esc' Key
    if cv2.waitKey(1) == 27:
        break

#Release Resources
cap.release()
cv2.destroyAllWindows()