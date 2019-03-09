from PIL import Image


def get_image_size(filepath):
    with Image.open(filepath) as img:
        width, height = img.size
    return width, height
