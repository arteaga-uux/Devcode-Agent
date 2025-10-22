# GNOME Code Assistant

An AI-powered code assistant for GNOME development using LangGraph agents, RAG (Retrieval-Augmented Generation), and incremental vectorization.

## 🏗️ Architecture

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │  LangGraph Agent │    │  RAG Pipeline   │
│   (azure_app.py)│◄──►│    (agent.py)    │◄──►│ (context_builder│
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Code Tools     │    │ File Tracker     │    │ Vector Store    │
│ (code_tools.py) │    │(file_tracker.py) │    │   (FAISS)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Key Features

- **Smart Routing**: Agent decides between RAG, direct answers, or code tools
- **Incremental Updates**: Only re-processes modified files
- **File Operations**: Read files, search code, propose edits (safely)
- **Azure Ready**: FastAPI with background tasks and health checks

## 🚀 Quick Start

### Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables**:
   ```bash
   export OPENAI_API_KEY="your_key_here"
   export DEBUG=true
   # Optional: set codebase root for RAG (defaults to gdm/daemon)
   export CODEBASE_DIR="/absolute/path/to/your/codebase"
   ```

3. **Run the agent**:
   ```bash
   # Test the agent directly
   python agent.py "explain the login process"
   
   # Run the FastAPI server
   python app.py

   # Run the eval harness (W1 localization)
   python -m eval.runner.run_localization
   ```

### Cloud Deployment

The project supports deployment to multiple cloud providers:

- **Azure**: See [deployments/azure/azure-deploy.md](deployments/azure/azure-deploy.md)
- **Google Cloud**: See [deployments/gcp/deploy.md](deployments/gcp/deploy.md)  
- **AWS**: See [deployments/aws/deploy.md](deployments/aws/deploy.md)

## 📁 Project Structure

```
Gnome Assistant/
├── config.py              # Centralized configuration
├── agent.py               # Shim → my_agent/agent.py
├── app.py                 # Shim → my_agent/app.py
├── code_tools.py          # File operations and code search
├── file_tracker.py        # Incremental vectorization tracking
├── incremental_pipeline.py # Smart rebuild pipeline
├── my_agent/              # Agent + RAG package
│   ├── agent.py           # LangGraph agent with decision routing
│   ├── app.py             # FastAPI app
│   ├── context_builder.py # RAG context construction
│   ├── context_formatter.py
│   ├── retriever.py       # Vector store retrieval
│   ├── build_vectorstore.py
│   ├── chunking.py
│   ├── ingest_project.py
│   ├── discovery.py
│   ├── loader.py
│   ├── embedder.py
│   ├── file_tracker.py
│   ├── code_tools.py
│   └── incremental_pipeline.py
├── utils/
│   └── token_counter.py   # Token counting utilities
├── vectorstore/           # FAISS index storage
├── gdm/                   # GNOME source code (RAG default root: gdm/daemon)
├── eval/                  # Evaluation harness (W1/W2, config+metrics+runners)
├── requirements.txt       # Python dependencies
├── deployments/           # Cloud-specific deployment configs
│   ├── azure/            # Azure deployment files
│   ├── gcp/              # Google Cloud deployment files
│   └── aws/              # AWS deployment files
└── README.md             # This file
```

### Eval Harness Overview
- Config: `eval/config/config.yaml` (centralized thresholds/paths; env overrides in `eval/config/.env.example`)
- Runners: `eval/runner/run_localization.py`, `eval/runner/run_change_impact.py`
- Metrics: `eval/metrics/*`
- Data: `eval/scenarios/*`, `eval/goldens/*`, `eval/canary/*`
- Reports/Registry: `eval/reports/`, `eval/registry/`

## 🎯 Agent Capabilities

### Code Suggestions Context

The agent suggests code changes in these scenarios:

1. **User Requests**: "Fix this bug", "Optimize this function"
2. **Error Detection**: Syntax errors, potential issues
3. **Best Practices**: Code style, performance improvements
4. **Refactoring**: "Make this more modular", "Add error handling"

**Safety**: All suggestions are **proposals only** - no files are modified without explicit confirmation.

### Decision Routing

The agent intelligently routes queries:

- **RAG Path**: "How does authentication work?" → Search codebase + explain
- **Direct Answer**: "What is a function pointer?" → General programming knowledge
- **Code Tools**: "Read file X", "Search for function Y" → Direct file operations

## ⚙️ Configuration

All settings are centralized in `config.py`:

```python
# Model settings
GENERATION_MODEL_NAME = "gpt-4o-mini"
EMBEDDING_MODEL_NAME = "text-embedding-3-small"

# RAG settings
CONFIG.top_k = 4
CONFIG.max_tokens = 5000
CONFIG.chunk_size = 300

# Codebase root for RAG (default gdm/daemon); override with env CODEBASE_DIR
SOURCE_DIRECTORY = Path(os.getenv("CODEBASE_DIR", str(PROJECT_ROOT / "gdm" / "daemon")))

# Safety settings
CONFIG.allow_file_modification = False  # Only propose, never modify
CONFIG.require_confirmation_for_edits = True
```

## 🔧 API Usage

### Query the Agent

```bash
curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"query": "explain the login process"}'
```

### Rebuild Vectorstore

```bash
curl -X POST "http://localhost:8000/rebuild" \
     -H "Content-Type: application/json" \
     -d '{"force_full": false}'
```

### Check Status

```bash
curl http://localhost:8000/health
curl http://localhost:8000/rebuild/status
```

## 🧪 Testing

```bash
# Test agent directly
python agent.py "read the main function in gdm-chooser.c"

# Test incremental pipeline
python incremental_pipeline.py --status
python incremental_pipeline.py --force

# Test FastAPI endpoints
python -m pytest tests/
```

## 🔒 Security Considerations

- **File Access**: Limited to configured source directory
- **Code Modifications**: Proposals only, requires confirmation
- **API Keys**: Use environment variables, never hardcode
- **CORS**: Configure appropriately for production
- **Input Validation**: Pydantic models validate all inputs

## 📊 Performance

- **Incremental Updates**: Only processes modified files
- **Background Tasks**: Non-blocking vectorstore rebuilds
- **Token Budgeting**: Efficient context construction
- **Caching**: File modification tracking prevents unnecessary work

## 🚀 Next Steps

1. **Test locally** with your GNOME codebase
2. **Deploy to Azure** using the provided guide
3. **Customize** the agent for your specific needs
4. **Add more tools** as needed (testing, documentation, etc.)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
