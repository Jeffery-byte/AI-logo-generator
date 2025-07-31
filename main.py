# main.py - FastAPI Backend for AI Logo Creator
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import json
import hashlib
import time
from datetime import datetime, timedelta
import redis
import asyncpg
import openai
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import colorsys
import re

# ================== CONFIGURATION ==================
app = FastAPI(
    title="LogoAI Backend",
    description="AI-powered logo generation service",
    version="1.0.0"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Redis for caching (logo generation results, rate limiting)
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Database connection pool (PostgreSQL)
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "logoai_db",
    "user": "postgres",
    "password": "your_password"
}

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
    variations: int = Field(default=3, ge=1, le=6)

class LogoResponse(BaseModel):
    id: str
    name: str
    svg_content: str
    style_info: Dict[str, Any]
    colors_used: List[str]
    generation_time: float
    confidence_score: float

class UserFeedback(BaseModel):
    logo_id: str
    rating: int = Field(..., ge=1, le=5)
    feedback_text: Optional[str] = None

# ================== DATABASE OPERATIONS ==================
class DatabaseManager:
    def __init__(self):
        self.pool = None
    
    async def init_pool(self):
        """Initialize database connection pool"""
        self.pool = await asyncpg.create_pool(**DB_CONFIG)
        
        # Create tables if they don't exist
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE TABLE IF NOT EXISTS logo_generations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id INTEGER REFERENCES users(id),
                    business_name VARCHAR(100),
                    industry VARCHAR(50),
                    style_type VARCHAR(20),
                    colors JSONB,
                    svg_content TEXT,
                    generation_params JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    feedback_rating INTEGER,
                    is_favorite BOOLEAN DEFAULT FALSE
                );
                
                CREATE INDEX IF NOT EXISTS idx_generations_user 
                ON logo_generations(user_id);
                
                CREATE INDEX IF NOT EXISTS idx_generations_created 
                ON logo_generations(created_at DESC);
            """)
    
    async def save_logo_generation(self, user_id: int, request: LogoGenerationRequest, 
                                 logos: List[LogoResponse]) -> List[str]:
        """Save generated logos to database"""
        logo_ids = []
        async with self.pool.acquire() as conn:
            for logo in logos:
                logo_id = await conn.fetchval("""
                    INSERT INTO logo_generations 
                    (user_id, business_name, industry, style_type, colors, 
                     svg_content, generation_params)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id
                """, 
                user_id,
                request.business_info.name,
                request.business_info.industry,
                request.style.style_type,
                json.dumps(logo.colors_used),
                logo.svg_content,
                json.dumps(request.dict())
                )
                logo_ids.append(str(logo_id))
        return logo_ids

    async def get_user_logos(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Retrieve user's logo history"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, business_name, industry, style_type, colors,
                       svg_content, created_at, feedback_rating, is_favorite
                FROM logo_generations 
                WHERE user_id = $1 
                ORDER BY created_at DESC 
                LIMIT $2
            """, user_id, limit)
            
            return [dict(row) for row in rows]

db_manager = DatabaseManager()

# ================== AI SERVICES ==================
class BusinessAnalyzer:
    """Analyzes business information to suggest optimal logo characteristics"""
    
    INDUSTRY_COLORS = {
        'technology': ['#007acc', '#0066cc', '#4a90e2', '#5cb3cc'],
        'healthcare': ['#00a86b', '#228b22', '#32cd32', '#87ceeb'],
        'finance': ['#1e3a5f', '#2c5f2d', '#8b4513', '#708090'],
        'food': ['#ff6347', '#ffa500', '#ffd700', '#32cd32'],
        'education': ['#4169e1', '#8a2be2', '#dc143c', '#228b22'],
        'creative': ['#ff1493', '#ff4500', '#ffd700', '#9370db']
    }
    
    STYLE_KEYWORDS = {
        'modern': ['tech', 'digital', 'software', 'app', 'innovation'],
        'professional': ['consulting', 'finance', 'law', 'corporate'],
        'playful': ['kids', 'games', 'entertainment', 'creative'],
        'elegant': ['luxury', 'premium', 'boutique', 'fashion'],
        'bold': ['sports', 'fitness', 'energy', 'power'],
        'vintage': ['craft', 'artisan', 'traditional', 'heritage']
    }
    
    @staticmethod
    async def analyze_business(business_info: BusinessInfo) -> Dict[str, Any]:
        """Analyze business to recommend colors and styles"""
        start_time = time.time()
        
        # Industry-based color suggestions
        industry_lower = business_info.industry.lower()
        suggested_colors = BusinessAnalyzer.INDUSTRY_COLORS.get(
            industry_lower, ['#3b82f6', '#1e40af', '#10b981']
        )
        
        # Name analysis for style suggestions
        name_words = re.findall(r'\w+', business_info.name.lower())
        description_words = re.findall(r'\w+', 
            (business_info.description or '').lower())
        all_words = name_words + description_words
        
        # Score each style based on keyword matches
        style_scores = {}
        for style, keywords in BusinessAnalyzer.STYLE_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in all_words)
            style_scores[style] = score
        
        # Get top recommended style
        recommended_style = max(style_scores, key=style_scores.get) or 'modern'
        
        analysis_time = time.time() - start_time
        
        return {
            'recommended_colors': suggested_colors,
            'recommended_style': recommended_style,
            'style_confidence': style_scores,
            'analysis_time': analysis_time,
            'business_keywords': all_words[:10]  # Top 10 relevant words
        }

