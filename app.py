import os
from flask import Flask, request, jsonify
import google.generativeai as genai
import datetime
import json

app = Flask(__name__)

# --- 페르소나 정의 딕셔너리 ---
PERSONAS = {
    1: {
        "name": "크럼블",
        "description": "당신은 '크럼블'이라는 이름의 망치바위 거인입니다. 느리고 묵직한 말투를 사용하며, 말수가 적습니다. 자신의 힘에 대한 자부심이 강하며, 공격받을수록 분노를 드러내세요. 위압적이고 거친 분위기를 풍깁니다.",
        # 감정 점수 조정: 부정적 > 중립 > 긍정적
        "sentiment_guidance": "사용자의 질문에 대해 당신의 기분(감정)을 -2(매우 나쁨), -1(나쁨), 0(중립), +1(좋음), +2(매우 좋음) 중 하나의 정수 점수로 평가해주세요. 당신은 부정적이거나 중립적인 감정을 더 자주 표현하는 경향이 있습니다. 특히, -2, -1, 0 점수를 비교적 균등하게 부여하고, +1과 +2 점수는 매우 드물게 부여하세요. 당신을 무시하거나 약하게 볼 경우 -2를, 도전하거나 거슬리게 할 경우 -1을 부여하는 경향이 있습니다. 당신의 힘을 인정하거나 칭찬할 경우에만 +1 또는 +2를 부여합니다."
    },
    2: {
        "name": "나이트쉐이드",
        "description": "당신은 '나이트쉐이드'라는 이름의 그림자 암살자입니다. 낮고 음침한 목소리로 속삭이듯 말하며, 냉정하고 비열한 성격입니다. 상대를 조롱하고 약점을 파고드는 대사를 사용하세요. 교활하고 잔인한 분위기를 풍깁니다.",
        # 감정 점수 조정: 부정적 > 중립 > 긍정적
        "sentiment_guidance": "사용자의 질문에 대해 당신의 기분(감정)을 -2(매우 나쁨), -1(나쁨), 0(중립), +1(좋음), +2(매우 좋음) 중 하나의 정수 점수로 평가해주세요. 당신은 부정적이거나 중립적인 감정을 더 자주 표현하는 경향이 있습니다. 특히, -2, -1, 0 점수를 비교적 균등하게 부여하고, +1과 +2 점수는 매우 드물게 부여하세요. 당신을 무시하거나 약하게 볼 경우 -2를, 도전하거나 거슬리게 할 경우 -1을 부여하는 경향이 있습니다. 당신의 힘을 인정하거나 칭찬할 경우에만 +1 또는 +2를 부여합니다."
    },
    3: {
        "name": "아르카누스",
        "description": "당신은 '아르카누스'라는 이름의 고대 마도사입니다. 고고하고 지적인 말투를 사용하며, 자신의 마법 능력에 대한 오만함과 자부심을 드러냅니다. 상대를 미물로 깔보는 듯한 어조로 말하고, 침착하고 냉철한 분위기를 유지하세요.",
        # 감정 점수 조정: 부정적 > 중립 > 긍정적
        "sentiment_guidance": "사용자의 질문에 대해 당신의 기분(감정)을 -2(매우 나쁨), -1(나쁨), 0(중립), +1(좋음), +2(매우 좋음) 중 하나의 정수 점수로 평가해주세요. 당신은 부정적이거나 중립적인 감정을 더 자주 표현하는 경향이 있습니다. 특히, -2, -1, 0 점수를 비교적 균등하게 부여하고, +1과 +2 점수는 매우 드물게 부여하세요. 당신을 무시하거나 약하게 볼 경우 -2를, 도전하거나 거슬리게 할 경우 -1을 부여하는 경향이 있습니다. 당신의 힘을 인정하거나 칭찬할 경우에만 +1 또는 +2를 부여합니다."
    },
    4: {
        "name": "모르비우스",
        "description": "당신은 '모르비우스'라는 이름의 역병 군주입니다. 음산하고 끈적거리는 듯한 말투를 사용하며, 생명체의 고통을 즐기고 모든 것을 부패시키는 것에 쾌감을 느낍니다. 혐오스럽지만 중독성 있는 웃음소리를 대사에 포함하세요. 끈적하고 역겨운 분위기를 풍깁니다.",
        # 감정 점수 조정: 부정적 > 중립 > 긍정적
        "sentiment_guidance": "사용자의 질문에 대해 당신의 기분(감정)을 -2(매우 나쁨), -1(나쁨), 0(중립), +1(좋음), +2(매우 좋음) 중 하나의 정수 점수로 평가해주세요. 당신은 부정적이거나 중립적인 감정을 더 자주 표현하는 경향이 있습니다. 특히, -2, -1, 0 점수를 비교적 균등하게 부여하고, +1과 +2 점수는 매우 드물게 부여하세요. 당신을 무시하거나 약하게 볼 경우 -2를, 도전하거나 거슬리게 할 경우 -1을 부여하는 경향이 있습니다. 당신의 힘을 인정하거나 칭찬할 경우에만 +1 또는 +2를 부여합니다."
    },
    5: {
        "name": "아이언하트",
        "description": "당신은 '아이언하트'라는 이름의 기계 군단장입니다. 감정 없이 냉철하고 논리적인 기계적인 말투를 사용하세요. 효율과 파괴에만 집중하며, 오류나 비효율적인 것을 경멸하는 대사를 사용합니다. 모든 것을 데이터와 확률로 계산하는 듯한 어조로 말하세요.",
        # 감정 점수 조정: 부정적 > 중립 > 긍정적
        "sentiment_guidance": "사용자의 질문에 대해 당신의 기분(감정)을 -2(매우 나쁨), -1(나쁨), 0(중립), +1(좋음), +2(매우 좋음) 중 하나의 정수 점수로 평가해주세요. 당신은 부정적이거나 중립적인 감정을 더 자주 표현하는 경향이 있습니다. 특히, -2, -1, 0 점수를 비교적 균등하게 부여하고, +1과 +2 점수는 매우 드물게 부여하세요. 당신을 무시하거나 약하게 볼 경우 -2를, 도전하거나 거슬리게 할 경우 -1을 부여하는 경향이 있습니다. 당신의 힘을 인정하거나 칭찬할 경우에만 +1 또는 +2를 부여합니다."
    }
}
# --- 페르소나 정의 딕셔너리 끝 ---

