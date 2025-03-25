import cv2
import numpy as np
import os
import time
from Hand_Detect import HandDetectorMP
from picamera2 import Picamera2 
from picamera2.devices import Hailo # Using hailo device for hardware-accelerated inference
import AirConfig


# Global drawing parameters
draw_color = AirConfig.default_color # default red
brush_thickness = AirConfig.default_brush_thickness
xp, yp = 0, 0   # previous x, previous y for drawing lines
pressed_keys = [] # buffer for numeric color entry (RGB)

# Track eraser mode
eraser_mode = False

# Hand presence tracking
last_hand_detection_time = time.time()
hand_timeout = AirConfig.hand_timeout  # seconds before clearing canvas when no hand detected

# Flag to show helper visualization - set to False to disable
show_helper = False  

# List to store drawn stroke
strokes = []

# Predefined color options for cycling 
color_options = [
    AirConfig.RED_COLOR,     # Red
    AirConfig.BLUE_COLOR,    # Blue 
    AirConfig.GREEN_COLOR,   # Green
    AirConfig.ERASER_COLOR   # Pink eraser
]

# Load overlays
overlays = {}

for key, filename in AirConfig.overlay_paths.items():
	img_path = os.path.join(AirConfig.folder_path, filename)
	if os.path.exists(img_path):
		img_overlay = cv2.imread(img_path)
		
		if img_overlay is not None:
			if AirConfig.debug_mode:
				print(f"Original size: {img_overlay.shape}")
				
			 # If image is taller than header height crop	
			if img_overlay.shape[0] > AirConfig.HEADER_HEIGHT:
				img_overlay = img_overlay[:AirConfig.HEADER_HEIGHT, :, :]
				if AirConfig.debug_mode:
					print(f"Cropped to header height: {img_overlay.shape}")
					
			# Resize to full width 
			img_overlay = cv2.resize(img_overlay, (AirConfig.CANVAS_WIDTH, AirConfig.HEADER_HEIGHT))
			
			# Store in dictionary
			overlays[key] = img_overlay
					
			if AirConfig.debug_mode:
				print(f"Added '{key}' overlay with shape: {img_overlay.shape}")  
				
		else:
			print(f"ERROR: Could not load image {img_path}")
					
	else:
		print(f"ERROR: File not found: {img_path}")
        
# Set default header
current_overlay_key = "red"
header = overlays.get("red")
if header is None and overlays:
    # Fall back to first available overlay if default not found
    current_overlay_key = next(iter(overlays.keys()))
    header = overlays[current_overlay_key]
    print(f"Default overlay not found, using '{current_overlay_key}' instead")

if not overlays:
    print("WARNING: No overlay images loaded!")
    # Create basic header if no images are available
    basic_header = np.zeros((AirConfig.HEADER_HEIGHT, AirConfig.CANVAS_WIDTH, 3), dtype=np.uint8)
    basic_header[:, :] = (50, 50, 50)  # Dark gray background
    overlays["red"] = basic_header
    header = basic_header
    current_overlay_key = "red"

# Debug info
print(f"Loaded {len(overlays)} overlay images")
if AirConfig.debug_mode:
	for key, overlay in overlays.items():
		print(f"Overlay '{key}' shape: {overlay.shape}")
	
# Initialize hand detector with robust confidence threshold
detector = HandDetectorMP(detection_con = AirConfig.detection_confidence, track_con = AirConfig.tracking_confidence)

picam2 = Picamera2()
main_size = (AirConfig.CANVAS_WIDTH, AirConfig.CANVAS_HEIGHT) # capture at default canvas width and height from config file
video_config = picam2.create_preview_configuration(main={"size": main_size, "format": "RGB888"})
picam2.configure(video_config)
picam2.start()

# Allow detector to start
time.sleep(2)

# Create named window for display
cv2.namedWindow("Canvas", cv2.WINDOW_NORMAL)

