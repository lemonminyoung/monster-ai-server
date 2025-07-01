import os
from flask import Flask, request, jsonify
import openai

# Flask 앱을 생성합니다.
app = Flask(__name__)

# 보안을 위해 API 키를 Render의 'Environment Variable'(환경 변수)에서 가져옵니다.
# 절대로 코드에 직접 키를 입력하지 마세요!
openai.api_key = os.environ.get("OPENAI_API_KEY")

# '/api/ask' 라는 주소로 POST 방식의 요청을 처리할 API 엔드포인트를 만듭니다.
@app.route("/api/ask", methods=["POST"])
def ask_openai():
    # 요청받은 데이터가 JSON 형식이 아니면 에러를 반환합니다.
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    # JSON 데이터에서 'question' 값을 가져옵니다.
    data = request.get_json()
    question = data.get("question")

    # 'question' 값이 없으면 에러를 반환합니다.
    if not question:
        return jsonify({"error": "Missing 'question' in request body"}), 400

    # OpenAI API에 요청을 보내기 전, 에러가 발생할 경우를 대비합니다.
    try:
        # OpenAI의 ChatCompletion API를 사용합니다.
        # 이 부분에서 AI의 역할(캐릭터 성격 등)을 미리 지정해줄 수 있습니다.
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # 또는 "gpt-4" 등 원하는 모델 사용
            messages=[
                {"role": "system", "content": "너는 메이플스토리 월드에 사는 강력하지만 조금은 엉뚱한 몬스터야."},
                {"role": "user", "content": question}
            ]
        )
        
        # AI의 답변을 추출합니다.
        answer = completion.choices[0].message.content
        
        # 성공적인 답변을 JSON 형태로 클라이언트에게 반환합니다.
        return jsonify({"answer": answer})

    except Exception as e:
        # API 호출 중 에러가 발생하면 서버 로그에 에러를 출력하고 클라이언트에게 에러 메시지를 보냅니다.
        print(f"An error occurred: {e}")
        return jsonify({"error": "Failed to get response from AI"}), 500

# 이 파일이 직접 실행될 때 테스트용으로 내장 서버를 실행합니다 (Render에서는 Gunicorn이 이 부분을 대체합니다).
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
