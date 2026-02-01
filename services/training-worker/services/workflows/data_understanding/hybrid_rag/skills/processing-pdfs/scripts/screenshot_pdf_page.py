import os
import sys
from pdf2image import convert_from_path
from PIL import Image

# Maximum file size limit (100MB)
MAX_FILE_SIZE_MB = 100


def screenshot_page(pdf_path, page_number=1, output_path=None, dpi=150, max_dim=1500):
    """
    Take a screenshot of a specific page from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        page_number: 1-indexed page number to screenshot (default: 1)
        output_path: Output path for the screenshot (default: same dir as PDF)
        dpi: Resolution for rendering (default: 150)
        max_dim: Maximum dimension (width or height) for the output image (default: 1500)
    
    Returns:
        Path to the saved screenshot
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # Validate file extension
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError("File must be a PDF")
    
    # Check file size
    file_size = os.path.getsize(pdf_path)
    if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ValueError(f"PDF file too large: {file_size / (1024*1024):.1f}MB (max {MAX_FILE_SIZE_MB}MB)")
    
    # Convert the specific page to image
    images = convert_from_path(
        pdf_path, 
        dpi=dpi, 
        first_page=page_number, 
        last_page=page_number
    )
    
    if not images:
        raise ValueError(f"Could not extract page {page_number} from PDF")
    
    image = images[0]
    
    # Scale image if needed to keep width/height under max_dim
    width, height = image.size
    if width > max_dim or height > max_dim:
        scale_factor = min(max_dim / width, max_dim / height)
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Determine output path
    if output_path is None:
        pdf_dir = os.path.dirname(pdf_path) or "."
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(pdf_dir, f"{pdf_name}_page_{page_number}.png")
    
    # Save the screenshot
    try:
        image.save(output_path, "PNG")
        print(f"Screenshot saved: {output_path} (size: {image.size})")
    except (IOError, PermissionError, OSError) as e:
        raise IOError(f"Failed to save screenshot to {output_path}: {e}")
    
    return output_path


def screenshot_pages(pdf_path, page_numbers=None, output_dir=None, dpi=150, max_dim=1500):
    """
    Take screenshots of multiple pages from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        page_numbers: List of 1-indexed page numbers (default: all pages)
        output_dir: Output directory for screenshots (default: same dir as PDF)
        dpi: Resolution for rendering (default: 150)
        max_dim: Maximum dimension for output images (default: 1500)
    
    Returns:
        List of paths to saved screenshots
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # Validate file extension
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError("File must be a PDF")
    
    # Check file size
    file_size = os.path.getsize(pdf_path)
    if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ValueError(f"PDF file too large: {file_size / (1024*1024):.1f}MB (max {MAX_FILE_SIZE_MB}MB)")
    
    # Determine output directory
    if output_dir is None:
        output_dir = os.path.dirname(pdf_path) or "."
    os.makedirs(output_dir, exist_ok=True)
    
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # Convert all pages if page_numbers not specified
    if page_numbers is None:
        images = convert_from_path(pdf_path, dpi=dpi)
        page_numbers = list(range(1, len(images) + 1))
    else:
        images = []
        for page_num in page_numbers:
            page_images = convert_from_path(
                pdf_path, 
                dpi=dpi, 
                first_page=page_num, 
                last_page=page_num
            )
            images.extend(page_images)
    
    saved_paths = []
    for i, (image, page_num) in enumerate(zip(images, page_numbers)):
        # Scale image if needed
        width, height = image.size
        if width > max_dim or height > max_dim:
            scale_factor = min(max_dim / width, max_dim / height)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        output_path = os.path.join(output_dir, f"{pdf_name}_page_{page_num}.png")
        try:
            image.save(output_path, "PNG")
            print(f"Screenshot saved: {output_path} (size: {image.size})")
        except (IOError, PermissionError, OSError) as e:
            raise IOError(f"Failed to save screenshot to {output_path}: {e}")
        saved_paths.append(output_path)
    
    print(f"Saved {len(saved_paths)} screenshots to {output_dir}")
    return saved_paths


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: screenshot_pdf_page.py <pdf_path> [page_number|--all] [output_path]")
        print("  pdf_path: Path to the PDF file")
        print("  page_number: 1-indexed page number (default: 1)")
        print("  --all: Screenshot all pages")
        print("  output_path: Output path for screenshot (optional)")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    # Check for --all flag
    if len(sys.argv) > 2 and sys.argv[2] == "--all":
        output_dir = sys.argv[3] if len(sys.argv) > 3 else None
        screenshot_pages(pdf_path, output_dir=output_dir)
    else:
        # Validate page number input
        try:
            page_number = int(sys.argv[2]) if len(sys.argv) > 2 else 1
            if page_number < 1:
                print(f"Error: page_number must be >= 1, got {page_number}")
                sys.exit(1)
        except ValueError:
            print(f"Error: page_number must be an integer, got '{sys.argv[2]}'")
            sys.exit(1)
        
        output_path = sys.argv[3] if len(sys.argv) > 3 else None
        screenshot_page(pdf_path, page_number, output_path)
