import base64
import cv2
import numpy as np
from colorama import Fore, Style, init

init(autoreset=True)

def print_with_color(text: str, color=""):
    if color == "red":
        print(Fore.RED + text)
    elif color == "green":
        print(Fore.GREEN + text)
    elif color == "yellow":
        print(Fore.YELLOW + text)
    elif color == "blue":
        print(Fore.BLUE + text)
    elif color == "magenta":
        print(Fore.MAGENTA + text)
    elif color == "cyan":
        print(Fore.CYAN + text)
    else:
        print(text)
    # No need for Style.RESET_ALL if autoreset=True in init()

def putBText(img,text,text_offset_x=20,text_offset_y=20,vspace=10,hspace=10, font_scale=1.0,background_RGB=(228,225,222),text_RGB=(1,1,1),font = cv2.FONT_HERSHEY_DUPLEX,thickness = 2,alpha=0.6,gamma=0):
    """
    Inputs:
    img: cv2 image img
    text_offset_x, text_offset_y: X,Y location of text start (top-left of the background box)
    vspace, hspace: Vertical and Horizontal space between text and box boundries
    font_scale: Font size
    background_RGB: Background R,G,B color
    text_RGB: Text R,G,B color
    font: Font Style e.g. cv2.FONT_HERSHEY_DUPLEX,cv2.FONT_HERSHEY_SIMPLEX,cv2.FONT_HERSHEY_PLAIN,cv2.FONT_HERSHEY_COMPLEX
          cv2.FONT_HERSHEY_TRIPLEX, etc
    thickness: Thickness of the text font
    alpha: Opacity 0~1 of the box around text
    gamma: 0 by default

    Output:
    img: CV2 image with text and background
    """
    # Ensure RGB values are integers if they aren't already
    R, G, B = int(background_RGB[0]), int(background_RGB[1]), int(background_RGB[2])
    text_R, text_G, text_B = int(text_RGB[0]), int(text_RGB[1]), int(text_RGB[2])

    (text_width, text_height) = cv2.getTextSize(text, font, fontScale=font_scale, thickness=thickness)[0]
    
    # Calculate coordinates for the background box
    # x, y are the top-left corner of the background box
    x, y = text_offset_x, text_offset_y
    
    # Define the region of interest (ROI) for the background box
    # Ensure ROI coordinates are within image bounds
    y1_roi, y2_roi = max(0, y - vspace), min(img.shape[0], y + text_height + vspace)
    x1_roi, x2_roi = max(0, x - hspace), min(img.shape[1], x + text_width + hspace)

    # Ensure the ROI is valid (y2 > y1 and x2 > x1)
    if y2_roi <= y1_roi or x2_roi <= x1_roi:
        # print_with_color(f"Warning: Invalid ROI for text '{text}' at ({x},{y}). Skipping background box.", "yellow")
        # If ROI is invalid, just draw text without background
        cv2.putText(img, text, (x, y + text_height), font, fontScale=font_scale, color=(text_B, text_G, text_R), thickness=thickness)
        return img

    crop = img[y1_roi:y2_roi, x1_roi:x2_roi]
    
    # Create the colored rectangle for the background
    white_rect = np.ones(crop.shape, dtype=np.uint8) # Ensure same shape as crop
    b_channel, g_channel, r_channel = cv2.split(white_rect)
    
    # Apply background color
    # Note: OpenCV uses BGR order for color channels in cv2.merge
    rect_changed = cv2.merge((B * b_channel, G * g_channel, R * r_channel))

    # Blend the crop with the colored rectangle
    res = cv2.addWeighted(crop, alpha, rect_changed, 1 - alpha, gamma)
    img[y1_roi:y2_roi, x1_roi:x2_roi] = res

    # Put the text on top of the blended background
    # Adjust text position to be within the background box, considering vspace/hspace
    # cv2.putText draws text from its bottom-left corner.
    text_draw_x = x 
    text_draw_y = y + text_height # Baseline of the text

    cv2.putText(img, text, (text_draw_x, text_draw_y), font, fontScale=font_scale, color=(text_B, text_G, text_R), thickness=thickness)
    return img

def draw_bbox_multi(img_path, output_path, elem_list, dark_mode=False): # dark_mode param kept for now, but not used for fixed colors
    img = cv2.imread(img_path)
    if img is None:
        print_with_color(f"Error: Could not read image at {img_path}", "red")
        return None

    count = 0
    
    # Fixed colors and thickness as per your request
    text_color_rgb = [0, 0, 0]  # Black text
    text_background_color_rgb = [200, 200, 200]  # Light gray background
    text_thickness = 3  # Bolder text

    for elem in elem_list:
        count += 1
        tl, br = elem.bbox[0], elem.bbox[1]
        label_text = str(count)

        try:
            # Calculate center of the element's bounding box
            center_x = (tl[0] + br[0]) // 2
            center_y = (tl[1] + br[1]) // 2

            # Estimate text size to help center the background box around the text
            # This is a bit heuristic with putBText as it manages its own padding (vspace, hspace)
            (text_w, text_h) = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 1, text_thickness)[0]
            
            # Aim to place the *center* of the text label (including its background) 
            # at the center of the UI element's bounding box.
            # putBText's text_offset_x, text_offset_y is the top-left of its background.
            # So, we need to shift from the center_x, center_y to get that top-left.
            # The actual background box size by putBText is (text_w + 2*hspace) x (text_h + 2*vspace)
            # Let's use small hspace/vspace for the label background.
            label_hspace = 3 
            label_vspace = 3

            text_bg_width = text_w + 2 * label_hspace
            text_bg_height = text_h + 2 * label_vspace
            
            offset_x = center_x - (text_bg_width // 2)
            offset_y = center_y - (text_bg_height // 2)


            img = putBText(img, label_text,
                           text_offset_x=offset_x,
                           text_offset_y=offset_y,
                           vspace=label_vspace, hspace=label_hspace, # Small padding for the label
                           font_scale=1.0, # Font scale for the label number
                           thickness=text_thickness,
                           background_RGB=tuple(text_background_color_rgb),
                           text_RGB=tuple(text_color_rgb),
                           font=cv2.FONT_HERSHEY_SIMPLEX, # Standard font
                           alpha=0.7) # Background opacity for the label
        except Exception as e:
            print_with_color(f"Error drawing text with putBText for element {count}: {e}", "red")
            # Fallback to simple cv2.putText if putBText fails (without background)
            try:
                cv2.putText(img, label_text,
                            (center_x - text_w // 2, center_y + text_h // 2), # Try to center text
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1.0, # font_scale
                            tuple(text_color_rgb),
                            text_thickness)
            except Exception as e_fallback:
                 print_with_color(f"Fallback cv2.putText also failed for element {count}: {e_fallback}", "red")

    cv2.imwrite(output_path, img)
    return img

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')