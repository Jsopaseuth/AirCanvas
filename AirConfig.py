import os

# Configurations/Global Parameters
CANVAS_WIDTH = 1920
CANVAS_HEIGHT = 1080
HEADER_HEIGHT = 125
STROKE_LIFETIME = 30.0 # Lifetime in seconds of drawn pixels
default_color = (0, 0, 255) # default red
default_brush_thickness = 5
eraser_brush_multiplier = 2 # Eraser size multiplied constant

# Hand presence tracking
detection_confidence = 0.85
tracking_confidence = 0.5
hand_timeout = 10  # seconds before clearing canvas when no hand detected

# Define color values
BLUE_COLOR = (255, 50, 10)   # Blue in BGR
GREEN_COLOR = (0, 255, 0)    # Green in BGR
RED_COLOR = (0, 0, 255)      # Red in BGR
ERASER_COLOR = (255, 192, 203)  # Light pink for eraser

# Define color detection regions in the overlay
# Format: (min_x, max_x, min_y, max_y, color_name, BGR color value)
# Updated based on percentage of distance away from left side of screen position
color_regions = [
    (CANVAS_WIDTH * 0.12, CANVAS_WIDTH * 0.20, HEADER_HEIGHT * 0.01, HEADER_HEIGHT * 0.95, "blue", BLUE_COLOR),     # 12-20% on x axis
    (CANVAS_WIDTH * 0.43, CANVAS_WIDTH * 0.51, HEADER_HEIGHT * 0.01, HEADER_HEIGHT * 0.95, "green", GREEN_COLOR),   # 43-51% on x axis
    (CANVAS_WIDTH * 0.73, CANVAS_WIDTH * 0.81, HEADER_HEIGHT * 0.01, HEADER_HEIGHT * 0.95, "red", RED_COLOR),      # 73-81% on x axis
    (CANVAS_WIDTH * 0.91, CANVAS_WIDTH * 0.98, HEADER_HEIGHT * 0.01, HEADER_HEIGHT * 0.95, "eraser", ERASER_COLOR) # 91-98% on x axis
    
    
    # (150, 250, 10, HEADER_HEIGHT-10, "blue", BLUE_COLOR),     # Blue brush (x=200)
    # (550, 650, 10, HEADER_HEIGHT-10, "green", GREEN_COLOR),   # Green brush (x=600)
    # (940, 1040, 10, HEADER_HEIGHT-10, "red", RED_COLOR),      # Red brush (x=990)
    # (1160, 1260, 10, HEADER_HEIGHT-10, "eraser", ERASER_COLOR) # Eraser (x=1210)
    
]

# Add brush size control regions to the right side of the screen
# Format: (min_x, max_x, min_y, max_y, action)
brush_control_regions = [
    (CANVAS_WIDTH-70, CANVAS_WIDTH-20, 200, 250, "increase"),   # Plus button (top)
    (CANVAS_WIDTH-70, CANVAS_WIDTH-20, 270, 320, "decrease")    # Minus button (bottom)
    
]

# Load overlays
folder_path = "/home/cotadmin/Downloads/Interfaces"

overlay_paths = {
    "red":  "0_red_option.jpg",       # red overlay
    "blue": "1_blue_option.jpg",     # blue overlay
    "green": "2_green_option.jpg",   # green overlay
    "eraser": "3_eraser_option.jpg"  # eraser overlay
}

show_countdown = True # When true shows auto-clear countdown when hand is not detected
debug_mode = False # When true, print additional debug information
