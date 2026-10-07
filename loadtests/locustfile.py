from locust import HttpUser, task, between

class AgriScopeUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def test_health(self):
        self.client.get("/health")

    @task(1)
    def test_ready(self):
        self.client.get("/ready")
