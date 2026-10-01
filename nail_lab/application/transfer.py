import time
from collections.abc import Callable

from nail_lab.application.ports import NailTransferGateway
from nail_lab.domain.images import validate_image


class TransferError(Exception):
    pass


def run_transfer(
    hand: bytes,
    design: bytes,
    gateway: NailTransferGateway,
    on_progress: Callable[[str], None] = lambda _: None,
    sleep: Callable[[float], None] = time.sleep,
    max_checks: int = 18,
) -> bytes:
    """At most ~3 minutes of polling; a task is submitted exactly once."""
    source = validate_image(hand, "손 사진")
    reference = validate_image(design, "네일 디자인 사진")
    on_progress("손 사진 업로드 중")
    source_id = gateway.upload(source)
    on_progress("디자인 사진 업로드 중")
    reference_id = gateway.upload(reference)
    on_progress("네일 적용 작업 요청 중")
    task_id = gateway.create_task(source_id, reference_id)
    for check in range(max_checks):
        if check:
            sleep(10)
        on_progress(f"결과 생성 중 · 상태 확인 {check + 1}/{max_checks}")
        data = gateway.task_status(task_id)
        status = data.get("task_status")
        if status == "error":
            reason = data.get("error_message") or data.get("error") or "원인을 알 수 없습니다."
            raise TransferError(f"YouCam 처리 실패: {reason}")
        if status == "success":
            results = data.get("results")
            url = results.get("url") if isinstance(results, dict) else None
            if not isinstance(url, str) or not url.startswith("https://"):
                raise TransferError("작업이 완료되었지만 결과 이미지 URL이 없습니다.")
            on_progress("결과 이미지 다운로드 중")
            return gateway.download_result(url)
        if status != "running":
            raise TransferError(f"알 수 없는 작업 상태: {status!r}")
    raise TransferError(f"시간 내에 완료되지 않았습니다. 작업 ID: {task_id}")
