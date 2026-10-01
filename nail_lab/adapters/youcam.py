import requests

from nail_lab.domain.images import NailImage


BASE_URL = "https://yce-api-01.makeupar.com"


class YouCamError(Exception):
    pass


class YouCamGateway:
    def __init__(self, api_key: str, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def _json(self, method: str, path: str, **kwargs) -> dict:
        try:
            response = self.session.request(
                method, BASE_URL + path, headers=self.headers, timeout=30, **kwargs
            )
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise YouCamError(f"YouCam 요청 오류 ({path}): {exc}") from exc
        if body.get("status") != 200 or not isinstance(body.get("data"), dict):
            raise YouCamError(f"YouCam 응답 오류: {body.get('error') or body.get('error_code') or '응답 형식 확인 필요'}")
        return body["data"]

    def upload(self, image: NailImage) -> str:
        data = self._json("POST", "/s2s/v2.0/file", json={"files": [{
            "file_name": image.file_name,
            "file_size": len(image.data),
            "content_type": image.content_type,
        }]})
        try:
            item = data["files"][0]
            upload = item["requests"][0]
            file_id = item["file_id"]
            url = upload["url"]
            headers = upload["headers"]
            if upload["method"] != "PUT" or not url.startswith("https://"):
                raise ValueError("업로드 방식이 예상과 다릅니다")
        except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
            raise YouCamError("파일 업로드 URL 응답을 해석할 수 없습니다.") from exc
        try:
            # Signed URL has its own headers. Never forward the API key to storage.
            response = self.session.put(url, data=image.data, headers=headers, timeout=60)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise YouCamError(f"이미지 업로드 실패: {exc}") from exc
        return file_id

    def create_task(self, source_id: str, reference_id: str) -> str:
        data = self._json("POST", "/s2s/v2.0/task/ai-nail", json={
            "src_file_id": source_id, "ref_file_id": reference_id,
        })
        task_id = data.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise YouCamError("작업 ID가 없는 응답입니다.")
        return task_id

    def task_status(self, task_id: str) -> dict:
        return self._json("GET", f"/s2s/v2.0/task/ai-nail/{task_id}")

    def download_result(self, url: str) -> bytes:
        if not url.startswith("https://"):
            raise YouCamError("결과 URL 형식이 올바르지 않습니다.")
        try:
            with self.session.get(url, timeout=60, stream=True) as response:
                response.raise_for_status()
                chunks = []
                total = 0
                for chunk in response.iter_content(chunk_size=65536):
                    total += len(chunk)
                    if total > 20_000_000:
                        raise YouCamError("결과 이미지가 20 MB를 초과합니다.")
                    chunks.append(chunk)
                result = b"".join(chunks)
                if not result:
                    raise YouCamError("빈 결과 이미지입니다.")
                return result
        except requests.RequestException as exc:
            raise YouCamError(f"결과 다운로드 실패: {exc}") from exc
