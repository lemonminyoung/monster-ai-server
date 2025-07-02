import os
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)
try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
except Exception as e:
    print(f"API Key 설정 중 에러 발생: {e}")

# '/api/ask' Post 엔드 포인트
@app.route("/api/ask", methods=["POST"])
def ask_gemini():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    question = data.get("question")

    # 'persona' 값을 요청 본문에서 선택적으로 가져올 수 있도록 추가
    persona = data.get("persona", "당신은 웨이브형 디펜스 게임에 등장하는 변덕이 심한 보스야.") # 기본 페르소나 설정

    if not question:
        return jsonify({"error": "Missing 'question' in request body"}), 400

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')

        # 성격 프롬프트
        full_question = f"{persona}\n\n사용자 질문: {question}"
        
        response = model.generate_content(full_question)
        return jsonify({"answer": response.text})

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "Failed to get response from AI"}), 500

# 테스트용 내장 서버
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
