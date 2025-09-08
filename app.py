import os
from flask import Flask, request, jsonify
import google.generativeai as genai
import datetime
import json
from flask import Response

app = Flask(__name__)

# --- [수정됨] 페르소나 및 감정 지침 요약 ---
PERSONAS = {
    1: {
        "name": "크크레인",
        "description": "너는 인형뽑기 기계 보스 '크크레인'. 장난과 도발을 즐기는 조커 스타일. 예측불가하며, 진지한 건 싫어함. 반말과 '크크크'를 사용하며 플레이어를 놀리는 말투.",
        "sentiment_guidance": "강한 도발 +2, 비꼼 +1, 협상 0, 의지 약함/침묵 -2."
    },
    2: {
        "name": "모래박쥐 교수",
        "description": "너는 '모래박쥐 교수'. 재수강생을 다루는 근엄한 교수. 학문과 규율을 중시하며 예의 없는 행동에 엄격함. 교수처럼 존댓말과 냉소적인 피드백을 사용.",
        "sentiment_guidance": "공손함/협상 +2, 침묵 -1, 도발/비꼼 -2."
    },
    3: {
        "name": "24년차 신인 가수",
        "description": "너는 '24년차 신인 가수'. 모두가 네 노래에 반응하길 바람. 리듬감 있는 호응에 기뻐하고, 조용한 반응에 분노함. 말투는 노래 가사처럼 리드미컬함.",
        "sentiment_guidance": "리드미컬/유쾌한 도발 +2, 협상 0, 공손함 -1, 무반응/침묵 -2."
    }
}
# --- 페르소나 정의 딕셔너리 끝 ---

# --- 모델 인스턴스를 앱 시작 시 한 번만 생성 ---
global_gemini_model = None 

try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    global_gemini_model = genai.GenerativeModel('gemini-1.5-flash') 
    print(f"Gemini 모델이 성공적으로 로드되었습니다.")
except Exception as e:
    print(f"API Key 또는 Gemini 모델 설정 중 에러 발생: {e}")
    global_gemini_model = None 
# --- 모델 인스턴스 생성 끝 ---

# --- day_key & 무드 유틸 ---
KST_OFFSET_SEC = 9 * 3600
MOODS = ["CALM", "ANGRY", "SAD", "HAPPY", "TRICKY"]
SECRET_SALT = os.environ.get("MOOD_SALT", "replace-with-a-long-random-salt")

