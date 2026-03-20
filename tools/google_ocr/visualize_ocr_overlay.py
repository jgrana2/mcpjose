import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pdf2image import convert_from_path
import re

def parse_output_file(filepath):
    """Parse the output.txt file and extract text and coordinates"""
    texts = []
    boxes = []
    
    with open(filepath, 'r') as f:
        for line in f:
            # Parse line format: Text: 'string', Box: [x_min, y_min, x_max, y_max]
            match = re.match(r"Text: '([^']*)', Box: \[([\d,\s]+)\]", line)
            if match:
                text = match.group(1)
                coords = list(map(int, match.group(2).split(',')))
                texts.append(text)
                boxes.append(coords)
    
    return texts, boxes

def plot_ocr_on_pdf(pdf_path, texts, boxes, output_file=None):
    """Plot OCR bounding boxes on top of the PDF image"""
    if not boxes:
        print("No boxes to plot")
        return
    
    # Convert PDF to images (first page)
    images = convert_from_path(pdf_path, dpi=300)
    
    if not images:
        print("Could not convert PDF to images")
        return
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(16, 20))
    
    # Display the first page image
    ax.imshow(images[0])
    
    # Add rectangles for each text box
    for i, (text, box) in enumerate(zip(texts, boxes)):
        x_min_box, y_min_box, x_max_box, y_max_box = box
        width = x_max_box - x_min_box
        height = y_max_box - y_min_box
        
        # Create rectangle with red outline
        rect = Rectangle((x_min_box, y_min_box), width, height, 
                         linewidth=2, edgecolor='red', facecolor='none', alpha=0.8)
        ax.add_patch(rect)
        
        # Add text label (skip very small texts to avoid clutter)
        if len(text) > 1:
            ax.text(x_min_box, y_min_box - 5, text, fontsize=7, color='white', 
                   bbox=dict(boxstyle='round,pad=0.2', facecolor='red', alpha=0.7))
    
    ax.set_title('OCR Text Detection Overlay on PDF', fontsize=14, fontweight='bold')
    ax.axis('off')
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, dpi=100, bbox_inches='tight')
        print(f"Plot saved to {output_file}")
    
    plt.show()

if __name__ == "__main__":
    # Parse the output file
    texts, boxes = parse_output_file('output.txt')
    
    print(f"Found {len(texts)} text elements")
    
    # Plot the boxes on top of the PDF
    plot_ocr_on_pdf('IDE2086 R0305.pdf', texts, boxes, 'ocr_overlay.png')
