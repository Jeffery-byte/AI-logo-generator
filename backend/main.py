# main.py - Enhanced Google Vertex AI Imagen Logo Generator Backend
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json
import hashlib
import time
import asyncio
from datetime import datetime
import requests
import base64
from io import BytesIO
from PIL import Image
import os
from dotenv import load_dotenv
import logging
from google.auth import default
from google.auth.transport.requests import Request
import google.auth

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================== CONFIGURATION ==================
app = FastAPI(
    title="Vertex AI Imagen Logo Generator - Enhanced Version",
    description="Professional logo generation using Google's Vertex AI Imagen with business context integration",
    version="8.1.0-enhanced"
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

# Get Google Cloud Configuration
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Initialize credentials
CREDENTIALS = None
PROJECT_ID = None

def initialize_google_auth():
    global CREDENTIALS, PROJECT_ID
    try:
        if GOOGLE_APPLICATION_CREDENTIALS and os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
            # Use service account file
            CREDENTIALS, PROJECT_ID = default()
            logger.info(f"✅ Using service account credentials: {GOOGLE_APPLICATION_CREDENTIALS}")
        elif GOOGLE_CLOUD_PROJECT:
            # Use default credentials with explicit project
            CREDENTIALS, _ = default()
            PROJECT_ID = GOOGLE_CLOUD_PROJECT
            logger.info(f"✅ Using default credentials with project: {PROJECT_ID}")
        else:
            # Try default credentials
            CREDENTIALS, PROJECT_ID = default()
            logger.info(f"✅ Using default credentials, detected project: {PROJECT_ID}")
        
        # Refresh credentials
        if CREDENTIALS.expired:
            CREDENTIALS.refresh(Request())
            
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize Google credentials: {str(e)}")
        return False

# Rate limiting
rate_limits = {}

# Create directories
os.makedirs("generated_logos", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Mount static files
app.mount("/static/logos", StaticFiles(directory="generated_logos"), name="logos")

# ================== DATA MODELS ==================
class BusinessInfo(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    industry: str = Field(..., min_length=1)
    description: Optional[str] = Field(None, max_length=200)
    target_audience: Optional[str] = Field(None, max_length=100)

class LogoStyle(BaseModel):
    style_type: str = Field(..., pattern="^(modern|vintage|bold|elegant|playful|professional)$")
    color_palette: List[str] = Field(..., min_items=1, max_items=3)
    font_preference: Optional[str] = "sans-serif"

class LogoGenerationRequest(BaseModel):
    business_info: BusinessInfo
    style: LogoStyle
    variations: Optional[int] = Field(1, ge=1, le=2)
    imagen_model: Optional[str] = Field("imagegeneration@006", pattern="^(imagegeneration@006|imagegeneration@005)$")

class LogoResponse(BaseModel):
    id: str
    name: str
    image_url: str
    local_path: Optional[str] = None
    style_info: Dict[str, Any]
    colors_used: List[str]
    generation_time: float
    confidence_score: float
    prompt_used: str

class GenerationStats(BaseModel):
    total_time: float
    logos_generated: int
    ai_model: str
    quality: str
    approximate_cost: str
    real_ai_generated: bool

# ================== ENHANCED VERTEX AI IMAGEN GENERATOR ==================

class VertexImagenLogoGenerator:
    """Generate professional logos using Google Vertex AI Imagen with enhanced business context"""
    
    # Updated model configuration for Vertex AI
    VERTEX_MODELS = {
        "imagegeneration@006": {
            "base_url": "https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/google/models/imagegeneration@006:predict",
            "cost": 0.03,
            "description": "Latest Imagen model with improved quality"
        },
        "imagegeneration@005": {
            "base_url": "https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/google/models/imagegeneration@005:predict",
            "cost": 0.025,
            "description": "Previous generation Imagen model"
        }
    }
    
    # Default location for Vertex AI
    DEFAULT_LOCATION = "us-central1"
    
    # Enhanced logo prompts optimized for Vertex AI Imagen
    IMAGEN_LOGO_PROMPTS = {
        'modern': [
            "A clean, minimalist logo for {business_name}. Simple geometric design with {colors} colors on white background. Professional vector style, high contrast, crisp edges."
        ],
        'vintage': [
            "A vintage-style logo for {business_name}. Classic retro design with {colors} colors on white background. Traditional typography, decorative elements."
        ],
        'bold': [
            "A bold, impactful logo for {business_name}. Strong, powerful design with {colors} colors on white background. Thick lines, dramatic contrast."
        ],
        'elegant': [
            "An elegant, sophisticated logo for {business_name}. Refined luxury design with {colors} colors on white background. Graceful curves, premium feel."
        ],
        'playful': [
            "A fun, creative logo for {business_name}. Playful design with {colors} colors on white background. Friendly, approachable style."
        ],
        'professional': [
            "A professional, corporate logo for {business_name}. Business-appropriate design with {colors} colors on white background. Trustworthy, reliable appearance."
        ]
    }
    
    COLOR_NAMES = {
        '#3B82F6': 'blue', '#1E40AF': 'navy blue',
        '#EF4444': 'red', '#DC2626': 'dark red',
        '#10B981': 'green', '#059669': 'emerald green',
        '#F59E0B': 'orange', '#D97706': 'amber orange',
        '#8B5CF6': 'purple', '#7C3AED': 'violet purple',
        '#6B7280': 'gray', '#374151': 'dark gray',
        '#EC4899': 'pink', '#BE185D': 'deep pink',
        '#14B8A6': 'teal', '#0D9488': 'dark teal',
        '#000000': 'black', '#FFFFFF': 'white'
    }
    
    @staticmethod
    def get_access_token() -> str:
        """Get access token for Vertex AI API"""
        global CREDENTIALS
        if not CREDENTIALS:
            raise Exception("Credentials not initialized")
        
        if CREDENTIALS.expired:
            CREDENTIALS.refresh(Request())
        
        return CREDENTIALS.token
    
    @staticmethod
    def create_vertex_prompts(business_name: str, industry: str, style: str, colors: List[str], variations: int = 1, 
                             business_description: Optional[str] = None, target_audience: Optional[str] = None) -> List[str]:
        """Create optimized prompts for Vertex AI Imagen with business context and proper variations"""
        
        # Sanitize business name
        safe_name = business_name.replace("&", "and").strip()
        
        # Convert colors to natural language
        color_names = []
        for color in colors[:2]:  # Use max 2 colors
            color_names.append(VertexImagenLogoGenerator.COLOR_NAMES.get(color, 'blue'))
        
        color_text = ' and '.join(color_names) if len(color_names) > 1 else color_names[0] if color_names else "blue"
        
        # Get base prompt template
        templates = VertexImagenLogoGenerator.IMAGEN_LOGO_PROMPTS.get(style, 
            VertexImagenLogoGenerator.IMAGEN_LOGO_PROMPTS['modern'])
        
        base_template = templates[0]  # Use the first template
        
        # Build contextual elements from business description
        context_elements = []
        
        if business_description and business_description.strip():
            desc = business_description.strip().lower()
            
            # Extract key concepts from description to enhance the logo
            if any(word in desc for word in ['tech', 'software', 'digital', 'app', 'platform', 'system']):
                context_elements.append("incorporating subtle tech-inspired elements")
            elif any(word in desc for word in ['food', 'restaurant', 'cafe', 'kitchen', 'dining']):
                context_elements.append("with food-related symbolic elements")
            elif any(word in desc for word in ['health', 'medical', 'wellness', 'fitness', 'care']):
                context_elements.append("featuring health and wellness symbolism")
            elif any(word in desc for word in ['finance', 'money', 'investment', 'banking', 'financial']):
                context_elements.append("with financial stability and trust symbols")
            elif any(word in desc for word in ['education', 'school', 'learning', 'teaching', 'training']):
                context_elements.append("incorporating educational and growth elements")
            elif any(word in desc for word in ['creative', 'design', 'art', 'artistic', 'studio']):
                context_elements.append("with creative and artistic flair")
            elif any(word in desc for word in ['service', 'consulting', 'professional', 'expert']):
                context_elements.append("emphasizing professionalism and expertise")
            elif any(word in desc for word in ['eco', 'green', 'sustainable', 'environment', 'natural']):
                context_elements.append("with eco-friendly and natural elements")
            elif any(word in desc for word in ['luxury', 'premium', 'high-end', 'exclusive']):
                context_elements.append("with luxury and premium aesthetics")
            elif any(word in desc for word in ['fun', 'entertainment', 'game', 'play', 'joy']):
                context_elements.append("with playful and entertaining elements")
            else:
                # Generic enhancement based on description keywords
                context_elements.append(f"reflecting the essence of {desc[:50]}...")
        
        # Add industry-specific enhancements
        industry_lower = industry.lower()
        if 'technology' in industry_lower and 'tech-inspired' not in str(context_elements):
            context_elements.append("with modern technology aesthetics")
        elif 'healthcare' in industry_lower and 'health' not in str(context_elements):
            context_elements.append("conveying trust and care")
        elif 'finance' in industry_lower and 'financial' not in str(context_elements):
            context_elements.append("symbolizing stability and growth")
        elif 'retail' in industry_lower:
            context_elements.append("appealing to consumers with inviting design")
        elif 'education' in industry_lower and 'educational' not in str(context_elements):
            context_elements.append("inspiring learning and development")
        elif 'real estate' in industry_lower:
            context_elements.append("representing stability and home")
        elif 'consulting' in industry_lower and 'professional' not in str(context_elements):
            context_elements.append("projecting expertise and reliability")
        elif 'food' in industry_lower and 'food-related' not in str(context_elements):
            context_elements.append("with appetizing and welcoming elements")
        elif 'creative' in industry_lower and 'creative' not in str(context_elements):
            context_elements.append("showcasing creativity and innovation")
        elif 'manufacturing' in industry_lower:
            context_elements.append("representing quality and precision")
        
        # Add target audience considerations
        if target_audience and target_audience.strip():
            audience = target_audience.strip().lower()
            if any(word in audience for word in ['young', 'millennial', 'gen z', 'youth']):
                context_elements.append("with contemporary appeal for younger demographics")
            elif any(word in audience for word in ['professional', 'business', 'corporate']):
                context_elements.append("tailored for professional audiences")
            elif any(word in audience for word in ['family', 'parent', 'children', 'kids']):
                context_elements.append("family-friendly and approachable")
            elif any(word in audience for word in ['luxury', 'affluent', 'premium', 'high-income']):
                context_elements.append("designed for discerning, upscale clientele")
        
        # Create variations with different approaches
        variation_approaches = [
            "",  # Original version
            "with subtle gradients and modern typography",
            "featuring clean geometric shapes and professional styling", 
            "incorporating elegant design elements and premium finish",
            "with contemporary aesthetics and refined details",
            "emphasizing brand recognition and memorability",
            "with balanced composition and visual hierarchy",
            "featuring distinctive character and market appeal"
        ]
        
        prompts = []
        for i in range(variations):
            # Start with base prompt
            base_prompt = base_template.format(
                business_name=safe_name,
                colors=color_text
            )
            
            # Build the enhanced prompt
            prompt_parts = [base_prompt]
            
            # Add context elements (rotate through them for variations)
            if context_elements:
                context_to_use = context_elements[i % len(context_elements)]
                prompt_parts.append(context_to_use)
            
            # Add variation approach
            approach = variation_approaches[i % len(variation_approaches)]
            if approach:
                prompt_parts.append(approach)
            
            # Combine all parts
            enhanced_prompt = " ".join(prompt_parts).replace("  ", " ").strip()
            
            # Ensure prompt isn't too long (Vertex AI has limits)
            if len(enhanced_prompt) > 400:
                enhanced_prompt = enhanced_prompt[:400] + "..."
            
            prompts.append(enhanced_prompt)
            
            # Log the enhanced prompt
            logger.info(f"🎨 Created enhanced prompt {i+1}/{variations}:")
            logger.info(f"   📝 Base: {base_prompt}")
            if context_elements:
                logger.info(f"   🎯 Context: {context_elements[i % len(context_elements)]}")
            if approach:
                logger.info(f"   ✨ Style: {approach}")
            logger.info(f"   🔗 Final: {enhanced_prompt}")
        
        return prompts
    
    @staticmethod
    async def generate_vertex_imagen_logo(prompt: str, model: str = "imagegeneration@006", location: str = None) -> Dict[str, Any]:
        """Generate logo using Vertex AI Imagen with proper authentication"""
        try:
            if not location:
                location = VertexImagenLogoGenerator.DEFAULT_LOCATION
                
            logger.info(f"🎨 Starting Vertex AI Imagen generation with {model}")
            logger.info(f"📍 Location: {location}")
            logger.info(f"📝 Prompt: {prompt}")
            
            # Check credentials
            if not CREDENTIALS or not PROJECT_ID:
                raise Exception("Google Cloud credentials not properly initialized")
            
            # Get access token
            access_token = VertexImagenLogoGenerator.get_access_token()
            
            # Get model configuration
            if model not in VertexImagenLogoGenerator.VERTEX_MODELS:
                raise Exception(f"Unsupported model: {model}")
            
            model_config = VertexImagenLogoGenerator.VERTEX_MODELS[model]
            endpoint = model_config["base_url"].format(
                project=PROJECT_ID,
                location=location
            )
            
            # Prepare Vertex AI request payload
            payload = {
                "instances": [
                    {
                        "prompt": prompt
                    }
                ],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": "1:1",
                    "safetyFilterLevel": "block_some",
                    "personGeneration": "dont_allow"
                }
            }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"🌐 Making request to: {endpoint}")
            
            # Make the request
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=60
            )
            
            logger.info(f"📊 Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Received successful response from Vertex AI")
                
                # Extract predictions from Vertex AI response
                if "predictions" in result and len(result["predictions"]) > 0:
                    images_data = []
                    
                    for i, prediction in enumerate(result["predictions"]):
                        logger.info(f"🖼️ Processing prediction {i}")
                        
                        if "bytesBase64Encoded" in prediction:
                            try:
                                image_data = base64.b64decode(prediction["bytesBase64Encoded"])
                                images_data.append({
                                    'image_data': image_data,
                                    'mime_type': 'image/png',
                                    'index': i
                                })
                                logger.info(f"✅ Successfully decoded image {i}: {len(image_data)} bytes")
                            except Exception as decode_error:
                                logger.error(f"❌ Failed to decode image {i}: {str(decode_error)}")
                        else:
                            logger.error(f"❌ No bytesBase64Encoded in prediction {i}")
                    
                    if images_data:
                        logger.info(f"✅ Generated {len(images_data)} image(s) successfully with Vertex AI")
                        return {
                            'success': True,
                            'images': images_data,
                            'original_prompt': prompt,
                            'model': model,
                            'location': location,
                            'raw_response': result
                        }
                    else:
                        return {
                            'success': False,
                            'error': 'No valid images in response',
                            'raw_response': result
                        }
                else:
                    logger.error("❌ No predictions found in Vertex AI response")
                    return {
                        'success': False,
                        'error': 'No predictions in response',
                        'raw_response': result
                    }
            else:
                error_text = response.text if response.content else "No error details"
                logger.error(f"❌ Vertex AI HTTP {response.status_code}: {error_text}")
                
                return {
                    'success': False,
                    'error': f"Vertex AI HTTP {response.status_code}: {error_text}",
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Vertex AI Imagen generation exception: {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
    
    @staticmethod
    async def save_vertex_logo(image_data: bytes, logo_id: str, variation: int, base_url: str = "http://localhost:8000") -> tuple[str, str]:
        """Save Vertex AI Imagen logo locally"""
        try:
            logger.info(f"💾 Saving Vertex AI Imagen logo: {logo_id} (v{variation})")
            
            if not image_data or len(image_data) < 100:
                raise Exception("Invalid or empty image data")
            
            # Save PNG
            png_path = f"generated_logos/{logo_id}_v{variation}.png"
            with open(png_path, 'wb') as f:
                f.write(image_data)
            logger.info(f"✅ PNG saved: {png_path}")
            
            local_url = f"{base_url}/static/logos/{logo_id}_v{variation}.png"
            return local_url, png_path
            
        except Exception as e:
            logger.error(f"❌ Save error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to save logo: {str(e)}")
    
    @staticmethod
    async def create_vertex_logos(request: LogoGenerationRequest, base_url: str = "http://localhost:8000") -> List[LogoResponse]:
        """Create professional logos using Vertex AI Imagen with enhanced business context"""
        start_time = time.time()
        
        try:
            variations = getattr(request, 'variations', 1)
            variations = min(max(variations, 1), 2)
            
            model = getattr(request, 'imagen_model', 'imagegeneration@006')
            
            logger.info(f"🎯 Creating {variations} enhanced Vertex AI Imagen logo(s) for: {request.business_info.name}")
            logger.info(f"🤖 Using model: {model}")
            logger.info(f"🏢 Industry: {request.business_info.industry}")
            if request.business_info.description:
                logger.info(f"📝 Description: {request.business_info.description}")
            if request.business_info.target_audience:
                logger.info(f"🎯 Target Audience: {request.business_info.target_audience}")
            
            # Validate request
            if not request.business_info.name.strip():
                raise HTTPException(status_code=400, detail="Business name cannot be empty")
            
            # Create enhanced prompts with business context
            prompts = VertexImagenLogoGenerator.create_vertex_prompts(
                request.business_info.name,
                request.business_info.industry,
                request.style.style_type,
                request.style.color_palette,
                variations,
                request.business_info.description,  # Now includes description
                request.business_info.target_audience  # Now includes target audience
            )
            
            logos = []
            base_id = hashlib.md5(f"{request.business_info.name}_{time.time()}".encode()).hexdigest()[:12]
            successful_generations = 0
            errors = []
            
            for i, prompt in enumerate(prompts):
                try:
                    logger.info(f"🔄 Generating logo {i+1}/{len(prompts)} with Vertex AI")
                    
                    # Generate logo with Vertex AI
                    vertex_result = await VertexImagenLogoGenerator.generate_vertex_imagen_logo(prompt, model)
                    
                    if vertex_result.get('success') and vertex_result.get('images'):
                        for img_idx, img_data in enumerate(vertex_result['images']):
                            logo_id = f"{base_id}_{i+1}_{img_idx+1}"
                            variation_num = successful_generations + 1
                            
                            # Save logo
                            local_url, local_path = await VertexImagenLogoGenerator.save_vertex_logo(
                                img_data['image_data'], 
                                base_id,
                                variation_num,
                                base_url
                            )
                            
                            logo = LogoResponse(
                                id=logo_id,
                                name=f"{request.business_info.name} Logo (Vertex AI {variation_num})",
                                image_url=local_url,
                                local_path=local_path,
                                style_info={
                                    "style": request.style.style_type,
                                    "variation": variation_num,
                                    "ai_model": f"Google Vertex AI {model}",
                                    "quality": "Professional HD",
                                    "industry": request.business_info.industry,
                                    "generation_method": "Enhanced Vertex AI Imagen Generation",
                                    "location": vertex_result.get('location', 'us-central1'),
                                    "business_context": "Enhanced with business description" if request.business_info.description else "Standard generation"
                                },
                                colors_used=request.style.color_palette[:2],
                                generation_time=time.time() - start_time,
                                confidence_score=0.95,
                                prompt_used=prompt
                            )
                            
                            logos.append(logo)
                            successful_generations += 1
                            logger.info(f"✅ Created enhanced Vertex AI logo {variation_num}: {logo_id}")
                    else:
                        error_msg = vertex_result.get('error', 'Unknown error')
                        logger.error(f"❌ Failed to create Vertex AI logo {i+1}: {error_msg}")
                        errors.append(f"Logo {i+1}: {error_msg}")
                        
                except Exception as e:
                    logger.error(f"❌ Failed to create Vertex AI logo {i+1}: {str(e)}")
                    errors.append(f"Logo {i+1}: {str(e)}")
                    continue
            
            if not logos:
                error_summary = "; ".join(errors) if errors else "Unknown errors occurred"
                raise HTTPException(
                    status_code=500, 
                    detail=f"All Vertex AI logo generations failed. Errors: {error_summary}"
                )
            
            logger.info(f"✅ Successfully generated {len(logos)} out of {variations} requested enhanced logos with Vertex AI")
            return logos
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Vertex AI logo creation error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Vertex AI logo creation failed: {str(e)}")

# ================== COMPREHENSIVE DIAGNOSTICS ==================

class VertexAIDiagnostics:
    """Comprehensive diagnostics for Vertex AI setup"""
    
    @staticmethod
    async def full_vertex_diagnostic() -> Dict[str, Any]:
        """Run comprehensive diagnostics on Vertex AI setup"""
        results = {
            "credentials_status": "unknown",
            "project_status": "unknown",
            "vertex_api_access": "unknown",
            "model_access": {},
            "recommendations": []
        }
        
        # Test 1: Check credentials initialization
        try:
            auth_success = initialize_google_auth()
            if auth_success and CREDENTIALS and PROJECT_ID:
                results["credentials_status"] = "valid"
                results["project_status"] = f"detected: {PROJECT_ID}"
                logger.info(f"✅ Credentials valid, project: {PROJECT_ID}")
            else:
                results["credentials_status"] = "invalid"
                results["recommendations"].append("Set up Google Cloud authentication (service account or gcloud auth)")
                return results
                
        except Exception as e:
            results["credentials_status"] = f"error: {str(e)}"
            results["recommendations"].append("Check Google Cloud SDK installation and authentication")
            return results
        
        # Test 2: Test Vertex AI API access
        try:
            logger.info("🔍 Testing Vertex AI API access...")
            
            access_token = VertexImagenLogoGenerator.get_access_token()
            
            # Test with a simple Vertex AI endpoint (list models)
            test_url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/us-central1/models"
            
            response = requests.get(
                test_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
            
            logger.info(f"📊 Vertex AI test response: {response.status_code}")
            
            if response.status_code == 200:
                results["vertex_api_access"] = "working"
                logger.info("✅ Vertex AI API access confirmed")
            elif response.status_code == 403:
                results["vertex_api_access"] = "forbidden"
                results["recommendations"].append("Enable Vertex AI API in Google Cloud Console and check billing")
            elif response.status_code == 401:
                results["vertex_api_access"] = "unauthorized"
                results["recommendations"].append("Check authentication credentials and permissions")
            else:
                results["vertex_api_access"] = f"error_{response.status_code}"
                results["recommendations"].append(f"Vertex AI API returned {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Vertex AI test failed: {str(e)}")
            results["vertex_api_access"] = f"error: {str(e)}"
            results["recommendations"].append("Check network connectivity and Vertex AI API configuration")
        
        # Test 3: Test Imagen model access
        if results["vertex_api_access"] == "working":
            try:
                logger.info("🎨 Testing Imagen model access...")
                
                test_result = await VertexImagenLogoGenerator.generate_vertex_imagen_logo(
                    "simple blue circle", 
                    "imagegeneration@006"
                )
                
                if test_result.get('success'):
                    results["model_access"]["imagegeneration@006"] = "working"
                    logger.info("✅ Imagen model access confirmed")
                else:
                    results["model_access"]["imagegeneration@006"] = f"failed: {test_result.get('error', 'unknown')}"
                    results["recommendations"].append("Check Imagen API availability and billing")
                    
            except Exception as e:
                results["model_access"]["imagegeneration@006"] = f"error: {str(e)}"
                results["recommendations"].append("Imagen model test failed - check API permissions")
        
        return results

# ================== API ENDPOINTS ==================

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Enhanced Vertex AI Imagen Logo Generator Starting...")
    logger.info("✨ NEW: Business description and target audience integration!")
    
    # Initialize Google Cloud authentication
    auth_success = initialize_google_auth()
    
    if not auth_success:
        logger.error("❌ CRITICAL: Google Cloud authentication failed!")
        logger.error("💡 Setup instructions:")
        logger.error("   1. Install Google Cloud SDK: https://cloud.google.com/sdk/docs/install")
        logger.error("   2. Run: gcloud auth application-default login")
        logger.error("   3. OR set GOOGLE_APPLICATION_CREDENTIALS to service account file")
        logger.error("   4. Set GOOGLE_CLOUD_PROJECT environment variable")
        logger.error("   5. Enable Vertex AI API in Google Cloud Console")
        logger.error("   6. Enable billing for your project")
        return
    
    # Run comprehensive diagnostics
    logger.info("🔍 Running comprehensive Vertex AI diagnostics...")
    diagnostic_results = await VertexAIDiagnostics.full_vertex_diagnostic()
    
    logger.info("🏥 Diagnostic Results:")
    logger.info(f"  Credentials: {diagnostic_results['credentials_status']}")
    logger.info(f"  Project: {diagnostic_results['project_status']}")
    logger.info(f"  Vertex AI Access: {diagnostic_results['vertex_api_access']}")
    logger.info(f"  Model Access: {diagnostic_results['model_access']}")
    
    if diagnostic_results['recommendations']:
        logger.info("💡 Recommendations:")
        for rec in diagnostic_results['recommendations']:
            logger.info(f"  • {rec}")
    
    if (diagnostic_results['credentials_status'] == 'valid' and 
        diagnostic_results['vertex_api_access'] == 'working' and
        diagnostic_results['model_access'].get('imagegeneration@006') == 'working'):
        logger.info("✅ All systems ready for enhanced Vertex AI Imagen logo generation!")
    else:
        logger.warning("⚠️ Some issues detected - check recommendations above")

@app.get("/")
async def root():
    return {
        "message": "Enhanced Vertex AI Imagen Logo Generator with Business Context",
        "version": "8.1.0-enhanced",
        "status": "healthy" if CREDENTIALS and PROJECT_ID else "auth_missing",
        "features": [
            "Google Vertex AI Imagen Generation",
            "Business Description Integration",
            "Target Audience Optimization",
            "Enhanced Prompt Generation",
            "Proper OAuth2 Authentication",
            "Service Account Support",
            "Comprehensive Diagnostics",
            "Professional Logo Design"
        ],
        "models": {
            "imagegeneration@006": "$0.03 per image - Latest Imagen model",
            "imagegeneration@005": "$0.025 per image - Previous generation"
        },
        "enhancements": {
            "business_context": "Logos now reflect business description and industry",
            "target_audience": "Design adapts to specified target demographics",
            "variations": "Multiple meaningful variations per generation",
            "prompt_intelligence": "Enhanced AI prompt generation with context"
        },
        "project_id": PROJECT_ID,
        "credentials_configured": bool(CREDENTIALS),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/diagnostics")
async def run_full_diagnostics():
    """Run comprehensive Vertex AI diagnostics"""
    try:
        logger.info("🔍 Running on-demand Vertex AI diagnostics...")
        
        diagnostic_results = await VertexAIDiagnostics.full_vertex_diagnostic()
        
        return {
            "status": "complete",
            "timestamp": datetime.utcnow().isoformat(),
            "results": diagnostic_results,
            "summary": {
                "ready_for_generation": (
                    diagnostic_results['credentials_status'] == 'valid' and 
                    diagnostic_results['vertex_api_access'] == 'working' and
                    diagnostic_results['model_access'].get('imagegeneration@006') == 'working'
                ),
                "main_issues": diagnostic_results['recommendations'][:3]
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Diagnostics failed: {str(e)}")
        return {
            "status": "error",
            "message": f"Diagnostics failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

@app.post("/api/v1/generate-logos", response_model=Dict[str, Any])
async def generate_vertex_logos_endpoint(request: LogoGenerationRequest):
    """Generate professional logos using enhanced Vertex AI Imagen with business context"""
    try:
        logger.info(f"🎯 Request: Generate enhanced Vertex AI Imagen logos for '{request.business_info.name}'")
        
        # Validate authentication
        if not CREDENTIALS or not PROJECT_ID:
            raise HTTPException(
                status_code=500,
                detail="Google Cloud authentication not configured. Run diagnostics for setup instructions."
            )
        
        model = getattr(request, 'imagen_model', 'imagegeneration@006')
        model_config = VertexImagenLogoGenerator.VERTEX_MODELS.get(model, VertexImagenLogoGenerator.VERTEX_MODELS['imagegeneration@006'])
        cost_per_image = model_config['cost']
        
        logger.info(f"💰 Estimated cost: ${cost_per_image * request.variations:.3f}")
        
        # Rate limiting
        client_id = "anonymous"
        current_time = time.time()
        if client_id in rate_limits:
            time_since_last = current_time - rate_limits[client_id]["last_request"]
            if time_since_last < 30:  # 30 seconds between requests
                wait_time = 30 - time_since_last
                raise HTTPException(
                    status_code=429, 
                    detail=f"Please wait {wait_time:.0f} seconds between logo generations"
                )
        
        rate_limits[client_id] = {"last_request": current_time}
        
        # Generate enhanced Vertex AI Imagen logos
        start_time = time.time()
        logos = await VertexImagenLogoGenerator.create_vertex_logos(request)
        total_time = time.time() - start_time
        
        # Calculate actual cost
        total_cost = len(logos) * cost_per_image
        
        # Create stats
        stats = GenerationStats(
            total_time=total_time,
            logos_generated=len(logos),
            ai_model=f"Google Vertex AI {model}",
            quality="Professional HD Enhanced",
            approximate_cost=f"${total_cost:.3f}",
            real_ai_generated=True
        )
        
        logger.info(f"✅ {len(logos)} enhanced Vertex AI Imagen logos generated successfully!")
        logger.info(f"💰 Actual cost: ${total_cost:.3f}")
        logger.info(f"⏱️ Total time: {total_time:.1f}s")
        
        return {
            "success": True,
            "data": {
                "logos": logos,
                "generation_stats": stats.dict()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/api/v1/logo/{logo_id}/download/{format}")
async def download_logo(logo_id: str, format: str):
    """Download logo in specified format"""
    try:
        if format not in ['png', 'jpg', 'jpeg']:
            raise HTTPException(status_code=400, detail="Format must be png, jpg, or jpeg")
        
        file_extension = 'jpg' if format in ['jpg', 'jpeg'] else 'png'
        
        # Find the file
        possible_paths = [
            f"generated_logos/{logo_id}.{file_extension}",
            f"generated_logos/{logo_id}_v1.{file_extension}",
            f"generated_logos/{logo_id}_v2.{file_extension}"
        ]
        
        # Also try with base ID patterns
        if '_' in logo_id:
            base_parts = logo_id.split('_')
            base_id = base_parts[0]
            possible_paths.extend([
                f"generated_logos/{base_id}_v1.{file_extension}",
                f"generated_logos/{base_id}_v2.{file_extension}"
            ])
        
        file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                file_path = path
                logger.info(f"✅ Found file: {file_path}")
                break
        
        if not file_path:
            logger.error(f"❌ Logo file not found. Tried paths: {possible_paths}")
            raise HTTPException(
                status_code=404, 
                detail=f"Logo file not found. The file may have been deleted or the logo ID is incorrect."
            )
        
        return FileResponse(
            path=file_path,
            filename=f"{logo_id}.{file_extension}",
            media_type=f"image/{file_extension}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Download error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.post("/api/v1/feedback")
async def submit_feedback(feedback_data: dict):
    """Accept feedback for generated logos"""
    try:
        logo_id = feedback_data.get('logo_id')
        rating = feedback_data.get('rating')
        feedback_text = feedback_data.get('feedback_text', '')
        
        if not logo_id:
            raise HTTPException(status_code=400, detail="logo_id is required")
        
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            raise HTTPException(status_code=400, detail="rating must be an integer between 1 and 5")
        
        logger.info(f"📝 Enhanced Vertex AI feedback for {logo_id}: Rating {rating}/5")
        if feedback_text:
            logger.info(f"💬 Comment: {feedback_text}")
        
        return {
            "success": True,
            "message": "Feedback received successfully",
            "feedback": {
                "logo_id": logo_id,
                "rating": rating,
                "feedback_text": feedback_text,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Feedback error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Feedback submission failed: {str(e)}")

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy" if CREDENTIALS and PROJECT_ID else "auth_missing",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "8.1.0-enhanced",
        "project_id": PROJECT_ID,
        "credentials_configured": bool(CREDENTIALS),
        "vertex_ai_ready": bool(CREDENTIALS and PROJECT_ID),
        "enhancement_features": {
            "business_description_integration": True,
            "target_audience_optimization": True,
            "enhanced_prompt_generation": True,
            "contextual_logo_design": True
        },
        "directories": {
            "generated_logos": os.path.exists("generated_logos"),
            "static": os.path.exists("static")
        }
    }

@app.get("/api/v1/test-simple")
async def test_simple_generation():
    """Test with the simplest possible Vertex AI prompt"""
    try:
        if not CREDENTIALS or not PROJECT_ID:
            return {"error": "Authentication not configured"}
        
        logger.info("🧪 Testing simple enhanced Vertex AI Imagen generation...")
        
        simple_prompt = "A simple blue circle logo on white background"
        
        result = await VertexImagenLogoGenerator.generate_vertex_imagen_logo(
            simple_prompt, 
            "imagegeneration@006"
        )
        
        if result.get('success'):
            return {
                "status": "success",
                "message": "Simple enhanced Vertex AI generation test passed!",
                "images_generated": len(result.get('images', [])),
                "prompt_used": simple_prompt,
                "model": "imagegeneration@006",
                "location": result.get('location', 'us-central1'),
                "enhancement_note": "This was a basic test. Enhanced features activate with business description."
            }
        else:
            return {
                "status": "failed",
                "message": "Simple enhanced Vertex AI generation test failed",
                "error": result.get('error', 'Unknown error'),
                "prompt_used": simple_prompt
            }
            
    except Exception as e:
        logger.error(f"❌ Simple enhanced Vertex AI test failed: {str(e)}")
        return {
            "status": "error",
            "message": f"Simple enhanced Vertex AI test error: {str(e)}"
        }

@app.get("/api/v1/test-enhanced")
async def test_enhanced_generation():
    """Test enhanced generation with business context"""
    try:
        if not CREDENTIALS or not PROJECT_ID:
            return {"error": "Authentication not configured"}
        
        logger.info("🧪 Testing enhanced Vertex AI generation with business context...")
        
        # Create test prompts with business context
        test_prompts = VertexImagenLogoGenerator.create_vertex_prompts(
            business_name="TechFlow Solutions",
            industry="Technology", 
            style="modern",
            colors=["#3B82F6", "#1E40AF"],
            variations=2,
            business_description="A software company that creates digital platforms for businesses",
            target_audience="young professionals"
        )
        
        return {
            "status": "success",
            "message": "Enhanced prompt generation test completed",
            "test_business": "TechFlow Solutions",
            "generated_prompts": test_prompts,
            "enhancement_features": [
                "Business description analysis",
                "Industry-specific styling",
                "Target audience optimization",
                "Multiple meaningful variations"
            ],
            "note": "These are the enhanced prompts that would be sent to Vertex AI"
        }
        
    except Exception as e:
        logger.error(f"❌ Enhanced generation test failed: {str(e)}")
        return {
            "status": "error",
            "message": f"Enhanced generation test error: {str(e)}"
        }

@app.get("/api/v1/setup-guide")
async def vertex_setup_guide():
    """Comprehensive setup guide for enhanced Vertex AI Imagen"""
    return {
        "title": "Enhanced Google Vertex AI Imagen Setup Guide",
        "version": "2025-enhanced",
        "new_features": [
            "✨ Business description integration",
            "✨ Target audience optimization", 
            "✨ Enhanced prompt generation",
            "✨ Contextual logo design",
            "✨ Multiple meaningful variations"
        ],
        "critical_changes": [
            "✅ Business context now affects logo design",
            "✅ Target audience influences styling",
            "✅ Enhanced prompt intelligence",
            "✅ Improved variation generation"
        ],
        "steps": [
            {
                "step": 1,
                "title": "Install Google Cloud SDK",
                "description": "Download and install the Google Cloud SDK",
                "details": [
                    "Visit https://cloud.google.com/sdk/docs/install",
                    "Download the appropriate installer for your OS",
                    "Run the installer and follow instructions",
                    "Restart your terminal/command prompt"
                ]
            },
            {
                "step": 2,
                "title": "Authenticate with Google Cloud",
                "description": "Set up authentication (choose ONE method)",
                "methods": [
                    {
                        "name": "Method A: Application Default Credentials (Recommended)",
                        "commands": [
                            "gcloud auth application-default login",
                            "gcloud config set project YOUR_PROJECT_ID"
                        ]
                    },
                    {
                        "name": "Method B: Service Account (Production)",
                        "steps": [
                            "Create service account in Google Cloud Console",
                            "Download JSON key file",
                            "Set GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json",
                            "Set GOOGLE_CLOUD_PROJECT=your-project-id"
                        ]
                    }
                ]
            },
            {
                "step": 3,
                "title": "Enable Required APIs",
                "description": "Enable Vertex AI API in Google Cloud Console",
                "details": [
                    "Go to https://console.cloud.google.com/",
                    "Navigate to 'APIs & Services' > 'Library'",
                    "Search for 'Vertex AI API'",
                    "Click 'Enable'"
                ]
            },
            {
                "step": 4,
                "title": "Enable Billing (CRITICAL)",
                "description": "Vertex AI requires billing to be enabled",
                "details": [
                    "Go to 'Billing' in Google Cloud Console",
                    "Link a payment method to your project",
                    "Ensure billing is enabled for your project"
                ]
            },
            {
                "step": 5,
                "title": "Update Environment Variables",
                "description": "Set required environment variables in .env file",
                "variables": [
                    "GOOGLE_CLOUD_PROJECT=your-project-id",
                    "GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json (if using service account)"
                ]
            },
            {
                "step": 6,
                "title": "Test Enhanced Features",
                "description": "Use diagnostic endpoints to verify enhanced setup",
                "endpoints": [
                    "/api/v1/diagnostics - Full system diagnostics",
                    "/api/v1/test-simple - Simple generation test",
                    "/api/v1/test-enhanced - Enhanced features test",
                    "/api/v1/health - Health check with enhancement status"
                ]
            }
        ],
        "enhanced_usage_tips": [
            {
                "tip": "Detailed Business Description",
                "description": "Provide a detailed business description to get more relevant logo designs",
                "example": "Instead of 'Tech company', use 'A software development company that creates mobile apps for healthcare professionals'"
            },
            {
                "tip": "Specific Target Audience",
                "description": "Define your target audience for better design adaptation", 
                "example": "young professionals, families with children, luxury market, etc."
            },
            {
                "tip": "Industry Selection",
                "description": "Choose the most specific industry category for better context",
                "benefit": "Industry influences design elements and styling"
            }
        ],
        "common_issues_fixed": [
            {
                "issue": "Generic logo designs",
                "old_problem": "Logos didn't reflect business specifics",
                "new_solution": "Enhanced prompts use business description and context"
            },
            {
                "issue": "Single variation only",
                "old_problem": "Only one logo generated despite variations=2",
                "new_solution": "Fixed prompt generation for multiple meaningful variations"
            },
            {
                "issue": "Ignored business details",
                "old_problem": "Description and target audience had no effect",
                "new_solution": "Business context now directly influences design"
            }
        ],
        "quick_test_commands": [
            "gcloud auth list  # Check if authenticated",
            "gcloud projects list  # Check available projects", 
            "gcloud config get-value project  # Check current project",
            "curl -H \"Authorization: Bearer $(gcloud auth print-access-token)\" https://us-central1-aiplatform.googleapis.com/v1/projects/$(gcloud config get-value project)/locations/us-central1/models"
        ],
        "troubleshooting": {
            "auth_issues": "Run 'gcloud auth application-default login'",
            "project_issues": "Set project with 'gcloud config set project PROJECT_ID'",
            "api_issues": "Enable Vertex AI API in Cloud Console",
            "billing_issues": "Enable billing in Cloud Console > Billing",
            "enhancement_issues": "Check /api/v1/test-enhanced endpoint for feature testing"
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Enhanced Vertex AI Imagen Logo Generator...")
    print("🔧 Version: 8.1.0-enhanced")
    print("📍 URL: http://localhost:8000")
    print()    
    print("🔧 SETUP REQUIREMENTS:")
    print("   1. Install Google Cloud SDK")
    print("   2. Run: gcloud auth application-default login")
    print("   3. Set project: gcloud config set project YOUR_PROJECT_ID")
    print("   4. Enable Vertex AI API in Cloud Console")
    print("   5. Enable billing")
    print("   6. Optional: Set GOOGLE_CLOUD_PROJECT in .env")
    print()
    print("📊 DIAGNOSTIC ENDPOINTS:")
    print("   🔍 Full Diagnostics: http://localhost:8000/api/v1/diagnostics")
    print("   🧪 Simple Test: http://localhost:8000/api/v1/test-simple")
    print("   ✨ Enhanced Test: http://localhost:8000/api/v1/test-enhanced")
    print("   💊 Health Check: http://localhost:8000/api/v1/health")
    print("   📚 Setup Guide: http://localhost:8000/api/v1/setup-guide")
    print()
    
    # Check authentication status
    auth_success = initialize_google_auth()
    if auth_success and CREDENTIALS and PROJECT_ID:
        print(f"✅ Google Cloud authentication configured!")
        print(f"📋 Project ID: {PROJECT_ID}")
        print("🧪 Test enhanced features: http://localhost:8000/api/v1/test-enhanced")
    else:
        print("❌ Google Cloud authentication not configured!")
        print("📋 Quick setup:")
        print("   1. gcloud auth application-default login")
        print("   2. gcloud config set project YOUR_PROJECT_ID")
        print("   3. Restart this server")
        print("📚 Full guide: http://localhost:8000/api/v1/setup-guide")
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)