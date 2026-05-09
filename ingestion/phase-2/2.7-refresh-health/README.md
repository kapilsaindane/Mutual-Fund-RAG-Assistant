# Phase 2.7 - Refresh and Health

## Purpose

Implements scheduled refresh for changed source content using GitHub Actions, with comprehensive quality gates and health monitoring.

## Components

### 1. Change Detection (`change_detector.py`)
- Detects changes in source URLs using content fingerprinting
- Supports incremental updates and force refresh
- Maintains state of previous fetches
- Generates change reports for pipeline decisions

### 2. Refresh Pipeline (`refresh_pipeline.py`)
- Orchestrates full or incremental ingestion pipeline
- Creates backups before updates
- Runs all phases (2.1-2.6) with error handling
- Generates comprehensive pipeline reports

### 3. Retry Manager (`retry_manager.py`)
- Implements exponential backoff retry logic
- Tracks retry attempts per operation
- Provides notification management (email/Slack)
- Maintains retry state across pipeline runs

### 4. Quality Gates (`quality_gates.py`)
- Validates data quality at each pipeline phase
- Detects empty chunks, duplicates, broken extractions
- Enforces quality thresholds (95% success rates)
- Generates detailed quality reports

### 5. Health Checker (`health_checker.py`)
- Monitors embedding and index system health
- Checks data freshness and system resources
- Validates query functionality and metadata filters
- Provides comprehensive health diagnostics

## Usage

### Manual Change Detection
```bash
python ingestion/phase-2/2.7-refresh-health/change_detector.py
```

### Manual Refresh Pipeline
```bash
# Full refresh
python ingestion/phase-2/2.7-refresh-health/refresh_pipeline.py --force-refresh true

# Incremental refresh (if changes detected)
python ingestion/phase-2/2.7-refresh-health/refresh_pipeline.py --changed-urls "url1,url2,url3"
```

### Quality Gates Check
```bash
python ingestion/phase-2/2.7-refresh-health/quality_gates.py
```

### Health Check
```bash
python ingestion/phase-2/2.7-refresh-health/health_checker.py
```

## GitHub Actions Integration

The automated workflow (`.github/workflows/data-refresh.yml`) runs:
- **Daily at 2 AM UTC**: Automatic change detection and refresh
- **Manual trigger**: Force refresh option available
- **On code changes**: Triggers when ingestion code is updated

### Workflow Stages
1. **Change Detection**: Identifies modified URLs
2. **Ingestion Pipeline**: Runs full or incremental refresh
3. **Quality Gates**: Validates data quality
4. **Health Checks**: Monitors system health
5. **Notifications**: Sends success/failure alerts

## Configuration

### Environment Variables
- `ADMIN_EMAIL`: Email address for notifications
- `SLACK_WEBHOOK_URL`: Slack webhook for notifications

### Quality Thresholds
- Fetch success rate: ≥95%
- Extraction success rate: ≥95%
- Empty chunks: 0%
- Duplicate chunks: 0%
- Embedding coverage: 100%

### Retry Configuration
- Max retries: 3
- Base delay: 60 seconds
- Max delay: 1 hour (exponential backoff)

## Outputs

### Reports Generated
- `change-report-latest.json`: Change detection results
- `pipeline-report-latest.json`: Pipeline execution summary
- `quality-gate-report-latest.json`: Quality validation results
- `health-report-latest.json`: System health status
- `notification-log-latest.json`: Notification history

### State Management
- `last_fetch_state.json`: Previous fetch fingerprints
- `retry_state.json`: Retry attempt tracking

## Monitoring

### Key Metrics
- Source freshness (last update timestamps)
- Pipeline success/failure rates
- Data quality scores
- System resource usage
- Embedding/index consistency

### Alerts
- Pipeline failures with detailed error information
- Quality gate violations
- System health degradation
- Resource exhaustion warnings

## Integration with Other Phases

This phase orchestrates and monitors all previous phases (2.1-2.6):
- **Phase 2.1 (Fetcher)**: Validates URL fetching success
- **Phase 2.2 (Extractor)**: Checks content extraction quality
- **Phase 2.3 (Cleaner)**: Validates text cleaning effectiveness
- **Phase 2.4 (Chunker)**: Ensures chunk quality and uniqueness
- **Phase 2.5 (Embedder)**: Validates embedding generation
- **Phase 2.6 (Indexerr)**: Checks vector index health

## Error Handling

### Automatic Recovery
- Retry failed operations with exponential backoff
- Fallback to full refresh on incremental failures
- Automatic backup restoration on critical failures

### Manual Intervention
- Detailed logs for troubleshooting
- State files for recovery points
- Manual override options for force refresh

## Dependencies

- Python 3.11+
- chromadb
- requests
- beautifulsoup4
- sentence-transformers
- numpy

## Security Considerations

- URL allowlist enforcement (inherited from Phase 1)
- No sensitive data in logs or notifications
- Secure credential management for notifications
- Input validation for all external inputs
