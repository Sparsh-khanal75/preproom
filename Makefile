.PHONY: up up-ollama demo down test lint api-dev worker-dev web-dev gen-api

up:            ## Run everything with Docker (uses .env)
	docker compose up -d --build
up-ollama:     ## Same, plus a local Ollama container, and pull the model
	docker compose --profile ollama up -d --build
	docker compose exec ollama ollama pull $${OLLAMA_MODEL:-qwen2.5:7b}
demo:          ## Create demo accounts and two scored interviews
	docker compose exec api python -m app.seed
down:
	docker compose down

test:
	cd api && pytest
	cd web && npm test
lint:
	cd api && ruff check . && ruff format --check .
	cd web && npm run lint && npm run typecheck

api-dev:
	cd api && uvicorn app.main:app --reload
worker-dev:
	cd api && python -m app.jobs.worker
web-dev:
	cd web && npm run dev
gen-api:       ## Regenerate the OpenAPI schema and the typed web client
	cd api && python -c "import json; from app.main import app; print(json.dumps(app.openapi(), indent=2))" > openapi.json
	cd web && npm run gen:api