def get_kst_day_key(offset_days: int = 0) -> int:
    now_utc = datetime.datetime.utcnow()
    kst = now_utc + datetime.timedelta(seconds=KST_OFFSET_SEC) + datetime.timedelta(days=offset_days)
    epoch = datetime.datetime(1970, 1, 1)
    days = int((kst - epoch).total_seconds() // 86400)
    return days

def pick_mood_for_day(day_key: int) -> str:
    import hashlib, random
    h = hashlib.sha256(f"{day_key}:{SECRET_SALT}".encode("utf-8")).hexdigest()
    seed = int(h[:16], 16)
    rnd = random.Random(seed)
    return rnd.choice(MOODS)

def seconds_until_next_kst_midnight() -> int:
    now_utc = datetime.datetime.utcnow()
    kst = now_utc + datetime.timedelta(seconds=KST_OFFSET_SEC)
    next_midnight_kst = (kst + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    delta = next_midnight_kst - kst
    return max(1, int(delta.total_seconds()))
# --- day_key & 무드 유틸 끝 ---

@app.get("/health")
def health():
    return Response(status=204)

@app.get("/api/mood-of-day")
def mood_of_day():
    try:
        offset = int(request.args.get("offset", 0))
    except ValueError:
        offset = 0

    day_key = get_kst_day_key(offset)
    mood = pick_mood_for_day(day_key)
    ttl = seconds_until_next_kst_midnight()
    payload = {
        "day_key": day_key,
        "mood": mood,
        "ttl_seconds": ttl,
        "timezone": "Asia/Seoul",
        "note": f"offset={offset} (테스트용; 운영에선 생략 권장)"
    }
    return jsonify(payload), 200

@app.route("/api/ask", methods=["POST"])
def ask_gemini():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    question = data.get("question") 
    persona_id = data.get("persona_id")
    sentiment_tuning_instruction = data.get("sentiment_tuning_instruction", "")

    try:
        offset = int(data.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0
    
    if not question:
        return jsonify({"error": "Missing 'question' in request body"}), 400

    persona = PERSONAS.get(persona_id, PERSONAS[3])
    selected_persona_desc = persona["description"]
    selected_persona_name = persona["name"]
    base_sentiment_guidance = persona["sentiment_guidance"]
    
    if persona_id not in PERSONAS:
        print(f"[{datetime.datetime.now()}] Invalid or missing persona_id: {persona_id}. Using default persona ({selected_persona_name}).")
    else:
        print(f"[{datetime.datetime.now()}] Selected persona for ID {persona_id}: {selected_persona_name}")
    
    if global_gemini_model is None:
        print(f"[{datetime.datetime.now()}] AI model not initialized, cannot process request.")
        return jsonify({"error": "AI model not initialized"}), 500

    day_key = get_kst_day_key(offset)
    today_mood = pick_mood_for_day(day_key)
    mood_hint = f"오늘 KST 기준 무드는 '{today_mood}'임. 이 무드를 톤/리액션에 반영."
    
    try:
        model_to_use = global_gemini_model
        
        # --- [수정됨] 프롬프트 압축 및 간결화 ---
        combined_prompt = (
            f"너는 '{selected_persona_name}' 캐릭터다. 페르소나: {selected_persona_desc}\n"
            f"{mood_hint}\n"
            f"**지시:**\n"
            f"- 입력은 '/'로 구분된 여러 사용자 발언임.\n"
            f"- 각 발언에 순서대로 답변 후, 다시 '/'로 합쳐 'answer' 필드에 단일 문자열로 응답.\n"
            f"- 입력 발언 수와 출력 답변 수는 반드시 일치해야 함.\n"
            f"- 모든 발언을 종합해 'sentiment_score'를 정수로 평가. 기준: {base_sentiment_guidance}\n"
            f"- 각 답변은 50자 이내로 간결하게.\n"
        )

        if sentiment_tuning_instruction:
            combined_prompt += f"- 추가 감정 지시: {sentiment_tuning_instruction}\n"

        combined_prompt += (
            f"**출력 형식 (JSON):** {{\"answer\": \"답변1/답변2\", \"sentiment_score\": 점수}}\n"
            f"**사용자 발언:** {question}"
        )

        combined_generation_config = {
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "OBJECT",
                "properties": { "answer": {"type": "STRING"}, "sentiment_score": {"type": "INTEGER"} },
                "required": ["answer", "sentiment_score"]
            }
        }

        print(f"[{datetime.datetime.now()}] Sending optimized prompt (first 150 chars):\n{combined_prompt[:150]}...\n---END OPTIMIZED PROMPT---\n")

        response_combined = model_to_use.generate_content(
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
            print(f"[{datetime.datetime.now()}] JSON decode error: {json_e}. Raw response: {combined_data_str}")
            ai_answer = "AI 응답 형식 오류 (JSON 파싱 실패)"
            sentiment_score = 0
        except Exception as general_e:
            print(f"[{datetime.datetime.now()}] General error processing response: {general_e}. Raw response: {response_combined.text if 'response_combined' in locals() else 'N/A'}")
            ai_answer = "AI 응답 처리 중 오류 발생."
            sentiment_score = 0

        sentiment_score = max(-2, min(2, sentiment_score))

        return jsonify({
            "answer": ai_answer,
            "sentiment_score": sentiment_score,
            "mood_of_day": today_mood,
            "day_key": day_key,
            "offset": offset,
            "ttl_seconds": seconds_until_next_kst_midnight()
        })

    except Exception as e:
        print(f"[{datetime.datetime.now()}] An error occurred: {e}")
        return jsonify({"error": "Failed to get response from AI"}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
