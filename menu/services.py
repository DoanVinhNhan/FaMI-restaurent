import os
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys

class ImageService:
    """
    Service for handling image processing (resizing, format conversion).
    """

    @staticmethod
    def process_image(image, max_size=(800, 800), format='JPEG', quality=85):
        """
        Resizes an image to fit within max_size, maintaining aspect ratio.
        Converts to specified format (default JPEG).
        
        Args:
            image: The uploaded image file.
            max_size: Tuple (width, height).
            format: Target image format.
            quality: Compression quality.
            
        Returns:
            InMemoryUploadedFile: The processed image ready for saving.
        """
        if not image:
            return None

        # Open image using Pillow
        img = Image.open(image)
        
        # Convert mode to RGB if necessary (e.g. for PNG with transparency -> JPEG)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        # Resize if larger than max_size
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Save to buffer
        output = BytesIO()
        img.save(output, format=format, quality=quality)
        output.seek(0)

        # Create new InMemoryUploadedFile
        new_image = InMemoryUploadedFile(
            output,
            'ImageField',
            f"{os.path.splitext(image.name)[0]}.jpg",
            'image/jpeg',
            sys.getsizeof(output),
            None
        )
        
        return new_image