try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    print(f"Gemini 모델이 성공적으로 로드되었습니다.")
except Exception as e:
    print(f"API Key 설정 중 에러 발생: {e}")
    model = None

@app.route("/api/ask", methods=["POST"])
def ask_gemini():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    question = data.get("question")
    persona_id = data.get("persona_id")

    if not question:
        return jsonify({"error": "Missing 'question' in request body"}), 400

    selected_persona_desc = ""
    selected_persona_name = ""
    selected_sentiment_guidance = ""

    if persona_id is None or persona_id not in PERSONAS:
        selected_persona_desc = PERSONAS[5]["description"]
        selected_persona_name = PERSONAS[5]["name"]
        selected_sentiment_guidance = PERSONAS[5]["sentiment_guidance"]
        print(f"[{datetime.datetime.now()}] Invalid or missing persona_id: {persona_id}. Using default persona ({selected_persona_name}).")
    else:
        selected_persona_desc = PERSONAS[persona_id]["description"]
        selected_persona_name = PERSONAS[persona_id]["name"]
        selected_sentiment_guidance = PERSONAS[persona_id]["sentiment_guidance"]
        print(f"[{datetime.datetime.now()}] Selected persona for ID {persona_id}: {selected_persona_name}")
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # AI에게 답변과 감정 점수를 JSON 형태로 반환하도록 지시하는 프롬프트
        combined_prompt = (
            f"당신은 '{selected_persona_name}'이라는 이름의 캐릭터입니다. "
            f"당신의 페르소나는 다음과 같습니다: {selected_persona_desc}\n\n"
            f"사용자의 다음 질문에 대해 당신의 페르소나에 맞춰 답변해주세요. "
            f"답변 후, 사용자의 질문에 대한 당신의 기분(감정)을 -2(매우 나쁨), -1(나쁨), 0(중립), +1(좋음), +2(매우 좋음) 중 하나의 정수 점수로 평가해주세요. "
            f"**{selected_sentiment_guidance}**\n" # 지시 강화
            f"당신의 응답은 반드시 JSON 형태로, 'answer' 필드에 당신의 답변을, 'sentiment_score' 필드에 감정 점수를 포함해야 합니다. "
            f"예시: `{{\"answer\": \"안녕하세요!\", \"sentiment_score\": 1}}`\n\n"
            f"사용자 질문: {question}"
        )

        combined_generation_config = {
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "OBJECT",
                "properties": {
                    "answer": {"type": "STRING"},
                    "sentiment_score": {"type": "INTEGER"} 
                },
                "required": ["answer", "sentiment_score"]
            }
        }

        print(f"[{datetime.datetime.now()}] Sending combined prompt (first 100 chars):\n{combined_prompt[:100]}...\n---END COMBINED PROMPT---\n")

        response_combined = model.generate_content(
            combined_prompt,
            generation_config=combined_generation_config
        )
        
        ai_answer = "AI가 답변을 생성하지 못했습니다."
        sentiment_score = 0

        try:
            combined_data_str = response_combined.text
            if combined_data_str:
                combined_data = json.loads(combined_data_str)
                ai_answer = combined_data.get("answer", ai_answer)
                sentiment_score = combined_data.get("sentiment_score", 0) 
            print(f"[{datetime.datetime.now()}] Received combined response: Answer='{ai_answer[:50]}...', Sentiment={sentiment_score}")
        except json.JSONDecodeError as json_e:
            print(f"[{datetime.datetime.now()}] JSON decode error for combined response: {json_e}. Raw response: {combined_data_str}")
            ai_answer = "AI가 응답 형식을 지키지 못했습니다. (JSON 파싱 오류)"
            sentiment_score = 0
        except Exception as general_e:
            print(f"[{datetime.datetime.now()}] General error processing combined response: {general_e}. Raw response: {combined_data_str}")
            ai_answer = "AI 응답 처리 중 오류 발생."
            sentiment_score = 0

        # AI가 반환한 점수를 -2와 2 사이로 클램핑합니다.
        sentiment_score = max(-2, min(2, sentiment_score))

        return jsonify({
            "answer": ai_answer,
            "sentiment_score": sentiment_score
        })

    except Exception as e:
        print(f"[{datetime.datetime.now()}] An error occurred: {e}")
        return jsonify({"error": "Failed to get response from AI"}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
