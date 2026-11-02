.PHONY: up down logs ps health
up:
	docker compose up -d --build
down:
	docker compose down
logs:
	docker compose logs -f --tail=200
ps:
	docker compose ps
health:
	curl -fsS http://localhost:8080/health
