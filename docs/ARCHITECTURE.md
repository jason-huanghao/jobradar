# JobHunter Extended - Architecture Document

## Overview

This document outlines the architecture for extending the JobHunter project with Chinese job platform support, multilingual Excel output, and a web-based CV upload system.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Chinese Job Platform Integration](#chinese-job-platform-integration)
3. [Multilingual Excel Generation](#multilingual-excel-generation)
4. [Web CV Upload System](#web-cv-upload-system)
5. [AI Platform Integration](#ai-platform-integration)
6. [Deployment Strategy](#deployment-strategy)
7. [Implementation Roadmap](#implementation-roadmap)

---

## System Architecture

### Current Architecture

```
config.yaml → CV Parser (LLM) → Query Builder → Sources → Dedup → Scorer (LLM) → Outputs
```

### Extended Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         JobHunter Extended                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│  │   Sources   │────▶│   Parser    │────▶│   Scorer    │  │
│  │             │     │             │     │             │  │
│  │ - BA (DE)   │     │   CV →      │     │   LLM       │  │
│  │ - Indeed     │     │   Profile    │     │   6-dim     │  │
│  │ - Google     │     │             │     │   scoring    │  │
│  │ - BOSS直聘  │     └─────────────┘     └─────────────┘  │
│  │ - 拉勾 (later)│                                   │
│  │ - 猎聘 (later)│     ┌─────────────────────────────┐       │
│  │ - 51Job (later)│     │       Output Manager       │       │
│  └─────────────┘     │                         │       │
│                       │ - Excel (EN + CN)       │       │
│  ┌─────────────┐     │ - Digests              │       │
│  │   Web UI    │     │ - Applications           │       │
│  │   (FastAPI) │     └─────────────────────────────┘       │
│  │             │                                        │
│  │ - CV Upload │     ┌─────────────────────────────┐       │
│  │ - User Mgmt │     │   Job Pool              │       │
│  │ - Status    │     │   (persistent storage)   │       │
│  └─────────────┘     └─────────────────────────────┘       │
│                                                              │
└──────────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Modularity**: Each component can be developed and tested independently
2. **Async First**: FastAPI background tasks for scalability
3. **Configuration-Driven**: All features configurable via YAML
4. **User Isolation**: Each user has isolated data folder
5. **Type Safety**: Pydantic models throughout
6. **Backward Compatibility**: Existing CLI functionality preserved

---

## Chinese Job Platform Integration

### Phase 1: BOSS直聘 (MVP)

**Technology Stack:**
- `DrissionPage` - Modern browser automation (easier than Selenium)
- `asyncio` - For concurrent requests
- `httpx` - For HTTP operations (fallback)

**Implementation Details:**

```python
# src/sources/bosszhipin.py

class BossZhipinSource(JobSource):
    name = "bosszhipin"

    def __init__(self):
        self.session = None  # DrissionPage session

    async def search(self, query: SearchQuery, config: AppConfig) -> list[RawJob]:
        """
        Search BOSS直聘 for jobs

        Algorithm:
        1. Initialize browser with DrissionPage
        2. Navigate to search page with keyword/location
        3. Intercept API responses (XHR/Fetch)
        4. Extract job data from JSON
        5. Parse to RawJob objects
        6. Close browser
        """
        # Implementation will use:
        # - DrissionPage for browser automation
        # - Cookie management for auth
        # - Rate limiting (delay between requests)
        # - IP rotation support (optional, via proxy)
```

**Data Model Extensions:**

```python
# Add to models.py

class ChineseJobMetadata(BaseModel):
    """Additional fields for Chinese job platforms"""
    salary_range: str = ""  # e.g., "15-25K"
    experience_required: str = ""  # e.g., "3-5年"
    education_required: str = ""  # e.g., "本科"
    company_size: str = ""  # e.g., "100-499人"
    company_industry: str = ""  # e.g., "互联网"
    tags: list[str] = Field(default_factory=list)  # 技能标签

# Extend RawJob
class RawJob(BaseModel):
    # ... existing fields ...
    chinese_metadata: ChineseJobMetadata | None = None
```

**Configuration:**

```yaml
# config.yaml additions

sources:
  bosszhipin:
    enabled: true
    # Search parameters
    city_code: "101010100"  # 北京
    page_size: 30
    max_pages: 3
    # Rate limiting
    delay_between_requests: 2.0  # seconds
    # Proxy support (optional)
    use_proxy: false
    proxy_url: ""
```

**Anti-Countermeasures:**

1. **Rate Limiting**: 2-3 second delay between requests
2. **User-Agent Rotation**: Random UA strings from pool
3. **Cookie Persistence**: Save cookies for session reuse
4. **IP Rotation** (optional): Via proxy if needed
5. **Error Handling**: Retry with exponential backoff

### Phase 2: Additional Platforms

**拉勾网:**
- Two-step process: GET page → extract cookies → POST for JSON
- URL: `https://www.lagou.com/jobs/positionAjax.json`
- Similar data model to BOSS直聘

**猎聘网:**
- Apify integration first (via MCP or API)
- Custom scraper later if needed
- URL: `https://www.liepin.com`

**51Job:**
- Apify integration first
- Custom scraper later
- URL: `https://www.51job.com`

---

## Multilingual Excel Generation

### Architecture

```
RawJob → Translation Module → ScoredJob → Excel Generator
                  ↓
            EN data | CN data
                  ↓
           jobs_pipeline.xlsx | jobs_pipeline_cn.xlsx
```

### Translation Strategy

**Option 1: LLM-Based Translation (Recommended)**

```python
# src/translators/job_translator.py

class JobTranslator:
    """Translate job data using LLM"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.cache = {}  # Translation cache

    async def translate_job(self, job: RawJob, target_lang: str = "zh") -> dict:
        """Translate a single job to target language"""
        # Cache key: f"{job.source}:{job.id}:{target_lang}"

        prompt = f"""
        Translate the following job information to {target_lang}:
        - Keep technical terms in English (Python, React, etc.)
        - Translate job titles, company names, locations
        - Maintain professional tone

        Original:
        Title: {job.title}
        Company: {job.company}
        Location: {job.location}
        Description: {job.description[:500]}...

        Return JSON: {{"title": "...", "company": "...", ...}}
        """

        # Call LLM and parse response
```

**Option 2: Dictionary-Based Translation**

```python
# src/translators/dictionary.py

JOB_TITLE_TRANSLATIONS = {
    "AI Engineer": "AI工程师",
    "Machine Learning Engineer": "机器学习工程师",
    "Data Scientist": "数据科学家",
    "Product Manager": "产品经理",
    # ... more mappings
}

LOCATION_TRANSLATIONS = {
    "Berlin": "柏林",
    "Munich": "慕尼黑",
    "Hamburg": "汉堡",
    "Beijing": "北京",
    "Shanghai": "上海",
    # ... more mappings
}

# Fallback to LLM if not in dictionary
```

**Hybrid Approach (Best):**
1. Check dictionary cache first
2. Use LLM for missing translations
3. Cache LLM results for future use

### Excel Structure

**English Version (existing):**
```
Avg Score | LLM Score | Title | Company | Location | Source | Date Posted | Salary | URL | ...
```

**Chinese Version (new):**
```
平均分 | LLM评分 | 职位 | 公司 | 地点 | 来源 | 发布日期 | 薪资 | 链接 | ...
```

**Implementation:**

```python
# src/outputs/chinese_excel_manager.py

class ChineseExcelManager:
    """Generate Chinese Excel files"""

    TRANSLATED_COLUMNS = [
        ("平均分", 10),
        ("LLM评分", 10),
        ("职位", 35),
        ("公司", 25),
        ("地点", 20),
        ("来源", 15),
        ("发布日期", 14),
        ("薪资", 18),
        ("远程", 8),
        ("链接", 45),
        # ... rest of columns
    ]

    def write_chinese_excel(self, scored_jobs: list[ScoredJob], translator: JobTranslator, output_path: Path) -> Path:
        """
        Generate jobs_pipeline_cn.xlsx

        Steps:
        1. Translate all jobs in batches
        2. Create Excel with Chinese column headers
        3. Write translated data
        4. Apply same styling as English version
        """
```

### Batch Translation Optimization

```python
# To handle large job lists efficiently

async def translate_batch(self, jobs: list[RawJob], batch_size: int = 10) -> list[dict]:
    """Translate multiple jobs in parallel batches"""
    results = []

    for i in range(0, len(jobs), batch_size):
        batch = jobs[i:i + batch_size]
        # Parallel LLM calls for each job in batch
        tasks = [self.translate_job(job) for job in batch]
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)

        # Rate limiting delay
        await asyncio.sleep(1.0)

    return results
```

---

## Web CV Upload System

### Technology Stack

**Backend:**
- **FastAPI** - Async Python web framework
  - Native async/await support
  - Automatic OpenAPI docs
  - Pydantic validation
  - Built-in BackgroundTasks

**Frontend:**
- **Simple HTML + JS** (initially)
  - File upload form
  - Progress indicator
  - Job status polling
- Optional: Streamlit for richer UI

**Background Processing:**
- **FastAPI BackgroundTasks** - For simple async operations
- Optional: **Celery + Redis** - For distributed processing

### Architecture

```
┌─────────────┐
│   Browser   │
│  (Client)   │
└──────┬──────┘
       │
       │ HTTP/REST
       ▼
┌─────────────────────────────────────┐
│         FastAPI Server           │
│                                  │
│  ┌────────────────────────────┐    │
│  │  API Endpoints          │    │
│  │                        │    │
│  │  POST /api/upload       │    │
│  │  GET  /api/status/:id  │    │
│  │  GET  /api/jobs/:id   │    │
│  │  GET  /api/users/:id  │    │
│  └────────────────────────────┘    │
│                                  │
│  ┌────────────────────────────┐    │
│  │  Background Worker       │    │
│  │                        │    │
│  │  - Parse CV            │    │
│  │  - Search jobs         │    │
│  │  - Score jobs          │    │
│  │  - Generate Excel      │    │
│  └────────────────────────────┘    │
│                                  │
│  ┌────────────────────────────┐    │
│  │  File System            │    │
│  │                        │    │
│  │  users/                │    │
│  │    └── {user_id}/      │    │
│  │        ├── cv.md        │    │
│  │        ├── profile.json  │    │
│  │        ├── jobs.xlsx    │    │
│  │        └── jobs_cn.xlsx│    │
│  └────────────────────────────┘    │
└─────────────────────────────────────┘
```

### Directory Structure

```
jobhunter/
├── src/
│   ├── main.py                    # Existing CLI
│   └── web/
│       ├── app.py                 # FastAPI application
│       ├── models/               # Web API models
│       ├── api/
│       │   ├── upload.py         # CV upload endpoint
│       │   ├── status.py         # Job status endpoint
│       │   └── jobs.py          # Job results endpoint
│       └── services/
│           ├── job_processor.py  # Background job processing
│           └── user_manager.py  # User/folder management
├── users/                         # User data directory
│   └── {user_id}/
│       ├── cv.md
│       ├── profile.json
│       ├── jobs_pipeline.xlsx
│       ├── jobs_pipeline_cn.xlsx
│       └── digests/
├── web_ui/                        # Static frontend
│   ├── index.html
│   ├── upload.html
│   ├── status.html
│   └── static/
│       ├── css/
│       └── js/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
└── pyproject.toml                  # Add FastAPI dependencies
```

### API Endpoints

#### 1. Upload CV

```python
@router.post("/api/upload")
async def upload_cv(
    file: UploadFile,
    user_id: str = Form(...),
    config: AppConfig = Depends(get_config)
):
    """
    Upload CV and trigger processing

    Request:
    - file: Markdown CV file
    - user_id: User identifier

    Response:
    {
        "job_id": "uuid",
        "status": "processing",
        "message": "CV uploaded successfully"
    }

    Process:
    1. Validate file (markdown format)
    2. Save to users/{user_id}/cv.md
    3. Create job record in users/{user_id}/jobs.json
    4. Trigger background processing
    5. Return job_id for status polling
    """
```

#### 2. Check Job Status

```python
@router.get("/api/status/{job_id}")
async def get_job_status(job_id: str):
    """
    Get current status of a job

    Response:
    {
        "job_id": "uuid",
        "status": "processing|completed|failed",
        "progress": 0-100,
        "current_step": "Parsing CV|Searching jobs|Scoring...",
        "error": null,
        "results": {
            "total_jobs": 150,
            "high_score_jobs": 25,
            "english_excel": "jobs_pipeline.xlsx",
            "chinese_excel": "jobs_pipeline_cn.xlsx"
        }
    }
    """
```

#### 3. Get Job Results

```python
@router.get("/api/jobs/{job_id}")
async def get_job_results(job_id: str):
    """
    Get processed job results

    Response:
    {
        "job_id": "uuid",
        "status": "completed",
        "jobs": [
            {
                "title": "AI Engineer",
                "title_cn": "AI工程师",
                "company": "Tech Corp",
                "score": 8.5,
                ...
            },
            ...
        ]
    }
    """
```

### Background Processing

```python
# src/web/services/job_processor.py

class JobProcessor:
    """Process uploaded CVs in background"""

    def __init__(self, config: AppConfig):
        self.config = config
        self.status_store = {}  # In-memory, or Redis for production

    async def process_upload(self, user_id: str, job_id: str, cv_path: Path) -> None:
        """
        Full pipeline execution

        Steps:
        1. Parse CV to profile
        2. Build queries
        3. Search all enabled sources
        4. Deduplicate jobs
        5. Score jobs (LLM)
        6. Generate English Excel
        7. Generate Chinese Excel
        8. Update status to completed
        """
        try:
            self.update_status(job_id, "parsing_cv", 10)

            # Step 1: Parse CV
            profile = await self.parse_cv(cv_path)

            self.update_status(job_id, "searching", 30)

            # Step 2: Search jobs
            jobs = await self.search_jobs(profile)

            self.update_status(job_id, "scoring", 60)

            # Step 3: Score jobs
            scored_jobs = await self.score_jobs(jobs, profile)

            self.update_status(job_id, "generating_output", 80)

            # Step 4: Generate outputs
            await self.generate_outputs(user_id, scored_jobs)

            self.update_status(job_id, "completed", 100, results={
                "total_jobs": len(scored_jobs),
                "english_excel": f"users/{user_id}/jobs_pipeline.xlsx",
                "chinese_excel": f"users/{user_id}/jobs_pipeline_cn.xlsx",
            })

        except Exception as e:
            self.update_status(job_id, "failed", 0, error=str(e))
            logger.error(f"Job {job_id} failed: {e}")
```

### Frontend Implementation

**upload.html:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>JobHunter - Upload CV</title>
</head>
<body>
    <h1>Upload Your CV</h1>
    <form id="uploadForm">
        <input type="text" id="userId" placeholder="Your ID (email or username)" required>
        <input type="file" id="cvFile" accept=".md,.markdown" required>
        <button type="submit">Upload & Process</button>
    </form>

    <div id="progress" style="display:none;">
        <h2>Processing...</h2>
        <div id="statusMessage"></div>
        <progress id="progressBar" value="0" max="100"></progress>
    </div>

    <div id="results" style="display:none;">
        <h2>Results</h2>
        <a href="#" id="englishExcel">Download English Excel</a>
        <a href="#" id="chineseExcel">Download Chinese Excel</a>
    </div>

    <script>
        // Auto-refresh status every 5 seconds
        setInterval(checkStatus, 5000);
    </script>
</body>
</html>
```

### Security Considerations

1. **File Upload Validation**:
   - File size limit: 10MB
   - Allowed extensions: .md, .markdown
   - Content type validation

2. **User ID Validation**:
   - Sanitize user_id (prevent path traversal)
   - Use UUID-based user folders

3. **Rate Limiting**:
   - Limit uploads per user per hour
   - Limit concurrent jobs per user

4. **Authentication (Optional for future)**:
   - JWT-based auth
   - User registration/login

---

## AI Platform Integration

### OpenClaw (Oh-My-OpenAgent) Integration

**Current Status:**
- Already has `SKILL.md` for OpenClaw
- Uses oh-my-openagent plugin system

**Updates Needed:**

1. **Update SKILL.md** to reflect new features:
```markdown
# JobHunter AI Agent

## Capabilities
- Multi-platform job search (DE + CN platforms)
- LLM-based job scoring
- CV parsing from Markdown
- Bilingual Excel generation
- Web-based CV upload

## New Features (2026)
- BOSS直聘 job scraping (MVP)
- Chinese Excel output
- FastAPI web interface for CV upload
- User-specific job tracking

## Usage
### CLI Mode (existing)
```bash
python -m src.main --mode full
```

### Web Mode (new)
```bash
python -m src.web.app
# Access at http://localhost:8000
```

## Configuration
All features configurable via config.yaml

See README_CN.md for Chinese documentation.
```

2. **Docker Configuration** for easy deployment:
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e .

# CLI mode
CMD ["python", "-m", "src.main"]

# Or web mode
# CMD ["python", "-m", "src.web.app"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  jobhunter-cli:
    build: .
    volumes:
      - ./config.yaml:/app/config.yaml
      - ./cv:/app/cv
      - ./outputs:/app/outputs
    command: python -m src.main

  jobhunter-web:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./config.yaml:/app/config.yaml
      - ./users:/app/users
    command: python -m src.web.app
```

### Claude Code Integration

**No changes needed** - Claude Code uses the same plugin system as OpenClaw (oh-my-openagent).

### Documentation Updates

Create comprehensive README for both English and Chinese users, covering:
1. Installation for each AI platform
2. Configuration for each platform
3. Usage examples
4. Troubleshooting

---

## Deployment Strategy

### Local/Docker Deployment

**Prerequisites:**
- Docker
- Docker Compose
- Python 3.11+ (if running locally)

**Installation:**

```bash
# 1. Clone repository
git clone https://github.com/YOUR/jobhunter.git
cd jobhunter

# 2. Configure
cp config.example.yaml config.yaml
# Edit config.yaml with your API keys and preferences

# 3. Setup environment
cp .env.example .env
# Add your LLM API keys

# 4. Run with Docker
docker-compose up -d

# CLI Mode: Process a single CV
docker-compose exec jobhunter-cli python -m src.main

# Web Mode: Start web server
docker-compose up jobhunter-web
# Access at http://localhost:8000
```

### File Structure After Deployment

```
jobhunter/
├── config.yaml              # Main configuration
├── .env                     # API keys
├── users/                   # User data (web mode)
│   ├── user@example.com/
│   │   ├── cv.md
│   │   ├── profile.json
│   │   ├── jobs_pipeline.xlsx
│   │   ├── jobs_pipeline_cn.xlsx
│   │   └── jobs.json        # Job status tracking
│   └── another@user.com/
│       └── ...
├── outputs/                  # CLI mode outputs
│   ├── jobs_pipeline.xlsx
│   ├── jobs_pipeline_cn.xlsx
│   └── digests/
├── memory/                  # Cache and job pool
│   ├── job_pool.json
│   └── candidate_profile.json
└── cv/                     # CLI mode CV storage
    └── cv_current.md
```

### Configuration Management

**Global Config** (config.yaml):
```yaml
# JobHunter configuration
candidate:
  cv_path: "./cv/cv_current.md"  # CLI mode

llm:
  text:
    provider: "volcengine"
    model: "doubao-seed-2.0-code"
    base_url: "https://ark.cn-beijing.volces.com/api/coding/v3"
    api_key_env: "ARK_API_KEY"

sources:
  bosszhipin:
    enabled: true
    city_code: "101010100"  # Beijing

  arbeitsagentur:
    enabled: true

  jobspy:
    enabled: true
    boards: ["indeed", "google"]

web:
  enabled: true
  host: "0.0.0.0"
  port: 8000
  upload_dir: "./users"
  max_file_size_mb: 10
```

**User-Specific Config** (optional):
- Users can override certain settings via request parameters
- Stored in `users/{user_id}/config.yaml`

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1)

- [ ] Create detailed architecture document (this file)
- [ ] Set up project structure for new features
- [ ] Add FastAPI dependencies to pyproject.toml
- [ ] Create base web application skeleton
- [ ] Implement user folder management service

### Phase 2: Web CV Upload (Week 2)

- [ ] Implement CV upload endpoint with validation
- [ ] Create job status tracking system
- [ ] Implement background job processor
- [ ] Create basic frontend UI (HTML/JS)
- [ ] Implement status polling endpoint
- [ ] Add results download functionality

### Phase 3: Chinese Excel (Week 3)

- [ ] Design translation module architecture
- [ ] Implement LLM-based job translator
- [ ] Add translation cache
- [ ] Implement Chinese Excel generator
- [ ] Add batch translation optimization
- [ ] Test with sample job data

### Phase 4: BOSS直聘 Integration (Week 4)

- [ ] Set up DrissionPage integration
- [ ] Implement BOSS直聘 scraper
- [ ] Add cookie management
- [ ] Implement rate limiting
- [ ] Add error handling and retries
- [ ] Test with real searches

### Phase 5: Documentation (Week 5)

- [ ] Write comprehensive README.md (English)
- [ ] Write comprehensive README_CN.md (Chinese)
- [ ] Create Docker setup guide
- [ ] Add AI platform integration docs
- [ ] Create troubleshooting guide
- [ ] Add example configurations

### Phase 6: Additional Platforms (Future)

- [ ] Implement 拉勾网 scraper
- [ ] Implement 猎聘 integration (Apify)
- [ ] Implement 51Job integration (Apify)
- [ ] Add platform-specific metadata extraction

### Phase 7: Enhancements (Future)

- [ ] Add user authentication
- [ ] Implement job alerts/notification system
- [ ] Add advanced filtering options
- [ ] Implement data visualization dashboard
- [ ] Add export to other formats (CSV, PDF)

---

## Testing Strategy

### Unit Tests

```python
# tests/test_translator.py

def test_job_translator_cache():
    """Test translation caching"""
    translator = JobTranslator(llm_client)
    job = create_test_job()

    # First call - should use LLM
    result1 = translator.translate_job(job)
    assert result1["title"] == "AI工程师"

    # Second call - should use cache
    result2 = translator.translate_job(job)
    assert result1 == result2

def test_batch_translation():
    """Test batch translation"""
    jobs = [create_test_job() for _ in range(20)]
    results = await translator.translate_batch(jobs, batch_size=5)

    assert len(results) == 20
    assert all("title_cn" in r for r in results)
```

### Integration Tests

```python
# tests/test_bosszhipin.py

@pytest.mark.asyncio
async def test_bosszhipin_search():
    """Test BOSS直聘 scraper"""
    source = BossZhipinSource()
    query = SearchQuery(
        keyword="AI工程师",
        location="北京",
        source="bosszhipin"
    )

    jobs = await source.search(query, config)

    assert len(jobs) > 0
    assert all(j.source == "bosszhipin" for j in jobs)
    assert all(j.title for j in jobs)
```

### End-to-End Tests

```python
# tests/test_web_pipeline.py

@pytest.mark.asyncio
async def test_cv_upload_pipeline():
    """Test full web upload pipeline"""
    # Upload CV
    response = client.post("/api/upload", files={
        "file": ("cv.md", sample_cv),
        "user_id": "test@example.com"
    })

    job_id = response.json()["job_id"]

    # Wait for completion
    await asyncio.sleep(30)

    # Check status
    status = client.get(f"/api/status/{job_id}").json()
    assert status["status"] == "completed"
    assert status["progress"] == 100

    # Download results
    english_excel = client.get(f"/api/jobs/{job_id}").json()["results"]["english_excel"]
    assert Path(english_excel).exists()
    assert Path(english_excel.replace(".xlsx", "_cn.xlsx")).exists()
```

---

## Performance Considerations

### Scalability

1. **CV Processing**:
   - Async LLM calls (batch of 5 jobs at a time)
   - Cache translations to avoid repeated calls
   - Limit concurrent jobs per user

2. **Web Server**:
   - FastAPI async by default
   - Use Gunicorn/Uvicorn for production
   - Horizontal scaling via Docker

3. **Job Scraping**:
   - Parallel source queries
   - Rate limiting per source
   - Deduplication before LLM scoring

### Caching Strategy

```python
# Cache layers
1. LLM Response Cache: In-memory (Redis for prod)
   - Cache LLM scoring results
   - Cache translations
   - TTL: 24 hours

2. Job Pool Cache: disk (JSON)
   - Persistent storage
   - Incremental updates

3. Translation Cache: disk (JSON)
   - Per-language dictionaries
   - Pre-translated common terms
```

### Resource Limits

```yaml
# config.yaml
runtime:
  max_concurrent_llm_calls: 5
  max_concurrent_scrapers: 3
  max_jobs_per_user: 100
  cache_ttl_hours: 24
```

---

## Monitoring and Logging

### Logging Structure

```python
# Structured logging
logger.info("job_started", extra={
    "job_id": job_id,
    "user_id": user_id,
    "timestamp": datetime.now().isoformat()
})

logger.info("job_completed", extra={
    "job_id": job_id,
    "duration_seconds": duration,
    "total_jobs": len(jobs),
    "scored_jobs": len(scored_jobs)
})
```

### Metrics to Track

- CV upload success rate
- Average processing time per CV
- Job count per source
- LLM API call latency
- Error rate per platform
- Cache hit rate

### Health Checks

```python
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": get_version(),
        "services": {
            "llm": await check_llm_connection(),
            "storage": check_disk_space(),
            "scrapers": check_scraper_health()
        }
    }
```

---

## Security Best Practices

1. **API Keys**: Never commit to git, use environment variables
2. **File Uploads**: Validate file type, size, content
3. **User Input**: Sanitize all inputs, prevent injection attacks
4. **Rate Limiting**: Protect against abuse
5. **HTTPS**: Use HTTPS in production
6. **Authentication**: Add JWT auth for production use
7. **CORS**: Configure CORS policy properly
8. **Secrets**: Rotate API keys regularly

---

## Troubleshooting

### Common Issues

1. **BOSS直聘 scraper returns no jobs**:
   - Check city_code is valid
   - Verify cookies are saved
   - Check rate limiting delays
   - Try with VPN/proxy

2. **Translation fails**:
   - Check LLM API key is valid
   - Verify LLM endpoint is accessible
   - Check request timeout settings

3. **Web upload fails**:
   - Verify CV is valid Markdown
   - Check file size limit
   - Check disk space
   - Review server logs

4. **Chinese Excel generation slow**:
   - Reduce batch size
   - Enable translation cache
   - Use faster LLM model for translation

---

## Conclusion

This architecture provides a solid foundation for extending the JobHunter project with Chinese job platforms, multilingual Excel output, and web-based CV upload.

**Key Strengths:**
- Modular design allows incremental implementation
- Async-first approach ensures scalability
- Configuration-driven for flexibility
- Docker-ready for easy deployment
- Comprehensive error handling and monitoring

**Next Steps:**
1. Review and approve this architecture
2. Set up development environment
3. Implement Phase 1 (Foundation)
4. Iterate through remaining phases

---

*Document Version: 1.0*
*Last Updated: 2026-03-07*
*Author: AI Agent*
