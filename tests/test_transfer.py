import unittest
from io import BytesIO

from PIL import Image

from nail_lab.application.transfer import TransferError, run_transfer
from nail_lab.domain.images import InputError


def photo():
    buffer = BytesIO()
    Image.new("RGB", (64, 64), "pink").save(buffer, "JPEG")
    return buffer.getvalue()


class FakeGateway:
    def __init__(self, statuses):
        self.statuses = iter(statuses)
        self.uploads = []
        self.tasks = []

    def upload(self, image):
        self.uploads.append(image)
        return str(len(self.uploads))

    def create_task(self, source_id, reference_id):
        self.tasks.append((source_id, reference_id))
        return "task-1"

    def task_status(self, task_id):
        return next(self.statuses)

    def download_result(self, url):
        return b"image-result"


class TransferTests(unittest.TestCase):
    def test_two_uploads_and_poll_success(self):
        gateway = FakeGateway([
            {"task_status": "running"},
            {"task_status": "success", "results": {"url": "https://example.com/result.jpg"}},
        ])
        delays = []
        result = run_transfer(photo(), photo(), gateway, sleep=delays.append)
        self.assertEqual(result, b"image-result")
        self.assertEqual(gateway.tasks, [("1", "2")])
        self.assertEqual(delays, [10])

    def test_invalid_image_does_not_call_api(self):
        gateway = FakeGateway([])
        with self.assertRaises(InputError):
            run_transfer(b"not-image", photo(), gateway)
        self.assertEqual(gateway.uploads, [])

    def test_provider_error_stops_polling(self):
        gateway = FakeGateway([{"task_status": "error", "error": "no_hand_detected"}])
        with self.assertRaisesRegex(TransferError, "no_hand_detected"):
            run_transfer(photo(), photo(), gateway)
        self.assertEqual(len(gateway.tasks), 1)


if __name__ == "__main__":
    unittest.main()
