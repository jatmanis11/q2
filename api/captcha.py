from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pytesseract
from PIL import Image
import io
import re
import os

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure tesseract path for Vercel (if available)
if os.path.exists('/usr/bin/tesseract'):
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

@app.post("/")
async def solve_captcha(file: UploadFile = File(...)):
    """
    Solve multiplication CAPTCHA from uploaded image
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read and process the image
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to grayscale for better OCR
        if image.mode != 'L':
            image = image.convert('L')
        
        # Extract text using OCR
        try:
            extracted_text = pytesseract.image_to_string(
                image, 
                config='--psm 8 -c tessedit_char_whitelist=0123456789x*×=+'
            ).strip()
        except Exception as ocr_error:
            # Fallback: try basic image processing without tesseract
            raise HTTPException(
                status_code=500, 
                detail=f"OCR processing failed: {str(ocr_error)}"
            )
        
        print(f"Extracted text: {extracted_text}")
        
        # Find multiplication pattern
        patterns = [
            r'(\d{8})\s*[×*x]\s*(\d{8})',  # 8-digit × 8-digit
            r'(\d+)\s*[×*x]\s*(\d+)',      # any digits × any digits
        ]
        
        num1, num2 = None, None
        
        for pattern in patterns:
            match = re.search(pattern, extracted_text)
            if match:
                num1, num2 = match.groups()
                break
        
        if num1 is None or num2 is None:
            # Try alternative extraction methods
            for separator in ['×', '*', 'x', 'X']:
                if separator in extracted_text:
                    parts = extracted_text.split(separator)
                    if len(parts) >= 2:
                        nums = []
                        for part in parts:
                            numbers = re.findall(r'\d+', part)
                            if numbers:
                                nums.extend(numbers)
                        if len(nums) >= 2:
                            num1, num2 = nums[0], nums[1]
                            break
        
        if num1 is None or num2 is None:
            raise HTTPException(
                status_code=422, 
                detail=f"Could not extract multiplication problem from image. Found text: '{extracted_text}'"
            )
        
        # Convert to integers and calculate
        try:
            int1 = int(num1)
            int2 = int(num2)
            result = int1 * int2
        except ValueError:
            raise HTTPException(
                status_code=422, 
                detail=f"Could not convert extracted numbers to integers: {num1}, {num2}"
            )
        
        # Return the required response format
        response = {
            "answer": str(result),
            "email": "23f3004152@ds.study.iitm.ac.in"
        }
        
        print(f"Calculation: {int1} × {int2} = {result}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

# Health check
@app.get("/")
async def health_check():
    return {"message": "CAPTCHA Solver API is running on Vercel"}
