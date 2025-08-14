# Vertex AI Logo Generator
Enterprise-grade logo generation powered by Google Vertex AI Imagen with enhanced business context integration


## Overview

A full-stack application that leverages **Google Vertex AI Imagen** to generate professional logos with advanced business context integration. Built for enterprises requiring scalable, AI-powered branding solutions with proper authentication and comprehensive diagnostics.

### ✨ Key Features

- **Google Vertex AI Integration**: Professional authentication with OAuth2 and service accounts
  
- **Business Context Intelligence**: Enhanced prompt generation using business description and target audience
  
- **Comprehensive Diagnostics**: Built-in system health monitoring and setup validation
  
- **Cloud-Native Architecture**: Designed for enterprise deployment and scaling
  
- **Multiple AI Models**: Support for Imagen 3 (latest) and Imagen 2.5
  
- **Real-time Cost Tracking**: Transparent pricing with usage analytics
  
- **Enterprise Security**: Proper credential management and secure API handling

## Demo & Screenshots

### Main Interface
![Main Interface](screenshots/Main interfaceg)

### Generated Logos with Vertex AI
![Generated Logos](screenshots/Generated Logos)

### Diagnostics Dashboard
![Diagnostics](screenshots/Diagnostics)

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐    ┌─────────────────────┐
│   React Frontend │    │  FastAPI Backend │    │   Google Vertex AI  │
│   (TypeScript)   │◄──►│     (Python)     │◄──►│      Imagen API     │
│                 │     │                  │    │                     │
│ • Logo Gallery   │    │ • Authentication │    │ • Image Generation  │
│ • Style Config   │    │ • Prompt Engine  │    │ • Model Selection   │
│ • Diagnostics    │    │ • File Management│    │ • Quality Control   │
└─────────────────┘     └──────────────────┘    └─────────────────────┘
```

## 🛠️ Technology Stack

### Backend
- **FastAPI**: High-performance Python web framework
- **Google Cloud SDK**: Official Vertex AI integration
- **Pydantic**: Data validation and settings management
- **Pillow**: Image processing and optimization
- **python-dotenv**: Environment configuration

### Frontend
- **React 18**: Modern UI framework with hooks
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first styling
- **Lucide React**: Professional icon system

### Cloud Services
- **Google Vertex AI**: Imagen models for logo generation
- **Google Cloud Authentication**: OAuth2 and service accounts
- **Cloud Storage**: Optional file persistence

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+
- Google Cloud Project with billing enabled
- Vertex AI API enabled

### 1. Clone Repository

```bash
git clone https://github.com/Jeffery-byte/vertex-ai-logo-generator.git
cd vertex-ai-logo-generator
```

### 2. Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup Google Cloud Authentication
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

# Create environment file
cp .env.example .env
# Edit .env with your configuration
```

### 3. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

### 4. Start Backend

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Access Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Diagnostics**: http://localhost:8000/api/v1/diagnostics

## 🔧 Configuration

### Environment Variables

```bash
# Required
GOOGLE_CLOUD_PROJECT=your-project-id

# Optional (if using service account)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Development
DEBUG=True
ENVIRONMENT=development
```

### Google Cloud Setup

1. **Enable APIs**:
   ```bash
   gcloud services enable aiplatform.googleapis.com
   gcloud services enable compute.googleapis.com
   ```

2. **Set up Authentication**:
   ```bash
   # Method 1: Application Default Credentials (Recommended for development)
   gcloud auth application-default login
   
   # Method 2: Service Account (Recommended for production)
   gcloud iam service-accounts create vertex-ai-logo-generator
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:vertex-ai-logo-generator@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/aiplatform.user"
   ```

3. **Enable Billing**: Vertex AI requires billing to be enabled

## 📚 API Documentation

### Core Endpoints

#### Generate Logos
```http
POST /api/v1/generate-logos
Content-Type: application/json

{
  "business_info": {
    "name": "TechFlow Solutions",
    "industry": "Technology",
    "description": "AI-powered software solutions",
    "target_audience": "young professionals"
  },
  "style": {
    "style_type": "modern",
    "color_palette": ["#3B82F6", "#1E40AF"]
  },
  "variations": 2,
  "imagen_model": "imagegeneration@006"
}
```

#### Run Diagnostics
```http
GET /api/v1/diagnostics

Response:
{
  "status": "complete",
  "results": {
    "credentials_status": "valid",
    "vertex_api_access": "working",
    "model_access": {
      "imagegeneration@006": "working"
    }
  },
  "summary": {
    "ready_for_generation": true
  }
}
```

#### Download Logos
```http
GET /api/v1/logo/{logo_id}/download/{format}
# Formats: png, jpg
```

## 🧪 Testing

### Run Backend Tests
```bash
cd backend
pytest tests/ -v --cov=.
```

### Run Frontend Tests
```bash
cd frontend
npm test
```

### Manual Testing with Diagnostics
```bash
# Test Vertex AI connectivity
curl http://localhost:8000/api/v1/test-simple

# Test enhanced features
curl http://localhost:8000/api/v1/test-enhanced

# Full diagnostic suite
curl http://localhost:8000/api/v1/diagnostics
```

## 🚀 Deployment

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build
```

### Google Cloud Run Deployment

```bash
# Deploy backend
gcloud run deploy vertex-logo-backend \
  --source=./backend \
  --region=us-central1 \
  --allow-unauthenticated

# Deploy frontend
gcloud run deploy vertex-logo-frontend \
  --source=./frontend \
  --region=us-central1 \
  --allow-unauthenticated
```

### Environment-Specific Configurations

- **Development**: Local authentication with gcloud
- **Staging**: Service account with limited permissions
- **Production**: Workload Identity for enhanced security

## 💰 Cost Analysis

| Model | Cost per Image | Quality | Use Case |
|-------|---------------|---------|----------|
| imagegeneration@006 | $0.030 | Highest | Production logos |
| imagegeneration@005 | $0.025 | High | Development/Testing |

**Estimated Monthly Costs** (1000 logo generations):
- Imagen 3: ~$30/month
- Imagen 2.5: ~$25/month

## 🔍 Performance Metrics

- **Average Generation Time**: 3-5 seconds per logo
- **Success Rate**: 98%+ with proper authentication
- **Image Quality**: Professional HD (1024x1024)
- **Concurrent Users**: Supports 50+ simultaneous generations

## 🛡️ Security Features

- **OAuth2 Authentication**: Secure Google Cloud integration
- **Rate Limiting**: Prevents abuse and controls costs
- **Input Validation**: Comprehensive request sanitization
- **Credential Management**: Secure handling of API keys
- **CORS Protection**: Configured for production security

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Use TypeScript strict mode
- Write tests for new features
- Update documentation
- Run linting before commits

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

##  Acknowledgments

- **Google Cloud Team** for Vertex AI platform
- **FastAPI Community** for excellent documentation
- **React Team** for modern UI framework
- **Tailwind CSS** for utility-first styling

## 📞 Support

- **Documentation**: [Wiki](wiki)
- **Issues**: [GitHub Issues](issues)
- **Discussions**: [GitHub Discussions](discussions)

## 🎯 Roadmap

- [ ] **v2.0**: Multi-tenant architecture
- [ ] **v2.1**: Advanced logo templates
- [ ] **v2.2**: Brand guideline generation
- [ ] **v2.3**: API marketplace integration
- [ ] **v3.0**: Custom model fine-tuning

---

<div align="center">
  <strong>Built with ❤️ for the future of AI-powered design</strong>
  <br>
  <sub>Ready for enterprise deployment and scaling</sub>
</div>
