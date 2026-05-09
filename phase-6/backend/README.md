# Phase 6 Backend - Minimal UI and User Experience

Backend API server for the HDFC Mutual Fund Assistant UI.

## Features

- **Complete Query Processing**: Integrates Phases 3-5 for end-to-end query handling
- **RESTful API**: Clean JSON endpoints for frontend integration
- **CORS Support**: Ready for frontend development
- **Error Handling**: Comprehensive error handling and logging
- **Health Checks**: System status monitoring
- **Environment Configuration**: Flexible configuration via environment variables

## API Endpoints

### Query Processing
```http
POST /api/query
Content-Type: application/json

{
  "query": "What is the expense ratio of HDFC Mid Cap Fund?",
  "method": "auto|extractive|groq",
  "show_steps": false,
  "save_logs": false
}
```

### UI Configuration
```http
GET /api/ui-data
```

Returns:
- Welcome message
- Disclaimer text
- Example questions
- System status

### Health Check
```http
GET /health
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp ../../.env.example ../../.env
# Edit .env with your API keys
```

3. Start the server:
```bash
python run.py
```

Or with custom options:
```bash
python run.py --host 0.0.0.0 --port 5000 --debug
```

## Usage Examples

### Process a Query
```bash
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the expense ratio of HDFC Mid Cap Fund?"}'
```

### Get UI Data
```bash
curl http://localhost:5000/api/ui-data
```

### Health Check
```bash
curl http://localhost:5000/health
```

## Response Format

### Successful Query Response
```json
{
  "success": true,
  "response": "The expense ratio is 0.45%. Source: https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth\n\nLast updated from sources: 2026-05-05",
  "method": "groq",
  "metadata": {
    "sentence_count": 1,
    "url_count": 1,
    "final_method": "groq"
  },
  "ui_data": {
    "type": "factual",
    "source_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
    "last_updated": "2026-05-05",
    "processing_steps": ["PII Detection", "Intent Classification", "Retrieval", "Answer Generation", "Post-Processing"]
  }
}
```

### Refusal Response
```json
{
  "success": true,
  "response": "I can only provide factual information about mutual funds and cannot give investment advice or recommendations. For educational resources, visit: https://www.amfiindia.com/mutual-funds-investor-education",
  "method": "refusal",
  "metadata": {
    "intent": "advisory_refuse",
    "confidence": 0.8
  },
  "ui_data": {
    "type": "refusal",
    "processing_steps": ["PII Detection", "Intent Classification", "Refusal Composition"]
  }
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | - | Groq API key for LLM generation |
| `USE_GROQ` | `true` | Force Groq usage |
| `GROQ_MODEL` | `llama3-70b-8192` | Groq model name |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `5000` | Server port |
| `DEBUG` | `false` | Debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |

## Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black .
flake8 .
```

### Logging
Logs are output to console with configurable levels:
- `DEBUG`: Detailed debugging information
- `INFO`: General information (default)
- `WARNING`: Warning messages
- `ERROR`: Error messages

## Architecture

The backend integrates the complete Phase 3-5 system:

1. **Phase 3**: Retrieval Engine (Hybrid search with RRF)
2. **Phase 4**: Query Classification and Policy Guardrails (Intent classification, PII detection)
3. **Phase 5**: Controlled Answer Generation (Extractive/Groq generation with policy enforcement)

All phases are coordinated through the Orchestrator component, ensuring consistent policy enforcement and error handling.

## Frontend Integration

The backend is designed to work seamlessly with a frontend application:

1. **CORS enabled** for cross-origin requests
2. **JSON responses** with consistent structure
3. **UI-specific formatting** for easy frontend consumption
4. **Error handling** with appropriate HTTP status codes

The `/api/ui-data` endpoint provides all necessary UI configuration data, making frontend setup straightforward.
