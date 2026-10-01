import os
import hashlib
from io import BytesIO

import streamlit as st
from dotenv import load_dotenv
from PIL import Image

from nail_lab.adapters.youcam import YouCamError, YouCamGateway
from nail_lab.application.transfer import TransferError, run_transfer
from nail_lab.domain.images import InputError


load_dotenv()
st.set_page_config(page_title="네일 트랜스퍼 실험실", page_icon="💅")
st.title("💅 네일 트랜스퍼 실험실")
st.caption("손 사진과 마음에 드는 네일 디자인 사진을 올려 적용 결과를 확인하세요.")

key = os.getenv("YOUCAM_API_KEY", "").strip()
if not key:
    st.info("실행 전에 .env 파일에 YOUCAM_API_KEY를 설정하세요. 아래에서 사진은 미리 확인할 수 있습니다.")

with st.form("transfer"):
    left, right = st.columns(2)
    with left:
        hand = st.file_uploader("1. 손 사진", type=["jpg", "jpeg", "png"], key="hand")
    with right:
        design = st.file_uploader("2. 네일 디자인 참고 사진", type=["jpg", "jpeg", "png"], key="design")
    submitted = st.form_submit_button("네일 적용하기", disabled=not key)

if hand or design:
    left, right = st.columns(2)
    if hand:
        left.image(hand, caption="원본 손 사진", width="stretch")
    if design:
        right.image(design, caption="참고 디자인", width="stretch")

current_inputs = tuple(
    hashlib.sha256(upload.getvalue()).hexdigest() if upload else None
    for upload in (hand, design)
)
if st.session_state.get("result_inputs") != current_inputs:
    st.session_state.pop("result", None)

if submitted:
    if not hand or not design:
        st.warning("사진 두 장을 모두 올려주세요.")
    else:
        try:
            with st.status("작업 준비 중", expanded=True) as progress:
                result = run_transfer(
                    hand.getvalue(), design.getvalue(), YouCamGateway(key),
                    on_progress=lambda message: progress.update(label=message),
                )
                progress.update(label="완료", state="complete")
            st.session_state["result"] = result
            st.session_state["result_inputs"] = current_inputs
        except (InputError, TransferError, YouCamError) as exc:
            st.error(str(exc))

if result := st.session_state.get("result"):
    st.subheader("적용 결과")
    st.image(result, width="stretch")
    try:
        with Image.open(BytesIO(result)) as image:
            is_png = image.format == "PNG"
    except (OSError, ValueError):
        is_png = False
    st.download_button(
        "결과 이미지 저장", data=result,
        file_name="nail-transfer-result.png" if is_png else "nail-transfer-result.jpg",
        mime="image/png" if is_png else "image/jpeg",
    )

st.caption("JPG/PNG · 각 10 MB 미만 · 긴 변 4096px 이하 · 손톱이 선명하게 보이는 사진 권장")
