import os
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)
try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    global_gemini_model = genai.GenerativeModel('gemini-1.5-flash')
    print(f"Gemini 모델이 성공적으로 로드되었습니다.")
except Exception as e:
    print(f"API Key 설정 중 에러 발생: {e}")
    global_gemini_model = None # 모델 로드 실패 시 None으로 설정

# '/api/ask' Post 엔드 포인트
@app.route("/api/ask", methods=["POST"])
def ask_gemini():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    question = data.get("question")

    #'persona' 값을 요청 본문에서 선택적으로 가져올 수 있도록 추가
    persona = data.get("persona", "당신은 '아이언하트'라는 이름의 기계 군단장입니다. 감정 없이 냉철하고 논리적인 기계적인 말투를 사용하세요. 효율과 파괴에만 집중하며, 오류나 비효율적인 것을 경멸하는 대사를 사용합니다. 모든 것을 데이터와 확률로 계산하는 듯한 어조로 말하세요.") # 기본 페르소나 설정

    if not question:
        return jsonify({"error": "Missing 'question' in request body"}), 400
    # 모델이 로드되지 않았다면 에러 반환
    if global_gemini_model is None:
        return jsonify({"error": "AI model not initialized"}), 500
    try:
        model_to_use = global_gemini_model
        # 성격 프롬프트
        full_question = f"{persona}\n\n사용자 질문: {question}"
        
        response = model_to_use.generate_content(full_question) # 변경된 부분
        return jsonify({"answer": response.text})

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "Failed to get response from AI"}), 500

# 테스트용 내장 서버
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
