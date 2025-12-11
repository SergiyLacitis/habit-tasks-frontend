from datetime import date
from typing import Any, Dict, List, Optional

import httpx


class APIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000/api/v1"):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.client = httpx.Client(base_url=base_url, timeout=10.0)
        self.user_role: Optional[str] = None

    def set_tokens(self, access: str, refresh: str = None):
        self.access_token = access
        if refresh:
            self.refresh_token = refresh
        self.client.headers["Authorization"] = f"Bearer {access}"

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            response = self.client.request(method, url, **kwargs)
            if response.status_code == 401 and self.refresh_token:
                print("Token expired. Refreshing...")
                if self.refresh_session():
                    self.client.headers["Authorization"] = f"Bearer {self.access_token}"
                    return self.client.request(method, url, **kwargs)

            response.raise_for_status()
            return response
        except httpx.HTTPError as e:
            print(f"API Error [{method} {url}]: {e}")
            raise e

    def login(self, username, password) -> bool:
        try:
            response = self.client.post(
                "/auth/login", data={"username": username, "password": password}
            )
            response.raise_for_status()
            data = response.json()
            self.set_tokens(data["access_token"], data.get("refresh_token"))

            me = self.get_me()
            self.user_role = me.get("role", "user")
            return True
        except Exception as e:
            print(f"Login failed: {e}")
            return False

    def register(self, username, email, password) -> bool:
        try:
            response = self.client.post(
                "/auth/register",
                json={"username": username, "email": email, "password": password},
            )
            response.raise_for_status()
            data = response.json()
            self.set_tokens(data["access_token"], data.get("refresh_token"))
            self.user_role = "user"
            return True
        except Exception as e:
            print(f"Registration failed: {e}")
            return False

    def refresh_session(self) -> bool:
        try:
            temp_client = httpx.Client(base_url=self.base_url)
            temp_client.headers["Authorization"] = f"Bearer {self.refresh_token}"
            response = temp_client.post("/auth/refresh")
            response.raise_for_status()
            data = response.json()
            self.set_tokens(data["access_token"], data.get("refresh_token"))
            return True
        except Exception:
            return False

    def get_me(self) -> Dict[str, Any]:
        return self._request("GET", "/auth/users/me").json()

    def get_tasks(self) -> List[Dict[str, Any]]:
        try:
            return self._request("GET", "/tasks/").json()
        except Exception:
            return []

    def create_task(self, title: str, description: str = None) -> bool:
        try:
            self._request(
                "POST",
                "/tasks/",
                json={
                    "title": title,
                    "description": description,
                },
            )
            return True
        except Exception:
            return False

    def update_task(self, task_id: int, title: str, description: str) -> bool:
        try:
            payload = {
                "title": title,
                "description": description,
            }

            self._request(
                "PATCH",
                f"/tasks/{task_id}",
                json={k: v for k, v in payload.items() if v is not None},
            )
            return True
        except Exception:
            return False

    def delete_task(self, task_id: int) -> bool:
        try:
            self._request("DELETE", f"/tasks/{task_id}")
            return True
        except Exception:
            return False

    def get_task_logs(
        self, task_id: int, date_from: date = None
    ) -> List[Dict[str, Any]]:
        params = {}
        if date_from:
            params["date_from"] = date_from.isoformat()
        try:
            return self._request("GET", f"/tasks/{task_id}/logs", params=params).json()
        except Exception:
            return []

    def set_log_status(self, task_id: int, log_date: date, status: bool) -> bool:
        try:
            if status:
                payload = {
                    "created_tasks": [],
                    "new_logs": [
                        {
                            "task_id": task_id,
                            "date": log_date.isoformat(),
                            "status": True,
                        }
                    ],
                }
                self._request("POST", "/sync/", json=payload)
            else:
                self._request(
                    "DELETE",
                    f"/taclsks/{task_id}/complete",
                    params={"date": log_date.isoformat()},
                )
            return True
        except Exception as e:
            print(f"Set log status error: {e}")
            return False

    def toggle_today(self, task_id: int, current_status: bool) -> bool:
        return self.set_log_status(task_id, date.today(), not current_status)

    def get_all_users(self) -> List[Dict[str, Any]]:
        try:
            return self._request("GET", "/users/").json()
        except Exception:
            return []


api = APIClient()