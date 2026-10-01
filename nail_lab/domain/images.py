from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError


MAX_BYTES = 10_000_000
MAX_SIDE = 4096
JPEG_QUALITIES = (90, 80, 70)


@dataclass(frozen=True)
class NailImage:
    data: bytes
    content_type: str
    file_name: str


class InputError(ValueError):
    pass


def validate_image(data: bytes, role: str) -> NailImage:
    if not data or len(data) >= MAX_BYTES:
        raise InputError(
            f"{role}: 10 MB 미만의 이미지를 올려주세요."
        )

    try:
        with Image.open(BytesIO(data)) as img:
            # MPO처럼 사진이 여러 장이면 첫 번째 사진을 사용합니다.
            img.seek(0)

            # 카메라 회전을 반영하고, 큰 사진은 비율을 유지하며 줄입니다.
            oriented = ImageOps.exif_transpose(img)
            oriented.thumbnail(
                (MAX_SIDE, MAX_SIDE),
                Image.Resampling.LANCZOS,
            )

            # 투명 배경은 JPEG로 바꾸기 전에 흰색으로 채웁니다.
            if "A" in oriented.getbands() or "transparency" in oriented.info:
                rgba = oriented.convert("RGBA")
                canvas = Image.new("RGB", rgba.size, "white")
                canvas.paste(rgba, mask=rgba.getchannel("A"))
                rgb = canvas
            else:
                rgb = oriented.convert("RGB")

            # 실제 JPEG 파일로 변환합니다.
            for quality in JPEG_QUALITIES:
                output = BytesIO()
                rgb.save(
                    output,
                    format="JPEG",
                    quality=quality,
                    optimize=True,
                )
                converted = output.getvalue()

                if len(converted) < MAX_BYTES:
                    return NailImage(
                        data=converted,
                        content_type="image/jpeg",
                        file_name=f"{role}.jpg",
                    )

    except InputError:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        SyntaxError,
        EOFError,
    ) as exc:
        raise InputError(
            f"{role}: 이미지를 읽거나 JPG로 변환할 수 없습니다."
        ) from exc

    raise InputError(
        f"{role}: 변환한 이미지도 10 MB 이상입니다. 작은 사진을 올려주세요."
    )