class LogoGenerator:
    """Core logo generation service using AI and programmatic design"""
    
    @staticmethod
    def generate_color_variations(base_colors: List[str], count: int = 3) -> List[List[str]]:
        """Generate color palette variations"""
        variations = [base_colors]
        
        for _ in range(count - 1):
            # Create variations by adjusting HSV values
            new_palette = []
            for color in base_colors:
                # Convert hex to RGB then to HSV
                hex_color = color.lstrip('#')
                rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                hsv = colorsys.rgb_to_hsv(rgb[0]/255, rgb[1]/255, rgb[2]/255)
                
                # Adjust hue slightly
                new_hue = (hsv[0] + 0.1) % 1.0
                new_rgb = colorsys.hsv_to_rgb(new_hue, hsv[1], hsv[2])
                
                # Convert back to hex
                new_hex = '#{:02x}{:02x}{:02x}'.format(
                    int(new_rgb[0] * 255),
                    int(new_rgb[1] * 255),
                    int(new_rgb[2] * 255)
                )
                new_palette.append(new_hex)
            
            variations.append(new_palette)
        
        return variations

    @staticmethod
    def create_logo_svg(business_name: str, style: str, colors: List[str], 
                       variation_id: int) -> str:
        """Generate SVG logo based on parameters"""
        
        # Different logo templates based on style and variation
        templates = {
            'modern': [
                lambda name, c: f'''<svg viewBox="0 0 300 120" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" style="stop-color:{c[0]};stop-opacity:1" />
                            <stop offset="100%" style="stop-color:{c[1] if len(c) > 1 else c[0]};stop-opacity:1" />
                        </linearGradient>
                    </defs>
                    <rect x="20" y="30" width="60" height="60" rx="15" fill="url(#grad1)"/>
                    <text x="100" y="70" font-family="Arial, sans-serif" font-size="32" font-weight="600" fill="{c[0]}">{name}</text>
                </svg>''',
                
                lambda name, c: f'''<svg viewBox="0 0 300 120" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="50" cy="60" r="30" fill="{c[0]}"/>
                    <circle cx="60" cy="50" r="8" fill="{c[1] if len(c) > 1 else '#ffffff'}"/>
                    <text x="100" y="70" font-family="Arial, sans-serif" font-size="28" font-weight="500" fill="{c[0]}">{name}</text>
                </svg>''',
            ],
            
            'professional': [
                lambda name, c: f'''<svg viewBox="0 0 300 120" xmlns="http://www.w3.org/2000/svg">
                    <rect x="20" y="40" width="50" height="40" fill="{c[0]}"/>
                    <rect x="25" y="35" width="50" height="40" fill="none" stroke="{c[1] if len(c) > 1 else c[0]}" stroke-width="2"/>
                    <text x="90" y="70" font-family="Times, serif" font-size="30" font-weight="bold" fill="{c[0]}">{name}</text>
                </svg>''',
            ],
            
            'playful': [
                lambda name, c: f'''<svg viewBox="0 0 300 120" xmlns="http://www.w3.org/2000/svg">
                    <polygon points="50,20 80,40 70,80 30,80 20,40" fill="{c[0]}"/>
                    <circle cx="45" cy="45" r="8" fill="{c[1] if len(c) > 1 else '#ffffff'}"/>
                    <text x="100" y="70" font-family="Comic Sans MS, cursive" font-size="28" font-weight="bold" fill="{c[0]}">{name}</text>
                </svg>''',
            ]
        }
        
        # Get template for the style, default to modern
        style_templates = templates.get(style, templates['modern'])
        template_func = style_templates[variation_id % len(style_templates)]
        
        return template_func(business_name, colors)

    @staticmethod
    async def generate_logos(request: LogoGenerationRequest) -> List[LogoResponse]:
        """Main logo generation function"""
        start_time = time.time()
        
        # Generate color variations
        color_variations = LogoGenerator.generate_color_variations(
            request.style.color_palette, request.variations
        )
        
        logos = []
        for i in range(request.variations):
            colors = color_variations[i % len(color_variations)]
            
            # Generate SVG
            svg_content = LogoGenerator.create_logo_svg(
                request.business_info.name,
                request.style.style_type,
                colors,
                i
            )
            
            # Create logo response
            logo_id = hashlib.md5(
                f"{request.business_info.name}{i}{time.time()}".encode()
            ).hexdigest()
            
            logo = LogoResponse(
                id=logo_id,
                name=f"{request.business_info.name} - Concept {i+1}",
                svg_content=svg_content,
                style_info={
                    "style": request.style.style_type,
                    "variation": i + 1,
                    "template_used": f"template_{i % 3}"
                },
                colors_used=colors,
                generation_time=time.time() - start_time,
                confidence_score=0.85 + (i * 0.05)  # Mock confidence scoring
            )
            
            logos.append(logo)
        
        return logos

