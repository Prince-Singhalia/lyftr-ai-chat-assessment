up:
	docker compose up --build -d
down:
	docker compose down
test:
	python -m pytest backend/tests -q
frontend-build:
	cd frontend && npm install && npm run build

