.PHONY: dev-db dev-backend dev-frontend dev migrate

dev-db:
	docker compose up postgres redis -d

dev-backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

migrate:
	cd backend && .venv/bin/alembic upgrade head

migrate-create:
	cd backend && .venv/bin/alembic revision --autogenerate -m "$(name)"

test-backend:
	cd backend && .venv/bin/pytest -v

gen-api-key:
	@prefix=$${prefix:-dev}; python3 -c "import secrets; print(f'gsk_$${prefix}_{secrets.token_urlsafe(32)}')"

new-quarter:
	python3 gst-engine/scripts/new_quarter.py $(q)

dev-gst-engine:
	cd gst-engine && ../backend/.venv/bin/uvicorn api.main:app --reload --host 0.0.0.0 --port 8001

test-gst-engine:
	cd gst-engine && ../backend/.venv/bin/pytest tests/ -v

install:
	cd backend && /opt/homebrew/bin/python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt "pydantic[email]"
	cd frontend && npm install
