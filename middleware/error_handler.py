"""Error handling middleware"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import traceback
from typing import Callable

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handler middleware"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request and handle errors"""
        try:
            response = await call_next(request)
            return response
            
        except HTTPException as http_exc:
            # Let FastAPI handle HTTP exceptions normally
            raise http_exc
            
        except Exception as exc:
            # Log the error with traceback
            logger.error(
                f"Unhandled exception: {str(exc)}\n"
                f"Path: {request.url.path}\n"
                f"Method: {request.method}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            
            # Return generic error response
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "An internal server error occurred",
                    "error_id": str(id(exc)),
                    "path": str(request.url.path)
                }
            )


class ValidationErrorHandler:
    """Handle validation errors"""
    
    @staticmethod
    def format_validation_error(error):
        """Format Pydantic validation errors"""
        errors = []
        for err in error.errors():
            field = ".".join(str(x) for x in err["loc"])
            message = err["msg"]
            errors.append({
                "field": field,
                "message": message,
                "type": err["type"]
            })
        return errors
