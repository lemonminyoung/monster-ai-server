import os
from flask import Flask, request, jsonify
import google.generativeai as genai

# Flask 앱을 생성합니다.
app = Flask(__name__)

# Render의 'Environment Variable'(환경 변수)에서 Gemini API 키를 가져옵니다.
try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
except Exception as e:
    print(f"API Key 설정 중 에러 발생: {e}")

# '/api/ask' 라는 주소로 POST 방식의 요청을 처리할 API 엔드포인트를 만듭니다.
@app.route("/api/ask", methods=["POST"])
def ask_gemini():
    # 요청받은 데이터가 JSON 형식이 아니면 에러를 반환합니다.
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    # JSON 데이터에서 'question' 값을 가져옵니다.
    data = request.get_json()
    question = data.get("question")

    # 'question' 값이 없으면 에러를 반환합니다.
    if not question:
        return jsonify({"error": "Missing 'question' in request body"}), 400

    # Gemini API에 요청을 보내기 전, 에러가 발생할 경우를 대비합니다.
    try:
        # Gemini 모델을 선택합니다. 'gemini-1.5-flash'는 빠르고 저렴한 최신 모델입니다.
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # AI에게 답변을 생성하도록 요청합니다.
        response = model.generate_content(question)
        
        # 성공적인 답변을 JSON 형태로 클라이언트에게 반환합니다.
        return jsonify({"answer": response.text})

    except Exception as e:
        # API 호출 중 에러가 발생하면 서버 로그에 에러를 출력하고 클라이언트에게 에러 메시지를 보냅니다.
        print(f"An error occurred: {e}")
        return jsonify({"error": "Failed to get response from AI"}), 500

# 이 파일이 직접 실행될 때 테스트용으로 내장 서버를 실행합니다.
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
