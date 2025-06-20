import cv2
import numpy as np
import os

def detect_and_blur_watermark(image_path, output_path, overlay_logo_path=None):
    img = cv2.imread(image_path)

    if img is None:
        print(f"Error: Could not read image from {image_path}")
        return False

    # Convert to grayscale for detection
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Basic watermark detection using thresholding
    # This tries to find very bright areas, common for some watermarks
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)

    # Find contours of bright areas (likely watermark text/logos)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        # Apply blur only if contour area is large enough to be a watermark
        if w * h > 150: # You can adjust this threshold (150)
            roi = img[y:y+h, x:x+w]
            blurred = cv2.GaussianBlur(roi, (23, 23), 30) # Adjust kernel size (23,23) and sigma (30) for blur intensity
            img[y:y+h, x:x+w] = blurred

    # Optional overlay (your logo)
    if overlay_logo_path:
        logo = cv2.imread(overlay_logo_path, cv2.IMREAD_UNCHANGED)
        if logo is not None:
            logo_height, logo_width = logo.shape[:2]
            img_height, img_width = img.shape[:2]

            # Resize logo to fit, maintaining aspect ratio, max 100x100
            target_width = 100
            target_height = int(logo_height * (target_width / logo_width))
            if target_height > 100:
                target_height = 100
                target_width = int(logo_width * (target_height / logo_height))

            logo = cv2.resize(logo, (target_width, target_height), interpolation=cv2.INTER_AREA)

            # Calculate offset to place in top right corner (adjust 10 for padding)
            y_offset, x_offset = 10, img_width - logo.shape[1] - 10
            
            # Ensure the logo placement doesn't go out of bounds
            if y_offset + logo.shape[0] > img_height or x_offset + logo.shape[1] > img_width:
                print("Warning: Logo might be too large or placement is out of bounds for the image. Adjusting or skipping overlay.")
                # You might add logic to resize further or place elsewhere, or skip
                
            # If logo has an alpha channel (for transparency)
            if logo.shape[2] == 4: # Check for 4 channels (RGBA)
                alpha_s = logo[:, :, 3] / 255.0 # Alpha mask of the logo
                alpha_l = 1.0 - alpha_s # Inverse alpha mask

                for c in range(0, 3): # For R, G, B channels
                    img[y_offset:y_offset+logo.shape[0], x_offset:x_offset+logo.shape[1], c] = \
                        (alpha_s * logo[:, :, c] + # Blend logo foreground
                         alpha_l * img[y_offset:y_offset+logo.shape[0], x_offset:x_offset+logo.shape[1], c]) # Blend image background
            else: # No alpha channel, simple overlay (assuming RGB)
                img[y_offset:y_offset+logo.shape[0], x_offset:x_offset+logo.shape[1]] = logo[:, :, :3]
        else:
            print(f"Error: Could not read overlay logo from {overlay_logo_path}")

    # Save output
    cv2.imwrite(output_path, img)
    return True

def process_media(file_path):
    base, ext = os.path.splitext(file_path)
    output_file_path = f"{base}_processed{ext}"
    
    # Get overlay logo path from environment variable (from Render's config)
    your_overlay_logo_path = os.getenv("OVERLAY_LOGO_PATH", None) 

    if detect_and_blur_watermark(file_path, output_file_path, your_overlay_logo_path):
        print(f"Media processed and saved to {output_file_path}")
        return output_file_path
    else:
        print(f"Failed to process media: {file_path}")
        return None
