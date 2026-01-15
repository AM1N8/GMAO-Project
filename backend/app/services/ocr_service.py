import os
import ollama
from ollama import AsyncClient
import pytesseract
from PIL import Image
import io
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        self.ollama_host = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        # This gets the model name from your .env file
        self.vision_model = os.getenv("OLLAMA_VISION_MODEL", "qwen2.5vl:3b")
        # Use AsyncClient for non-blocking I/O
        self.client = AsyncClient(host=self.ollama_host)
        logger.info(f"OCR Service initialized with model: {self.vision_model}")

    def get_active_model(self) -> Dict[str, str]:
        """Returns the currently configured VLM model name."""
        return {
            "model": self.vision_model,
            "provider": "ollama",
            "host": self.ollama_host
        }

    def _optimize_image(self, file_content: bytes) -> bytes:
        """
        Resizes large images to max 1024px to speed up VLM tokenization.
        Converts to efficient JPEG format.
        """
        try:
            image = Image.open(io.BytesIO(file_content))
            
            # Convert to RGB (handles RGBA/P modes)
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Resize if dimension > 1024px to reduce token count
            max_dim = 1024
            if max(image.width, image.height) > max_dim:
                image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                
                # Save to optimized bytes
                buf = io.BytesIO()
                image.save(buf, format='JPEG', quality=85)
                return buf.getvalue()
            
            return file_content
        except Exception as e:
            logger.warning(f"Image optimization failed: {e}")
            return file_content

    async def extract_markdown_vlm(self, file_content: bytes) -> str:
        """
        Uses VLM to extract text with structure (tables, headers) preserved.
        """
        # Optimize image size before sending
        optimized_image = self._optimize_image(file_content)
        
        try:
            # Use await + keep_alive to prevent reloading model
            response = await self.client.chat(
                model=self.vision_model,
                messages=[{
                    'role': 'user',
                    'content': (
                        "OCR this image completely and accurately. "
                        "1. Extract all text including headings, paragraphs, and lists. "
                        "2. If there are tables, represent them using Markdown table syntax. "
                        "3. Use appropriate Markdown for headers (# ## ###) and lists (- or 1.). "
                        "4. Output ONLY the raw Markdown content. No introductory text."
                    ),
                    'images': [optimized_image]
                }],
                keep_alive="1h"  # Keep model in VRAM for 1 hour
            )
            return response['message']['content']
        except Exception as e:
            logger.error(f"VLM Markdown extraction failed: {e}")
            logger.info("Falling back to Tesseract...")
            # Fallback is synchronous, run in threadpool if needed, but acceptable here
            return pytesseract.image_to_string(Image.open(io.BytesIO(file_content)))

    async def extract_semantic_html(self, file_content: bytes) -> str:
        optimized_image = self._optimize_image(file_content)
        try:
            response = await self.client.chat(
                model=self.vision_model,
                messages=[{
                    'role': 'user',
                    'content': (
                        "Convert the content of this image into semantic HTML. "
                        "1. Use <h1>, <h2> for titles. "
                        "2. Use <p> for paragraphs and <ul>/<li> for lists. "
                        "3. Use <table> tags for tabular data. "
                        "4. Return ONLY the HTML code inside a <div>. No markdown code blocks."
                    ),
                    'images': [optimized_image]
                }],
                keep_alive="1h"
            )
            content = response['message']['content']
            # Clean up if model adds ```html ... ```
            return content.replace("```html", "").replace("```", "").strip()
        except Exception as e:
            logger.error(f"VLM HTML extraction failed: {e}")
            raise

    async def extract_structured_json(self, file_content: bytes) -> str:
        optimized_image = self._optimize_image(file_content)
        try:
            response = await self.client.chat(
                model=self.vision_model,
                format="json", 
                messages=[{
                    'role': 'user',
                    'content': (
                        "Analyze this image and extract all data into a JSON object. "
                        "Use keys like 'document_title', 'sections' (with 'heading' and 'content'), 'tables', and 'metadata'."
                    ),
                    'images': [optimized_image]
                }],
                keep_alive="1h"
            )
            return response['message']['content']
        except Exception as e:
            logger.error(f"VLM JSON extraction failed: {e}")
            return "{}"

    async def extract_text(self, file_content: bytes) -> str:
        """
        Extracts raw text content with minimal formatting.
        """
        optimized_image = self._optimize_image(file_content)
        try:
            response = await self.client.chat(
                model=self.vision_model,
                messages=[{
                    'role': 'user',
                    'content': (
                        "OCR this image and extract all text. "
                        "Return ONLY the plain text content. "
                        "Do not use markdown formatting or tables. "
                        "Maintain the original reading order."
                    ),
                    'images': [optimized_image]
                }],
                keep_alive="1h"
            )
            return response['message']['content']
        except Exception as e:
            logger.error(f"VLM Text extraction failed: {e}")
            return pytesseract.image_to_string(Image.open(io.BytesIO(file_content)))

# Singleton instance
ocr_service = OCRService()