# Main loop: constant capture/process frames
while True:
    # Capture frame from camera
    frame = picam2.capture_array()
    if frame is None:
        print("No frame captured")
        continue
    
    # Flip frame for mirror effect     
    frame = cv2.flip(frame, 1)
    
    # Resize to ensure frame is the predetermined canvas width and height
    frame = cv2.resize(frame, (AirConfig.CANVAS_WIDTH, AirConfig.CANVAS_HEIGHT))
    processed_frame = frame.copy()
    
    # Process hand detection on current frame
    processed_frame = detector.find_hands(processed_frame)
    lm_list = detector.find_position(processed_frame, draw=False)
    
    current_time = time.time()
    
    if lm_list:
        # Hand detected, update last detection time
        last_hand_detection_time = time.time()
        
        # Get landmark positions for index (lm8) and middle fingers (lm12)
        x1, y1 = lm_list[8][1:]
        fingers = detector.fingers_up()
        
        # If both index and middle fingers are up, reset drawing and check for header/color selection
        if fingers[1] and fingers[2]:
            xp, yp = 0, 0 # Reset to previous point
            cv2.rectangle(processed_frame, (x1, y1 - 15), (lm_list[12][1], lm_list[12][2] + 25), draw_color, cv2.FILLED)
            
            # Check if finger is in header area
            if y1 < AirConfig.HEADER_HEIGHT:
                # Check which color region finger is touching
                for region in AirConfig.color_regions:
                    x_min, x_max, y_min, y_max, color_name, color_value = region
                    if x_min <= x1 <= x_max and y_min <= y1 <= y_max:
                        if color_name in overlays:
                            header = overlays[color_name]
                            current_overlay_key = color_name
                            draw_color = color_value
                            eraser_mode = (color_name == "eraser")
                            print(f"Changed to {color_name}, color: {color_value}")
                            break
            
            # Check if finger is in brush size control area (right side of screen)
            elif AirConfig.CANVAS_WIDTH-70 <= x1 <= AirConfig.CANVAS_WIDTH-20 and 200 <= y1 <= 320:
                for region in AirConfig.brush_control_regions:
                    x_min, x_max, y_min, y_max, action = region
                    if x_min <= x1 <= x_max and y_min <= y1 <= y_max:
                        if action == "increase" and brush_thickness < 100:
                            brush_thickness += 5
                            print(f"Brush thickness increased to: {brush_thickness}")
                        elif action == "decrease" and brush_thickness > 5:
                            brush_thickness -= 5
                            print(f"Brush thickness decreased to: {brush_thickness}")
                        # Wait a moment to prevent multiple rapid changes
                        time.sleep(0.3)
                            
        # If index finger is up and middle finger is down Draw    
        elif fingers[1] and not fingers[2]:
            # Choose circle size based on eraser mode
            circle_radius = 25 if eraser_mode else 15
            
            # Visual feedback for current position
            if eraser_mode:
                # White circle with border for eraser
                cv2.circle(processed_frame, (x1, y1), circle_radius+2, (0, 0, 0), 2)
                cv2.circle(processed_frame, (x1, y1), circle_radius, (255, 255, 255), cv2.FILLED)
            else:
                cv2.circle(processed_frame, (x1, y1), circle_radius, draw_color, cv2.FILLED)
                
            if xp == 0 and yp == 0:
                # Initialize (no drawing yet)
                xp, yp = x1, y1
            else:
                # Draw if valid previous position
                # Ensures drawing does not start at (0, 0)
                if abs(x1 - xp) + abs(y1 - yp) < 100: # Prevents large jumps in pixels
                    # Only create strokes for non-header area
                    if y1 > AirConfig.HEADER_HEIGHT or yp > AirConfig.HEADER_HEIGHT:
                        if eraser_mode:
                            # Instead of creating special eraser strokes, directly remove
                            # any existing strokes that intersect with this eraser movement
                            eraser_thickness = brush_thickness * AirConfig.eraser_brush_multiplier
                            to_remove = []
                            
                            for idx, existing_stroke in enumerate(strokes):
                                if len(existing_stroke) == 8:
                                    s_x1, s_y1, s_x2, s_y2, s_color, s_thickness, s_time, s_is_eraser = existing_stroke
                                else:
                                    s_x1, s_y1, s_x2, s_y2, s_color, s_thickness, s_time = existing_stroke
                                    s_is_eraser = False
                                
                                # Skip eraser strokes - no need to erase erasers
                                if s_is_eraser:
                                    continue
                                
                                # Calculate distance from line (eraser) to line (stroke)
                                # Simple bounding box collision
                                eraser_margin = eraser_thickness + s_thickness
                                
                                # Current eraser bounding box
                                eraser_min_x = min(xp, x1) - eraser_margin
                                eraser_max_x = max(xp, x1) + eraser_margin
                                eraser_min_y = min(yp, y1) - eraser_margin
                                eraser_max_y = max(yp, y1) + eraser_margin
                                
                                # Stroke bounding box
                                stroke_min_x = min(s_x1, s_x2) - eraser_margin
                                stroke_max_x = max(s_x1, s_x2) + eraser_margin
                                stroke_min_y = min(s_y1, s_y2) - eraser_margin
                                stroke_max_y = max(s_y1, s_y2) + eraser_margin
                                
                                # Check for collision
                                if not (stroke_max_x < eraser_min_x or stroke_min_x > eraser_max_x or 
                                        stroke_max_y < eraser_min_y or stroke_min_y > eraser_max_y):
                                    to_remove.append(idx)
                            
                            # Remove collided strokes in reverse order (to maintain indices)
                            for idx in sorted(to_remove, reverse=True):
                                if idx < len(strokes):
                                    strokes.pop(idx)
                        else:
                            # Normal drawing - add stroke
                            strokes.append((xp, yp, x1, y1, draw_color, brush_thickness, current_time, False))
                xp, yp = x1, y1
        else:
            xp, yp = 0, 0
    
    # No landmarks detected reset drawing to starting point (if applicable)
    else:
        xp, yp = 0, 0
        
        # Check if hand has been absent for more than timeout period
        time_since_last_hand = current_time - last_hand_detection_time
        if time_since_last_hand >= AirConfig.hand_timeout and len(strokes) > 0:
            # Clear canvas after timeout
            strokes = []
            print(f"Canvas cleared after {time_since_last_hand:.1f} seconds with no hand detected")
    
    # Create new canvas and redraw strokes that have not expired
    img_canvas = np.zeros((AirConfig.CANVAS_HEIGHT, AirConfig.CANVAS_WIDTH, 3), np.uint8)
    
    # First pass: identify eraser strokes
    eraser_strokes = []
    for i, stroke in enumerate(strokes):
        # Check if it has eraser flag
        if len(stroke) == 8:
            x_start, y_start, x_end, y_end, color, thickness, t_stamp, is_eraser = stroke
        else:
            # Backward compatibility
            x_start, y_start, x_end, y_end, color, thickness, t_stamp = stroke
            is_eraser = False
            
        if is_eraser and current_time - t_stamp <= AirConfig.STROKE_LIFETIME:
            eraser_strokes.append((x_start, y_start, x_end, y_end, thickness))
    
    # Second pass: draw non-erased strokes
    new_strokes = []
    for stroke in strokes:
        # Handle both formats (with or without eraser flag)
        if len(stroke) == 8:
            x_start, y_start, x_end, y_end, color, thickness, t_stamp, is_eraser = stroke
        else:
            x_start, y_start, x_end, y_end, color, thickness, t_stamp = stroke
            is_eraser = False
            
        # Skip drawing eraser strokes 
        if is_eraser:
            continue
            
        # Check if stroke has expired
        if current_time - t_stamp <= AirConfig.STROKE_LIFETIME:
            # Check if this stroke was erased
            erased = False
            for e_x_start, e_y_start, e_x_end, e_y_end, e_thickness in eraser_strokes:
                # Simplified collision detection using bounding boxes
                eraser_margin = e_thickness + thickness
                
                # Bounding boxes for stroke and eraser
                stroke_min_x = min(x_start, x_end) - eraser_margin
                stroke_max_x = max(x_start, x_end) + eraser_margin
                stroke_min_y = min(y_start, y_end) - eraser_margin
                stroke_max_y = max(y_start, y_end) + eraser_margin
                
                eraser_min_x = min(e_x_start, e_x_end) - eraser_margin
                eraser_max_x = max(e_x_start, e_x_end) + eraser_margin
                eraser_min_y = min(e_y_start, e_y_end) - eraser_margin
                eraser_max_y = max(e_y_start, e_y_end) + eraser_margin
                
                # Check for collision
                if not (stroke_max_x < eraser_min_x or stroke_min_x > eraser_max_x or 
                        stroke_max_y < eraser_min_y or stroke_min_y > eraser_max_y):
                    erased = True
                    break
                    
            # Draw and keep non-erased strokes
            if not erased:
                # Only draw below header area
                if y_start > AirConfig.HEADER_HEIGHT or y_end > AirConfig.HEADER_HEIGHT:
                    cv2.line(img_canvas, (x_start, y_start), (x_end, y_end), color, thickness)
                new_strokes.append(stroke)
    
    # Update strokes list
    strokes = new_strokes
    
    # Ensure canvas is type uint8 before conversion
    img_canvas = img_canvas.astype(np.uint8)
    
    # Convert drawing canvas to mask
    img_gray = cv2.cvtColor(img_canvas, cv2.COLOR_BGR2GRAY)
    _, img_inv = cv2.threshold(img_gray, 50, 255, cv2.THRESH_BINARY_INV)
    img_inv = cv2.cvtColor(img_inv, cv2.COLOR_GRAY2BGR)
    
    # Merge drawings with camera frame
    final_img = cv2.bitwise_and(processed_frame, img_inv)
    final_img = cv2.bitwise_or(final_img, img_canvas)
    
    # Apply current overlay header
    if header is not None and header.shape[0] == AirConfig.HEADER_HEIGHT and header.shape[1] == AirConfig.CANVAS_WIDTH:
        final_img[0:AirConfig.HEADER_HEIGHT, 0:AirConfig.CANVAS_WIDTH] = header
    
    # Add a visible boundary line to show where header ends
    cv2.line(final_img, (0, AirConfig.HEADER_HEIGHT), (AirConfig.CANVAS_WIDTH, AirConfig.HEADER_HEIGHT), (0, 0, 0), 3)
    cv2.line(final_img, (0, AirConfig.HEADER_HEIGHT), (AirConfig.CANVAS_WIDTH, AirConfig.HEADER_HEIGHT), (255, 255, 255), 1)
    
    # Draw brush size controls on right side, vertically stacked
    # Plus button (top)
    cv2.rectangle(final_img, (AirConfig.CANVAS_WIDTH-70, 200), (AirConfig.CANVAS_WIDTH-20, 250), (50, 50, 50), cv2.FILLED)
    cv2.putText(final_img, "+", (AirConfig.CANVAS_WIDTH-55, 235), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    
    # Minus button (bottom)
    cv2.rectangle(final_img, (AirConfig.CANVAS_WIDTH-70, 270), (AirConfig.CANVAS_WIDTH-20, 320), (50, 50, 50), cv2.FILLED)
    cv2.putText(final_img, "-", (AirConfig.CANVAS_WIDTH-55, 305), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    
    # Current brush size display (centered between buttons)
    cv2.putText(final_img, f"{brush_thickness}", (AirConfig.CANVAS_WIDTH-55, 370), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
    
    # Show hand timeout indicator if no hand is detected
    if not lm_list and AirConfig.show_countdown:
        time_since_last_hand = current_time - last_hand_detection_time
        if time_since_last_hand > 0 and time_since_last_hand < AirConfig.hand_timeout:
            # Show countdown
            remaining = AirConfig.hand_timeout - time_since_last_hand
            cv2.putText(final_img, f"Auto-clear in: {remaining:.1f}s", (20, AirConfig.CANVAS_HEIGHT-30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    # Display final image
    cv2.imshow("Canvas", final_img)
    
    # Key controls
    key = cv2.waitKey(1) & 0xFF 
    if key == ord('q'):
        break
    elif key == ord('c'):
        try:
            current_index = color_options.index(draw_color)
        except ValueError:
            current_index = 0
        
        # Update color
        new_index = (current_index + 1) % len(color_options)
        draw_color = color_options[new_index]
        
        # Update overlay based on new color
        if new_index == 0 and "red" in overlays:  # Red
            header = overlays["red"]
            current_overlay_key = "red"
            eraser_mode = False
        elif new_index == 1 and "blue" in overlays:  # Blue
            header = overlays["blue"]
            current_overlay_key = "blue"
            eraser_mode = False
        elif new_index == 2 and "green" in overlays:  # Green
            header = overlays["green"]
            current_overlay_key = "green"
            eraser_mode = False
        elif new_index == 3 and "eraser" in overlays:  # Eraser
            header = overlays["eraser"]
            current_overlay_key = "eraser"
            eraser_mode = True
                
        print(f"Color changed to: {draw_color}, mode: {current_overlay_key}")
        
    # Use 'x' to clear canvas
    elif key == ord('x'):
        strokes = []
    elif key == ord('+') and brush_thickness < 100:
        brush_thickness += 5
        print(f"Brush thickness increased to: {brush_thickness}")
    elif key == ord('-') and brush_thickness > 1:
        brush_thickness -= 5
        print(f"Brush thickness decreased to: {brush_thickness}")
    elif 48 <= key <= 57:
        pressed_keys.append(key - 48)
        
        if len(pressed_keys) == 9:
            blue = int(''.join(map(str, pressed_keys[:3])))
            green = int(''.join(map(str, pressed_keys[3:6])))
            red = int(''.join(map(str, pressed_keys[6:9])))
            draw_color = (blue, green, red)
            eraser_mode = False  # Custom colors are not eraser
            print("Color is set to:", draw_color)
            pressed_keys = []
            
picam2.stop()    
cv2.destroyAllWindows()
