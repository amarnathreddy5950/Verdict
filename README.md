# Portfolio Projects (planned)

Build order chosen to maximize signal for the target companies (Cohere, Hugging Face,
Weights & Biases, GitLab, Sourcegraph, Zapier). Lead with evaluation + production rigor,
which is the rare strength most candidates lack.

## 1. llm-eval-toolkit  (flagship — build first)
An open-source LLM-as-judge evaluation harness.
- Define test cases, run candidate prompts/agents across models (OpenAI / Anthropic / Bedrock)
- Score with judge models + rule-based checks; track regressions; output a comparison report
- GitHub Actions workflow that runs evals on every commit
- **Targets:** Weights & Biases, Arize, Comet, Braintrust, Humanloop, Cohere, Hugging Face

## 2. agent-investigator
A multi-step AI agent (public, model-agnostic analog of the AWS RCA work).
- Orchestrator plans steps, calls tools, produces an explained root-cause report
- Plug in the eval toolkit (#1) to grade its outputs
- **Targets:** LangChain/LangGraph, CrewAI, Sourcegraph, Zapier, Cohere

## 3. rag-benchmark
A RAG service with a rigorous benchmark report.
- Measure retrieval quality, latency, and cost across embedding models / vector DBs
  (Pinecone vs Weaviate vs Qdrant), with a written tradeoff analysis
- **Targets:** Pinecone, Weaviate, Qdrant, Cohere, Hugging Face

## Force multipliers
- Profile README (see ../github-profile/README.md) — done, ready to copy-paste
- One OSS contribution to a framework the targets maintain (LangGraph / LlamaIndex / CrewAI)
- A short writeup/blog: "how I built and evaluated an agent"
- LLM observability layer (OpenTelemetry traces + Grafana dashboard) on top of #2
