
import io
import os
import numpy as np
from pptx import Presentation
from PIL import Image

def extract_clean_images_from_pptx(pptx_path, output_dir):
    """
    Extract images from PPTX, combining multiple images per slide into a single flattened image.
    For slides with multiple images:
    - If images are same size: composite them (max blend for overlays)
    - If images are different sizes: stitch them together (horizontally or vertically)
    """
    os.makedirs(output_dir, exist_ok=True)
    prs = Presentation(pptx_path)
    extracted = []

    for slide_idx, slide in enumerate(prs.slides, start=1):
        slide_images = []
        
        # Collect all images from this slide
        for shape_idx, shape in enumerate(slide.shapes, start=1):
            if not shape.shape_type == 13:  # Skip if not a picture
                continue
            if not hasattr(shape, "image"):
                continue

            image = shape.image
            try:
                img_data = io.BytesIO(image.blob)
                with Image.open(img_data) as im:
                    # Convert to RGB if needed
                    if im.mode != 'RGB':
                        im = im.convert('RGB')
                    slide_images.append(np.array(im))
            except Exception as e:
                print(f"Skipping image from slide {slide_idx}: {e}")
                continue
        
        if not slide_images:
            continue
        
        # Process slide images
        if len(slide_images) == 1:
            # Single image: save as-is
            combined_img = Image.fromarray(slide_images[0])
        else:
            # Multiple images: combine them
            combined_img = combine_slide_images(slide_images)
        
        # Save the combined image
        name = f"slide{slide_idx:02d}.png"
        path = os.path.join(output_dir, name)
        combined_img.save(path)
        extracted.append(name)
    
    return extracted


def combine_slide_images(images):
    """
    Combine multiple images from a slide into a single image.
    
    Strategy:
    1. If all images are the same size: composite using max blend (for overlays)
    2. If different sizes: stitch horizontally or vertically based on dimensions
    """
    if not images:
        raise ValueError("No images to combine")
    
    if len(images) == 1:
        return Image.fromarray(images[0])
    
    # Get dimensions
    heights = [img.shape[0] for img in images]
    widths = [img.shape[1] for img in images]
    
    # Check if all images are the same size
    if len(set(heights)) == 1 and len(set(widths)) == 1:
        # Same size: composite using max blend (for overlays/channels)
        h, w = heights[0], widths[0]
        combined = np.zeros((h, w, 3), dtype=np.uint8)
        
        for img in images:
            # Use maximum intensity for each pixel (good for fluorescence overlays)
            combined = np.maximum(combined, img)
        
        return Image.fromarray(combined)
    
    # Different sizes: stitch them together
    # Determine if we should stitch horizontally or vertically
    # by comparing total width vs total height
    total_width = sum(widths)
    total_height = sum(heights)
    max_width = max(widths)
    max_height = max(heights)
    
    # If images have similar heights, stitch horizontally
    # If images have similar widths, stitch vertically
    height_variance = np.var(heights) / (np.mean(heights) ** 2) if np.mean(heights) > 0 else 1
    width_variance = np.var(widths) / (np.mean(widths) ** 2) if np.mean(widths) > 0 else 1
    
    if height_variance < width_variance and height_variance < 0.1:
        # Similar heights: stitch horizontally
        stitched = stitch_horizontally(images)
    else:
        # Stitch vertically
        stitched = stitch_vertically(images)
    
    return Image.fromarray(stitched)


def stitch_horizontally(images):
    """Stitch images horizontally, aligning to top."""
    heights = [img.shape[0] for img in images]
    widths = [img.shape[1] for img in images]
    
    max_height = max(heights)
    total_width = sum(widths)
    
    stitched = np.zeros((max_height, total_width, 3), dtype=np.uint8)
    x_offset = 0
    
    for img in images:
        h, w = img.shape[0], img.shape[1]
        stitched[:h, x_offset:x_offset+w] = img
        x_offset += w
    
    return stitched


def stitch_vertically(images):
    """Stitch images vertically, aligning to left."""
    heights = [img.shape[0] for img in images]
    widths = [img.shape[1] for img in images]
    
    total_height = sum(heights)
    max_width = max(widths)
    
    stitched = np.zeros((total_height, max_width, 3), dtype=np.uint8)
    y_offset = 0
    
    for img in images:
        h, w = img.shape[0], img.shape[1]
        stitched[y_offset:y_offset+h, :w] = img
        y_offset += h
    
    return stitched
