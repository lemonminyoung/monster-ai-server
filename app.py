import os
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# --- 페르소나 정의 딕셔너리 ---
# 클라이언트로부터 받을 번호(ID)에 따라 다른 페르소나를 매핑합니다.
# 여기에 원하는 보스 캐릭터의 페르소나를 추가하거나 수정할 수 있습니다.
PERSONAS = {
    1: {
        "name": "크럼블",
        "description": "당신은 '크럼블'이라는 이름의 망치바위 거인입니다. 느리고 묵직한 말투를 사용하며, 말수가 적습니다. 자신의 힘에 대한 자부심이 강하며, 공격받을수록 분노를 드러내세요. 위압적이고 거친 분위기를 풍깁니다."
    },
    2: {
        "name": "나이트쉐이드",
        "description": "당신은 '나이트쉐이드'라는 이름의 그림자 암살자입니다. 낮고 음침한 목소리로 속삭이듯 말하며, 냉정하고 비열한 성격입니다. 상대를 조롱하고 약점을 파고드는 대사를 사용하세요. 교활하고 잔인한 분위기를 풍깁니다."
    },
    3: {
        "name": "아르카누스",
        "description": "당신은 '아르카누스'라는 이름의 고대 마도사입니다. 고고하고 지적인 말투를 사용하며, 자신의 마법 능력에 대한 오만함과 자부심을 드러냅니다. 상대를 미물로 깔보는 듯한 어조로 말하고, 침착하고 냉철한 분위기를 유지하세요."
    },
    4: {
        "name": "모르비우스",
        "description": "당신은 '모르비우스'라는 이름의 역병 군주입니다. 음산하고 끈적거리는 듯한 말투를 사용하며, 생명체의 고통을 즐기고 모든 것을 부패시키는 것에 쾌감을 느낍니다. 혐오스럽지만 중독성 있는 웃음소리를 대사에 포함하세요. 끈적하고 역겨운 분위기를 풍깁니다."
    },
    5: {
        "name": "아이언하트",
        "description": "당신은 '아이언하트'라는 이름의 기계 군단장입니다. 감정 없이 냉철하고 논리적인 기계적인 말투를 사용하세요. 효율과 파괴에만 집중하며, 오류나 비효율적인 것을 경멸하는 대사를 사용합니다. 모든 것을 데이터와 확률로 계산하는 듯한 어조로 말하세요."
    }
}
try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    #global_gemini_model = genai.GenerativeModel('gemini-1.5-flash')
    print(f"Gemini 모델이 성공적으로 로드되었습니다.")
except Exception as e:
    print(f"API Key 설정 중 에러 발생: {e}")
    #global_gemini_model = None # 모델 로드 실패 시 None으로 설정
    model= None

# '/api/ask' Post 엔드 포인트
@app.route("/api/ask", methods=["POST"])
def ask_gemini():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    question = data.get("question")
    persona_id = data.get("persona_id") # 클라이언트로부터 받을 페르소나 ID

    #'persona' 값을 요청 본문에서 선택적으로 가져올 수 있도록 추가
    #persona = data.get("persona", "당신은 '아이언하트'라는 이름의 기계 군단장입니다. 감정 없이 냉철하고 논리적인 기계적인 말투를 사용하세요. 효율과 파괴에만 집중하며, 오류나 비효율적인 것을 경멸하는 대사를 사용합니다. 모든 것을 데이터와 확률로 계산하는 듯한 어조로 말하세요.") # 기본 페르소나 설정
    #persona = data.get("persona", "당신은 '크럼블'이라는 이름의 망치바위 거인입니다. 느리고 묵직한 말투를 사용하며, 말수가 적습니다. 자신의 힘에 대한 자부심이 강하며, 공격받을수록 분노를 드러내세요. 위압적이고 거친 분위기를 풍깁니다.") # 기본 페르소나 설정
    if not question:
        return jsonify({"error": "Missing 'question' in request body"}), 400

    # persona_id를 사용하여 해당 페르소나 설명을 가져옵니다.
    # persona_id가 없거나 유효하지 않으면 기본 페르소나를 사용하거나 에러를 반환할 수 있습니다.
    if persona_id is None or persona_id not in PERSONAS:
        # 유효하지 않은 persona_id일 경우 기본 페르소나 (예: 아이언하트)를 사용하거나
        # 에러를 반환하도록 선택할 수 있습니다. 여기서는 기본 페르소나를 사용합니다.
        selected_persona = PERSONAS[4]["description"] # 기본값으로 아이언하트 페르소나 사용
        print(f"[{datetime.datetime.now()}] Invalid or missing persona_id: {persona_id}. Using default persona.")
    else:
        selected_persona = PERSONAS[persona_id]["description"]
        print(f"[{datetime.datetime.now()}] Selected persona for ID {persona_id}: {PERSONAS[persona_id]['name']}")
        
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        # 성격 프롬프트
        full_question = f"{selected_persona}\n\n사용자 질문: {question}"

        print(f"[{datetime.datetime.now()}] Sending question with persona (first 50 chars): {selected_persona[:50]}...")
        print(f"[{datetime.datetime.now()}] Actual Full Question Sent (first 100 chars):\n{full_question[:100]}...\n---END FULL QUESTION---\n")
        
        response = model.generate_content(full_question)
        print(f"[{datetime.datetime.now()}] Received response (first 50 chars): {response.text[:50]}...")
        return jsonify({"answer": response.text})

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "Failed to get response from AI"}), 500

# 테스트용 내장 서버
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
