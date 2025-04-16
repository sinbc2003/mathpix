import streamlit as st
import requests
import base64
import time

st.title("PDF to Markdown with Mathpix")
st.write("""
이 앱은 교사의 수업자료를 PDF로 업로드하면,
해당 PDF를 **Markdown** 형식의 txt파일로 변환하여 다운로드할 수 있게 해줍니다.
""")

# 파일 업로더
uploaded_file = st.file_uploader("PDF 파일을 업로드하세요", type=["pdf"])

def convert_pdf_to_markdown(pdf_bytes: bytes, app_id: str, app_key: str) -> str:
    """
    Mathpix PDF OCR API를 통해 PDF 파일을 Markdown 형태의 텍스트로 변환합니다.
    반환값: 변환된 Markdown 텍스트 (실패 시 None)
    """
    # PDF를 base64로 인코딩
    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

    # PDF 변환 요청 URL
    post_url = "https://api.mathpix.com/v3/pdf"

    headers = {
        "app_id": app_id,
        "app_key": app_key,
        "Content-Type": "application/json"
    }

    # API 요청 바디
    data = {
        "urls": [],        # URL 대신 직접 업로드할 때는 "files" + base64 사용
        "files": [b64_pdf],
        "formats": ["markdown"],  # html, text 등 가능
        "ocr": ["math"],          # 수식 OCR
        "metadata": False
    }

    # 1) 비동기 PDF 변환 프로세스 시작
    response = requests.post(post_url, headers=headers, json=data)
    if response.status_code != 200:
        st.error(f"Mathpix API 에러: {response.text}")
        return None

    # API가 반환한 pdf_id 추출
    pdf_id = response.json().get("pdf_id", None)
    if not pdf_id:
        st.error("pdf_id를 가져오지 못했습니다.")
        return None

    # 2) 변환 상태를 주기적으로 확인 (폴링)
    get_url = f"https://api.mathpix.com/v3/pdf/{pdf_id}?formats=markdown"

    while True:
        poll_res = requests.get(get_url, headers=headers)
        if poll_res.status_code != 200:
            st.error(f"폴링 중 에러: {poll_res.text}")
            return None

        poll_json = poll_res.json()
        status = poll_json.get("status", "")

        if status == "completed":
            # 변환된 데이터의 다운로드 URL (markdown_url)
            markdown_url = poll_json.get("markdown", None)
            if not markdown_url:
                st.error("Markdown URL을 가져오지 못했습니다.")
                return None

            # 최종 변환 결과 (Markdown 텍스트) 가져오기
            md_res = requests.get(markdown_url)
            if md_res.status_code == 200:
                return md_res.text
            else:
                st.error("변환 결과 텍스트를 가져오지 못했습니다.")
                return None

        elif status in ["queued", "processing"]:
            time.sleep(5)
            continue
        else:
            st.error(f"처리 실패 혹은 알 수 없는 상태: {poll_json}")
            return None

# 메인 로직
if uploaded_file is not None:
    # Secrets에서 API 정보 가져오기
    # => Streamlit Cloud의 'Project settings -> Secrets'에 아래처럼 저장했다고 가정:
    # [mathpix]
    # app_id = "YOUR_APP_ID"
    # app_key = "YOUR_APP_KEY"
    app_id = st.secrets["mathpix"]["app_id"]
    app_key = st.secrets["mathpix"]["app_key"]

    with st.spinner("Mathpix API를 통해 변환 중입니다. 잠시만 기다려 주세요..."):
        pdf_bytes = uploaded_file.read()
        result_markdown = convert_pdf_to_markdown(pdf_bytes, app_id, app_key)

    if result_markdown:
        st.success("PDF → Markdown 변환이 완료되었습니다!")
        # 결과 미리보기
        st.subheader("변환 결과 미리보기")
        st.write(result_markdown)

        # 다운로드 버튼 (txt 파일)
        st.download_button(
            label="결과 다운로드 (.txt)",
            data=result_markdown,
            file_name="converted_markdown.txt",
            mime="text/plain"
        )

