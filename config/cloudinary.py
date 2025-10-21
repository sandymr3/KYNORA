"""Cloudinary Configuration for Image Storage"""

import cloudinary
import cloudinary.uploader
import cloudinary.api
from config.settings import settings
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class CloudinaryConfig:
    """Cloudinary configuration and helper methods"""
    
    _instance: Optional['CloudinaryConfig'] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Singleton pattern for Cloudinary configuration"""
        if cls._instance is None:
            cls._instance = super(CloudinaryConfig, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Cloudinary configuration"""
        if not self._initialized:
            self._initialize_cloudinary()
            self._initialized = True
    
    def _initialize_cloudinary(self):
        """Initialize Cloudinary with credentials"""
        try:
            cloudinary_config = settings.get_cloudinary_config()
            cloudinary.config(
                cloud_name=cloudinary_config["cloud_name"],
                api_key=cloudinary_config["api_key"],
                api_secret=cloudinary_config["api_secret"],
                secure=True
            )
            logger.info(f"Cloudinary initialized for cloud: {cloudinary_config['cloud_name']}")
        except Exception as e:
            logger.error(f"Failed to initialize Cloudinary: {str(e)}")
            raise Exception(f"Cloudinary initialization failed: {str(e)}")
    
    def upload_image(
        self, 
        file_path: str, 
        folder: str = "kynora",
        public_id: Optional[str] = None,
        transformation: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Upload image to Cloudinary
        
        Args:
            file_path: Path to the image file or URL
            folder: Folder name in Cloudinary
            public_id: Public ID for the image
            transformation: Image transformation options
            **kwargs: Additional upload options
            
        Returns:
            dict: Upload response with URL and metadata
        """
        try:
            upload_options = {
                "folder": folder,
                "resource_type": "image",
                "overwrite": True,
                "invalidate": True,
                **kwargs
            }
            
            if public_id:
                upload_options["public_id"] = public_id
            
            if transformation:
                upload_options["transformation"] = transformation
            
            result = cloudinary.uploader.upload(file_path, **upload_options)
            
            logger.info(f"Image uploaded successfully: {result.get('public_id')}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to upload image: {str(e)}")
            raise Exception(f"Image upload failed: {str(e)}")
    
    def upload_product_image(
        self, 
        file_path: str, 
        product_id: str,
        image_type: str = "main"
    ) -> str:
        """
        Upload product image with automatic transformations
        
        Args:
            file_path: Path to the image file
            product_id: Product ID
            image_type: Type of image (main, thumbnail, gallery)
            
        Returns:
            str: Cloudinary URL of uploaded image
        """
        try:
            folder = f"kynora/products/{product_id}"
            public_id = f"{product_id}_{image_type}"
            
            # Define transformations based on image type
            transformations = {
                "main": [
                    {"width": 800, "height": 800, "crop": "fill", "quality": "auto:good"},
                ],
                "thumbnail": [
                    {"width": 300, "height": 300, "crop": "fill", "quality": "auto:good"},
                ],
                "gallery": [
                    {"width": 1200, "height": 1200, "crop": "limit", "quality": "auto:best"},
                ]
            }
            
            transformation = transformations.get(image_type, transformations["main"])
            
            result = self.upload_image(
                file_path,
                folder=folder,
                public_id=public_id,
                transformation=transformation
            )
            
            return result["secure_url"]
            
        except Exception as e:
            logger.error(f"Failed to upload product image: {str(e)}")
            raise Exception(f"Product image upload failed: {str(e)}")
    
    def upload_user_avatar(self, file_path: str, user_id: str) -> str:
        """
        Upload user avatar with automatic transformations
        
        Args:
            file_path: Path to the avatar file
            user_id: User ID
            
        Returns:
            str: Cloudinary URL of uploaded avatar
        """
        try:
            result = self.upload_image(
                file_path,
                folder=f"kynora/users/{user_id}",
                public_id=f"{user_id}_avatar",
                transformation=[
                    {"width": 300, "height": 300, "crop": "fill", "gravity": "face", "quality": "auto:good"},
                ]
            )
            return result["secure_url"]
            
        except Exception as e:
            logger.error(f"Failed to upload user avatar: {str(e)}")
            raise Exception(f"Avatar upload failed: {str(e)}")
    
    def delete_image(self, public_id: str) -> bool:
        """
        Delete image from Cloudinary
        
        Args:
            public_id: Public ID of the image
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            result = cloudinary.uploader.destroy(public_id)
            return result.get("result") == "ok"
        except Exception as e:
            logger.error(f"Failed to delete image: {str(e)}")
            return False
    
    def get_optimized_url(
        self, 
        public_id: str, 
        width: Optional[int] = None,
        height: Optional[int] = None,
        crop: str = "fill",
        quality: str = "auto",
        format: str = "auto"
    ) -> str:
        """
        Get optimized URL for an image
        
        Args:
            public_id: Public ID of the image
            width: Desired width
            height: Desired height
            crop: Crop mode
            quality: Image quality
            format: Image format
            
        Returns:
            str: Optimized image URL
        """
        try:
            options = {
                "crop": crop,
                "quality": quality,
                "format": format,
                "secure": True
            }
            
            if width:
                options["width"] = width
            if height:
                options["height"] = height
            
            return cloudinary.CloudinaryImage(public_id).build_url(**options)
            
        except Exception as e:
            logger.error(f"Failed to generate optimized URL: {str(e)}")
            raise Exception(f"URL generation failed: {str(e)}")


# Global Cloudinary instance
cloudinary_config = CloudinaryConfig()

# Export helper functions
upload_image = cloudinary_config.upload_image
upload_product_image = cloudinary_config.upload_product_image
upload_user_avatar = cloudinary_config.upload_user_avatar
delete_image = cloudinary_config.delete_image
get_optimized_url = cloudinary_config.get_optimized_url
