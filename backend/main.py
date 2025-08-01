# main.py - Real AI Logo Generator Backend with DALL-E 3
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json
import hashlib
import time
import asyncio  # Added missing import
from datetime import datetime
import requests
import base64
from io import BytesIO
from PIL import Image
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

# ================== CONFIGURATION ==================
app = FastAPI(
    title="Real AI LogoAI Backend",
    description="True AI-powered logo generation using DALL-E 3",
    version="3.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables
load_dotenv()

# Configure OpenAI
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Rate limiting
rate_limits = {}

# Create directories
os.makedirs("generated_logos", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Mount static files for serving images
app.mount("/static/logos", StaticFiles(directory="generated_logos"), name="logos")

# ================== DATA MODELS ==================
class BusinessInfo(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    industry: str = Field(..., min_length=1)
    description: Optional[str] = Field(None, max_length=200)
    target_audience: Optional[str] = None

class LogoStyle(BaseModel):
    style_type: str = Field(..., pattern="^(modern|vintage|bold|elegant|playful|professional)$")
    color_palette: List[str] = Field(..., min_items=1, max_items=5)
    font_preference: Optional[str] = "sans-serif"

class LogoGenerationRequest(BaseModel):
    business_info: BusinessInfo
    style: LogoStyle
    variations: int = Field(default=2, ge=1, le=4)  # Changed default to 2

class LogoResponse(BaseModel):
    id: str
    name: str
    image_url: str  # Now points to local served image
    dalle_url: Optional[str] = None  # Original DALL-E URL for reference
    local_path: Optional[str] = None  # Local saved image path
    style_info: Dict[str, Any]
    colors_used: List[str]
    generation_time: float
    confidence_score: float
    prompt_used: str  # The actual prompt sent to DALL-E
    dalle_revised_prompt: Optional[str] = None  # DALL-E's revised prompt

class UserFeedback(BaseModel):
    logo_id: str
    rating: int = Field(..., ge=1, le=5)
    feedback_text: Optional[str] = None

# ================== REAL AI LOGO GENERATOR ==================
class RealAILogoGenerator:
    """Real AI-powered logo generation using DALL-E 3"""
    
    # Style-specific prompt templates
    STYLE_PROMPTS = {
        'modern': "A clean, minimalist, modern logo design for {business_name}, a {industry} company. Simple geometric shapes, contemporary typography, flat design style, professional and sleek appearance",
        
        'vintage': "A vintage-style retro logo for {business_name}, a {industry} business. Classic typography, aged aesthetic, traditional design elements, nostalgic feel, muted color palette",
        
        'bold': "A bold, strong, impactful logo design for {business_name} in the {industry} industry. Thick typography, powerful visual elements, high contrast, commanding presence",
        
        'elegant': "An elegant, sophisticated, luxury logo for {business_name}, a {industry} company. Refined typography, graceful design elements, premium aesthetic, classy appearance",
        
        'playful': "A fun, creative, playful logo design for {business_name} in {industry}. Whimsical elements, bright colors, friendly appearance, approachable design",
        
        'professional': "A corporate, professional, trustworthy logo for {business_name}, a {industry} business. Clean typography, business-appropriate design, reliable and credible appearance"
    }
    
    # Industry-specific additions
    INDUSTRY_ELEMENTS = {
        'technology': "incorporating tech elements like circuits, gears, or digital motifs",
        'healthcare': "with medical cross, caduceus, or health-related symbols",
        'finance': "featuring financial symbols, charts, or stability indicators",
        'retail': "with shopping or commerce-related elements",
        'food & beverage': "incorporating food, dining, or culinary elements",
        'education': "with books, graduation caps, or learning symbols",
        'real estate': "featuring houses, buildings, or property elements",
        'consulting': "with professional advisory or business growth symbols",
        'creative services': "incorporating artistic, creative, or design elements",
        'manufacturing': "with industrial, production, or machinery elements"
    }
    
    @staticmethod
    def generate_logo_prompt(business_name: str, industry: str, style: str, 
                           colors: List[str], description: str = "") -> str:
        """Generate detailed prompt for DALL-E 3"""
        
        # Base prompt from style
        base_prompt = RealAILogoGenerator.STYLE_PROMPTS.get(style, RealAILogoGenerator.STYLE_PROMPTS['modern'])
        prompt = base_prompt.format(business_name=business_name, industry=industry)
        
        # Add industry-specific elements
        industry_addition = RealAILogoGenerator.INDUSTRY_ELEMENTS.get(industry.lower(), "")
        if industry_addition:
            prompt += f", {industry_addition}"
        
        # Add color information
        if colors:
            color_names = []
            for color in colors[:3]:  # Max 3 colors for clarity
                # Convert hex to color name (simplified)
                color_map = {
                    '#3B82F6': 'blue', '#1E40AF': 'dark blue',
                    '#EF4444': 'red', '#DC2626': 'dark red',
                    '#10B981': 'green', '#059669': 'emerald',
                    '#F59E0B': 'orange', '#D97706': 'amber',
                    '#8B5CF6': 'purple', '#7C3AED': 'violet',
                    '#6B7280': 'gray', '#374151': 'dark gray',
                    '#EC4899': 'pink', '#BE185D': 'rose',
                    '#14B8A6': 'teal', '#0D9488': 'cyan'
                }
                color_names.append(color_map.get(color, 'custom color'))
            
            prompt += f". Use colors: {', '.join(color_names)}"
        
        # Add business description if provided
        if description:
            prompt += f". Business focus: {description}"
        
        # Logo-specific requirements
        prompt += ". Logo should be suitable for business cards and websites, vector-style design, white background, no text overlays, icon-style logo design"
        
        return prompt
    
    @staticmethod
    async def generate_dalle_logo(prompt: str, size: str = "1024x1024") -> Dict[str, Any]:
        """Generate logo using DALL-E 3"""
        try:
            print(f"🎨 Generating with DALL-E 3...")
            print(f"📝 Prompt: {prompt[:100]}...")
            
            response = await client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality="hd",  # High quality for logos
                style="vivid",  # More creative and hyper-real
                n=1  # DALL-E 3 only supports n=1
            )
            
            image_data = response.data[0]
            
            return {
                'success': True,
                'image_url': image_data.url,
                'revised_prompt': image_data.revised_prompt,
                'original_prompt': prompt
            }
            
        except Exception as e:
            print(f"❌ DALL-E Error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"DALL-E generation failed: {str(e)}")
    
    @staticmethod
    async def download_and_save_image(image_url: str, logo_id: str, base_url: str = "http://localhost:8000") -> tuple[str, str]:
        """Download image from DALL-E URL and save locally - Returns (local_url, local_path)"""
        try:
            print(f"📥 Downloading image for logo {logo_id}...")
            
            # Download image with timeout and retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.get(image_url, timeout=30)
                    response.raise_for_status()
                    break
                except requests.exceptions.RequestException as e:
                    print(f"⚠️ Download attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(2)  # Wait before retry
            
            # Save original PNG
            png_path = f"generated_logos/{logo_id}.png"
            with open(png_path, 'wb') as f:
                f.write(response.content)
            
            # Also create JPEG version
            img = Image.open(BytesIO(response.content))
            
            # Create white background for JPEG (remove transparency)
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img, mask=img.split()[-1] if len(img.split()) > 1 else None)
                img = background
            
            jpeg_path = f"generated_logos/{logo_id}.jpg"
            img.save(jpeg_path, 'JPEG', quality=95)
            
            # Return local URL that will be served by FastAPI
            local_url = f"{base_url}/static/logos/{logo_id}.png"
            
            print(f"✅ Images saved: {png_path}, {jpeg_path}")
            print(f"🌐 Local URL: {local_url}")
            
            return local_url, png_path
            
        except Exception as e:
            print(f"❌ Image save error: {str(e)}")
            # Return the original DALL-E URL as fallback
            return image_url, ""
    
    @staticmethod
    async def generate_real_ai_logos(request: LogoGenerationRequest, base_url: str = "http://localhost:8000") -> List[LogoResponse]:
        """Generate real AI logos using DALL-E 3"""
        start_time = time.time()
        logos = []
        
        try:
            # Generate variations by modifying the prompt
            base_prompt = RealAILogoGenerator.generate_logo_prompt(
                request.business_info.name,
                request.business_info.industry,
                request.style.style_type,
                request.style.color_palette,
                request.business_info.description or ""
            )
            
            # Create variations
            variations = [
                base_prompt,
                base_prompt + ", circular badge design, emblem style",
                base_prompt + ", horizontal layout, text and icon combination",
                base_prompt + ", abstract symbol, iconic representation"
            ]
            
            for i in range(min(request.variations, len(variations))):
                print(f"🎯 Generating variation {i+1}/{request.variations}")
                
                # Generate with DALL-E 3
                dalle_result = await RealAILogoGenerator.generate_dalle_logo(variations[i])
                
                if dalle_result['success']:
                    logo_id = hashlib.md5(f"{request.business_info.name}_{i}_{time.time()}".encode()).hexdigest()[:12]
                    
                    # Download and save image locally
                    local_url, local_path = await RealAILogoGenerator.download_and_save_image(
                        dalle_result['image_url'], 
                        logo_id,
                        base_url
                    )
                    
                    logo = LogoResponse(
                        id=logo_id,
                        name=f"{request.business_info.name} - AI Design {i+1}",
                        image_url=local_url,  # Use local URL instead of DALL-E URL
                        dalle_url=dalle_result['image_url'],  # Keep original for reference
                        local_path=local_path,
                        style_info={
                            "style": request.style.style_type,
                            "variation": i+1,
                            "ai_model": "DALL-E 3",
                            "quality": "HD",
                            "industry": request.business_info.industry,
                            "generation_method": "Real AI Generation"
                        },
                        colors_used=request.style.color_palette,
                        generation_time=time.time() - start_time,
                        confidence_score=0.95,  # High confidence for DALL-E 3
                        prompt_used=variations[i],
                        dalle_revised_prompt=dalle_result.get('revised_prompt')
                    )
                    
                    logos.append(logo)
                    print(f"✅ Generated logo {i+1}: {logo_id}")
                
                # Small delay between requests to respect rate limits
                if i < request.variations - 1:
                    await asyncio.sleep(2)  # Increased delay
            
            return logos
            
        except Exception as e:
            print(f"❌ Real AI Logo Generation Error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Real AI generation failed: {str(e)}")

# ================== API ENDPOINTS ==================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print("🚀 Starting Real AI LogoAI Backend with DALL-E 3...")
    
    # Test OpenAI connection
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ CRITICAL: OPENAI_API_KEY not found!")
        print("💡 Add your OpenAI API key to .env file")
        return
    
    try:
        # Test DALL-E access (skip test to avoid unnecessary costs)
        print("✅ OpenAI API key configured!")
        print("💰 Note: DALL-E 3 costs ~$0.04-0.08 per image")
    except Exception as e:
        print(f"⚠️ OpenAI connection test failed: {str(e)}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Real AI LogoAI Backend with DALL-E 3",
        "version": "3.0.0",
        "status": "healthy",
        "features": [
            "DALL-E 3 AI Generation", 
            "HD Quality Images", 
            "Real AI-Powered Logos",
            "PNG & JPEG Export",
            "Local Image Serving"
        ],
        "pricing_info": "~$0.04-0.08 per logo generation",
        "timestamp": datetime.utcnow().isoformat(),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "endpoints": {
            "generate": "/api/v1/generate-logos",
            "download": "/api/v1/logo/{logo_id}/download/{format}",
            "static_images": "/static/logos/{logo_id}.{format}"
        }
    }

@app.post("/api/v1/generate-logos", response_model=Dict[str, Any])
async def generate_real_ai_logos_endpoint(request: LogoGenerationRequest):
    """Generate real AI-powered logos using DALL-E 3"""
    try:
        print(f"🎨 Generating REAL AI logos for: {request.business_info.name}")
        print(f"💰 Estimated cost: ${0.04 * request.variations:.2f}")
        
        # Rate limiting (more strict for paid API)
        client_id = "anonymous"
        current_time = time.time()
        if client_id in rate_limits:
            if current_time - rate_limits[client_id]["last_request"] < 60:  # 1 minute between requests
                raise HTTPException(
                    status_code=429, 
                    detail="Please wait 60 seconds between AI logo generations"
                )
        
        rate_limits[client_id] = {"last_request": current_time}
        
        # Check OpenAI API key
        if not os.getenv("OPENAI_API_KEY"):
            raise HTTPException(
                status_code=500,
                detail="OpenAI API key not configured. Add OPENAI_API_KEY to your .env file"
            )
        
        # Generate real AI logos with local serving
        logos = await RealAILogoGenerator.generate_real_ai_logos(request, "http://localhost:8000")
        
        total_cost = len(logos) * 0.04  # Approximate cost
        print(f"✅ Generated {len(logos)} real AI logos!")
        print(f"💰 Approximate cost: ${total_cost:.2f}")
        
        return {
            "success": True,
            "data": {
                "logos": logos,
                "generation_stats": {
                    "total_time": logos[0].generation_time if logos else 0,
                    "logos_generated": len(logos),
                    "ai_model": "DALL-E 3",
                    "quality": "HD",
                    "approximate_cost": f"${total_cost:.2f}",
                    "real_ai_generated": True,
                    "locally_served": True
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error generating real AI logos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Real AI generation failed: {str(e)}")

@app.get("/api/v1/logo/{logo_id}/download/{format}")
async def download_logo(logo_id: str, format: str):
    """Download generated logo in specified format"""
    try:
        if format not in ['png', 'jpg', 'jpeg']:
            raise HTTPException(status_code=400, detail="Format must be png, jpg, or jpeg")
        
        file_extension = 'jpg' if format in ['jpg', 'jpeg'] else 'png'
        file_path = f"generated_logos/{logo_id}.{file_extension}"
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"Logo file not found: {file_path}")
        
        return FileResponse(
            path=file_path,
            filename=f"{logo_id}.{file_extension}",
            media_type=f"image/{file_extension}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Download error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.get("/api/v1/logo/{logo_id}/info")
async def get_logo_info(logo_id: str):
    """Get information about a logo"""
    try:
        png_path = f"generated_logos/{logo_id}.png"
        jpg_path = f"generated_logos/{logo_id}.jpg"
        
        return {
            "logo_id": logo_id,
            "png_exists": os.path.exists(png_path),
            "jpg_exists": os.path.exists(jpg_path),
            "png_url": f"http://localhost:8000/static/logos/{logo_id}.png" if os.path.exists(png_path) else None,
            "jpg_url": f"http://localhost:8000/static/logos/{logo_id}.jpg" if os.path.exists(jpg_path) else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Info retrieval failed: {str(e)}")

@app.post("/api/v1/feedback")
async def submit_feedback(feedback: UserFeedback):
    """Submit feedback for generated logo"""
    try:
        print(f"📝 Real AI Feedback - Logo: {feedback.logo_id}, Rating: {feedback.rating}/5")
        if feedback.feedback_text:
            print(f"💬 Comment: {feedback.feedback_text}")
        
        # In production, store feedback to improve prompts
        return {
            "success": True,
            "message": "Feedback recorded for AI improvement"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feedback failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting REAL AI LogoAI Backend with DALL-E 3...")
    print("📍 Backend URL: http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    print("🎨 Features: Real DALL-E 3 AI Generation")
    print("💰 Cost: ~$0.04-0.08 per logo")
    print("🔑 CRITICAL: Set OPENAI_API_KEY in .env file!")
    print("💳 Make sure you have OpenAI API credits!")
    print("📁 Images will be saved locally and served at /static/logos/")
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)