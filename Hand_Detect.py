import cv2 # import open cv
import mediapipe as mp # import mediapipe
from google.protobuf.json_format import MessageToDict # library to convert protocol buffers message to a dictionary
import time

class HandDetectorMP:
	def __init__(self, mode = False, max_hands = 2, model_complexity = 1, detection_con = 0.5, track_con = 5.0):
		self.mode = mode # toggles between static and tracking modes 
		self.max_hands = max_hands # determiens maximum number of hands to detect and track
		self.model_complexity = model_complexity # parameter influencing accuracy and speed of tracking (computational load)
		self.detection_con = detection_con # Confidence thresholds for initating hand detection 
		self.track_con = track_con  # Confidence thresholds for initating maintaining tracking
		
		self.tip_ids = [4, 8, 12, 16, 20] # isolating finger tips, thumb tip to pinky tip respectively
		self.mp_hands = mp.solutions.hands 
		self.hands = self.mp_hands.Hands(self.mode, self.max_hands, self.model_complexity, self.detection_con, self.track_con) # MediaPipe's hand module
		self.mp_draw = mp.solutions.drawing_utils 
			
	# Process input image for hand detection and landmark extraction 	
	def find_hands(self, img, draw = True): 
		img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) 
		self.results = self.hands.process(img_rgb) # Stores self.hands attributes 
		
		if self.results.multi_hand_landmarks: # checks if multiple hand land marks are present in processed image
			for hand_lms in self.results.multi_hand_landmarks: 
				if draw: # parameter
					self.mp_draw.draw_landmarks(img, hand_lms, self.mp_hands.HAND_CONNECTIONS)  # method for drawing utilities from media pipe to overlay lindmarks/connections on image
		return img # returns processed image with drawn hand landmarks
		
	# Taking image as primary input, along with optional parameters for specifying hand index (hand_no) and boolean flag (draw)
	# indicating whether detected landmarks should be visually highlighted on image.  	
	def find_position(self, img, hand_no = 0, draw = True): # hand_no allows the user to choose which hand's landmarkers to track
		self.lm_list = [] # Empty list to store info about detected landmarks
		
		if self.results.multi_hand_landmarks: # multi hand landmarks check
			selected_hand = self.results.multi_hand_landmarks[hand_no]
			for l_id, lm in enumerate(selected_hand.landmark):
				h, w, c = img.shape
				
				# iterates through each landmark in selected hand to calculate pixel coordinates using cx and cy
				# the landmarks normalized coordinates represented by lm.x and lm.y, ranging between 0 and 1, will represent the position of the landmark within the image   
				cx, cy = int(lm.x * w), int(lm.y * h) 
				self.lm_list.append([l_id, cx, cy]) 
				
				if draw:
					cv2.circle(img, (cx, cy), 10, (200, 100, 200), cv2.FILLED) 
					
		return self.lm_list
		
		
		
	# Method processes an input image with optional perameters, 
	# hand index (hand_no) to specify which hand's landmarks to track 
	# and a boolean flag (draw to determine whether to visually annotate 
	# the detected landmarks. It begins by initializing an empty list 
	# (self.lm_list) to store landmark data and then verifies the 
	# presence of multi-hand landmarks. For selected hand, the method 
	# iterates through each landmark, converting normalized coordinates 
	# into absolute pixel values by multiplying with image's width and 
	# height and rounding these values to nearest int. Computed data, 
	# including landmark IDs and their coresponding pixel position, is 
	# added to self.lm_list. Additionally, if draw is set to True, method 
	# utilizes OpenCV (cv2.circle) to overlay visual markers on the image,
	# thereby offering a customizable visualization of hand landmarks 
	def fingers_up(self):
		fingers = []
		
		if not self.lm_list:
			return[0, 0, 0, 0, 0]
		
	# Thumb logic using temp variables 
		thumb_tip = self.lm_list[self.tip_ids[0]]
		thumb_ip = self.lm_list[self.tip_ids[0]-1]
		if thumb_tip[1] > thumb_ip[1]:
			fingers.append(1)
		else:
			fingers.append(0)			

				
	# Fingers logic
		for id in range(1, 5):
			if self.lm_list[self.tip_ids[id]][2] < self.lm_list[self.tip_ids[id] - 2][2]:
				fingers.append(1)
			else:
				fingers.append(0)
			
		return fingers
		
    # Initialize variables, capture video from webcam, and continuously process frames.
    # Loop utilizes instance of HandDetectorMP class, detects hands and 
    # retrieves landmark positions. Prints coordinates of specific landmark (5th landmark)
    # then calculates and displays frames per second of video feed.
	if __name__ == "__main__":
		p_time = 0 
		cap = cv2.VideoCapture(0)
		detector = HandDetectorMP(detection_con=0.8, track_con=0.5) # Variable for whole HandDetectorMP class
		
		while True:
			ret, img = cap.read()
			if not ret:
				break
			img = detector.find_hand(img)
			lm_list = detector.find_position(img, draw = True)
			
			if lm_list:
				fingers = detector.find_hands()
				cv2.putText(img, f"Fingers: {fingers}", (10, 70),
				cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
				print(lm_list[4])
			c_time = time.time()
			fps = 1 / (c_time - p_time) if (c_time - p_time) != 0 else 0
			p_time = c_time
			
			cv2.putText(img, f"FPS: {int(fps)}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
			cv2.imshow("Hand Detection", img)
			if cv2.waitKey(1) & 0xFF == ord('q'):
				break
			
			cap.release()
			cv2.destroyAllWindows()
		
		
		
		
	
		

		
		
		
		