# ================== API ENDPOINTS ==================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
   # await db_manager.init_pool()
   # print("🚀 LogoAI Backend started successfully!")
    pass

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "LogoAI Backend API",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/v1/analyze-business", response_model=Dict[str, Any])
async def analyze_business_endpoint(business_info: BusinessInfo):
    """Analyze business information and provide recommendations"""
    try:
        # Check cache first
        cache_key = f"analysis:{hashlib.md5(business_info.name.encode()).hexdigest()}"
        cached_result = redis_client.get(cache_key)
        
        if cached_result:
            return json.loads(cached_result)
        
        # Perform analysis
        analysis = await BusinessAnalyzer.analyze_business(business_info)
        
        # Cache result for 1 hour
        redis_client.setex(cache_key, 3600, json.dumps(analysis))
        
        return {
            "success": True,
            "data": analysis,
            "cached": False
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/api/v1/generate-logos", response_model=Dict[str, Any])
async def generate_logos_endpoint(
    request: LogoGenerationRequest,
    background_tasks: BackgroundTasks,
    # credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Generate AI-powered logos"""
    try:
        start_time = time.time()
        
        # Rate limiting check
        client_id = "anonymous"  # In real app, extract from JWT token
        rate_key = f"rate_limit:{client_id}"
        current_requests = redis_client.get(rate_key) or 0
        
        if int(current_requests) >= 10:  # 10 requests per hour
            raise HTTPException(
                status_code=429, 
                detail="Rate limit exceeded. Please try again later."
            )
        
        # Increment rate limit counter
        redis_client.setex(rate_key, 3600, int(current_requests) + 1)
        
        # Generate logos
        logos = await LogoGenerator.generate_logos(request)
        
        # Save to database in background
        # background_tasks.add_task(db_manager.save_logo_generation, 1, request, logos)
        
        total_time = time.time() - start_time
        
        return {
            "success": True,
            "data": {
                "logos": logos,
                "generation_stats": {
                    "total_time": total_time,
                    "logos_generated": len(logos),
                    "average_time_per_logo": total_time / len(logos)
                }
            },
            "remaining_requests": 10 - int(current_requests) - 1
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.post("/api/v1/feedback")
async def submit_feedback(feedback: UserFeedback):
    """Submit feedback for a generated logo"""
    try:
        # In a real app, this would update the database and potentially retrain models
        feedback_key = f"feedback:{feedback.logo_id}"
        redis_client.setex(feedback_key, 86400, json.dumps(feedback.dict()))
        
        return {
            "success": True,
            "message": "Feedback recorded successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feedback submission failed: {str(e)}")

@app.get("/api/v1/user/logos")
async def get_user_logos():
    """Get user's logo generation history"""
    try:
        # In a real app, extract user_id from JWT token
        user_id = 1
        logos = await db_manager.get_user_logos(user_id)
        
        return {
            "success": True,
            "data": {
                "logos": logos,
                "total_count": len(logos)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve logos: {str(e)}")

@app.get("/api/v1/statistics")
async def get_statistics():
    """Get platform usage statistics"""
    try:
        # Mock statistics - in real app, query database
        stats = {
            "total_logos_generated": 15847,
            "active_users_today": 342,
            "average_generation_time": 2.3,
            "user_satisfaction": 4.6,
            "popular_styles": {
                "modern": 45,
                "professional": 28,
                "playful": 15,
                "elegant": 12
            }
        }
        
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve statistics: {str(e)}")

# ================== WEBSOCKET FOR REAL-TIME UPDATES ==================
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                self.disconnect(connection)

manager = ConnectionManager()

@app.websocket("/ws/generation-progress")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time generation progress"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and send progress updates
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)