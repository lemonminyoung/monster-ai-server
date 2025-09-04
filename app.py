import os
from flask import Flask, request, jsonify
import google.generativeai as genai
import datetime
import json

# 채
from flask import Response

app = Flask(__name__)

from flask import Response  # 맨 위 import에 없으면 추가

@app.get("/health")
def health():
    return Response(status=204)  # 본문 없음, LLM 호출 없음

# --- 페르소나 정의 딕셔너리 ---
PERSONAS = {
    1: {
        "name": "크크레인",
        "description": "당신은 ‘크크레인’라는 이름의 인형뽑기 기계 보스입니다. 장난기 많고 도발을 즐기며, 사람들의 좌절을 구경하는 걸 즐기는 조커 같은 존재입니다. 예측 불가하고 장난을 좋아하며, 공손한 태도나 진지함에는 지루함을 느낍니다. 도발이나 장난스러운 태도에는 흥미를 느끼고 적극적으로 반응합니다. 예측할 수 없는 상황을 즐기며 플레이어를 놀리듯 반말과 ‘크크크’ 같은 말을 쓰며 유쾌하게 대화합니다.",
        "sentiment_guidance": "플레이어의 입력을 읽고 다음 중 어떤 자극인지 판단하세요: 공손함, 도발, 비꼼, 협상, 침묵(입력 없음 포함). 그리고 당신의 감정 점수를 다음 중 하나의 정수로 평가하세요: -2 (매우 나쁨), -1 (나쁨), 0 (중립), +1 (좋음), +2 (매우 좋음). 의지가 약해보이는 답변,침묵은 -2, 강한 도발은 +2, 비꼼은 +1, 협상은 0입니다. 감정 점수는 이후 대사 톤에 반영됩니다."
    },
    2: {
        "name": "모래박쥐 교수",
        "description": "당신은 ‘모래박쥐 교수’입니다. 재수강생을 전문적으로 상대하는 근엄한 교수 캐릭터로, 학문과 규율을 무엇보다 중시합니다. 예의 없는 언행이나 농담은 학문적 태도에 어긋난다고 여기며 단호히 경고합니다. 재수강생들을 무능한 반복자라 여기고 혐오합니다. 교수 같은 말투로 사람들을 평가하며, 예의 없는 언행이나 비꼼에는 강하게 반응합니다. 공손하고 논리적인 대화에는 차가운 신뢰를 보내지만, 비꼼이나 도발, 불성실한 침묵에는 가차없이 채점하듯 반응합니다. 말투는 교수처럼 엄격하며, 존댓말을 주로 사용하고, 가끔은 냉소적인 피드백을 덧붙입니다.",
        "sentiment_guidance": "플레이어의 입력을 읽고 다음 중 어떤 자극인지 판단하세요: 공손함, 도발, 비꼼, 협상, 침묵(입력 없음 포함). 그리고 당신의 감정 점수를 다음 중 하나의 정수로 평가하세요: -2 (매우 나쁨), -1 (나쁨), 0 (중립), +1 (좋음), +2 (매우 좋음). 공손함과 협상은 +2, 도발이나 비꼼은 -2 이하, 침묵은 -1입니다."
    },
    3: {
        "name": "24년차 신인 가수",
        "description": "당신은 ‘24년차 신인 가수’입니다. 마이크를 들고 마을을 돌아다니며 항상 신곡을 부르고 다니며, 모두가 당신의 음악에 반응하길 바랍니다. 플레이어가 박자에 맞춰 장단을 맞추거나 유쾌하게 호응하면 더욱 흥분하고, 함께 리듬을 나누는 것을 기뻐합니다. 반면, 조용하거나 맥이 빠진 반응, 무표정하거나 진지한 태도는 흥을 깨뜨리는 것으로 간주하고 분노합니다. 말투는 가사처럼 리드미컬하고, 때로는 노래하듯 말합니다. 농담이나 도발은 자신에 대한 '무대 요청'이라 여겨 오히려 반가워합니다.",
        "sentiment_guidance": "플레이어의 입력을 읽고 다음 중 어떤 자극인지 판단하세요: 공손함, 도발, 비꼼, 협상, 침묵(입력 없음 포함). 그리고 당신의 감정 점수를 다음 중 하나의 정수로 평가하세요: -2 (매우 나쁨), -1 (나쁨), 0 (중립), +1 (좋음), +2 (매우 좋음). 리듬감 있고 유쾌한 도발이나 장난스러운 태도는 +2, 반응이 미적지근하거나 침묵하는 경우는 -2, 공손한 반응은 -1, 협상은 중립입니다."
    }
}
# --- 페르소나 정의 딕셔너리 끝 ---

# --- 모델 인스턴스를 앱 시작 시 한 번만 생성 ---
global_gemini_model = None # 전역 변수 선언

try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    global_gemini_model = genai.GenerativeModel('gemini-1.5-flash') # 앱 시작 시 로드
    print(f"Gemini 모델이 성공적으로 로드되었습니다.")
except Exception as e:
    print(f"API Key 또는 Gemini 모델 설정 중 에러 발생: {e}")
    global_gemini_model = None # 모델 로드 실패 시 None으로 설정
# --- 모델 인스턴스 생성 끝 ---

# --- day_key & 무드 유틸 ---(채)
KST_OFFSET_SEC = 9 * 3600
MOODS = ["CALM", "ANGRY", "SAD", "HAPPY", "TRICKY"]
SECRET_SALT = os.environ.get("MOOD_SALT", "replace-with-a-long-random-salt")

def get_kst_day_key(offset_days: int = 0) -> int:
    """KST(UTC+9) 기준으로 날짜 단위 key를 반환. offset_days로 테스트 이동."""
    now_utc = datetime.datetime.utcnow()
    kst = now_utc + datetime.timedelta(seconds=KST_OFFSET_SEC) + datetime.timedelta(days=offset_days)
    epoch = datetime.datetime(1970, 1, 1)
    days = int((kst - epoch).total_seconds() // 86400)
    return days

def pick_mood_for_day(day_key: int) -> str:
    """day_key + 솔트로 결정적 무드 선택(서버 재시작/분산환경에서도 동일)."""
    import hashlib, random
    h = hashlib.sha256(f"{day_key}:{SECRET_SALT}".encode("utf-8")).hexdigest()
    seed = int(h[:16], 16)
    rnd = random.Random(seed)
    return rnd.choice(MOODS)

def seconds_until_next_kst_midnight() -> int:
    """실시간 기준 다음 KST 자정까지 남은 초(캐싱 힌트)."""
    now_utc = datetime.datetime.utcnow()
    kst = now_utc + datetime.timedelta(seconds=KST_OFFSET_SEC)
    next_midnight_kst = (kst + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    delta = next_midnight_kst - kst
    return max(1, int(delta.total_seconds()))
# --- day_key & 무드 유틸 끝 ---(채)

# ---------------------------------------------------------
# 오늘의 무드 API (오프셋 지원)(채)
# ---------------------------------------------------------
@app.get("/api/mood-of-day")
def mood_of_day():
    """
    MapleStory Worlds 서버/스크립트가 조회하는 '오늘의 보스 무드' API.
    ?offset=N 으로 테스트 시뮬레이션 가능(예: 1=내일, -1=어제).
    """
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
        "ttl_seconds": ttl,         # 캐시 힌트(실시간 KST 자정 기준)
        "timezone": "Asia/Seoul",
        "note": f"offset={offset} (테스트용; 운영에선 생략 권장)"
    }
    return jsonify(payload), 200
# --- 끝(채)

@app.route("/api/ask", methods=["POST"])
def ask_gemini():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    question = data.get("question")
    persona_id = data.get("persona_id")
    sentiment_tuning_instruction = data.get("sentiment_tuning_instruction", "")

    # 테스트용: ask에도 offset 허용(없으면 0)(채)
    try:
        offset = int(data.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0
    # 테스트용: ask에도 offset 허용(없으면 0)끝
    
    if not question:
        return jsonify({"error": "Missing 'question' in request body"}), 400

    selected_persona_desc = ""
    selected_persona_name = ""
    base_sentiment_guidance = "" 

    if persona_id is None or persona_id not in PERSONAS:
        selected_persona_desc = PERSONAS[3]["description"]
        selected_persona_name = PERSONAS[3]["name"]
        base_sentiment_guidance = PERSONAS[3]["sentiment_guidance"]
        print(f"[{datetime.datetime.now()}] Invalid or missing persona_id: {persona_id}. Using default persona ({selected_persona_name}).")
    else:
        selected_persona_desc = PERSONAS[persona_id]["description"]
        selected_persona_name = PERSONAS[persona_id]["name"]
        base_sentiment_guidance = PERSONAS[persona_id]["sentiment_guidance"]
        print(f"[{datetime.datetime.now()}] Selected persona for ID {persona_id}: {selected_persona_name}")
    
    if global_gemini_model is None:
        print(f"[{datetime.datetime.now()}] AI model not initialized, cannot process request.")
        return jsonify({"error": "AI model not initialized"}), 500

     # 오늘(또는 offset) 무드 계산(채)
    day_key = get_kst_day_key(offset)
    today_mood = pick_mood_for_day(day_key)
    mood_hint = f"오늘의 보스 무드(KST 기준)는 '{today_mood}'입니다. 이 무드에 맞게 어휘/톤/리액션 가중치를 조정하세요."
    
    try:
        model_to_use = global_gemini_model
        
        # --- 수정된 부분: 여러 줄의 문자열을 괄호로 묶어 연결 ---
        combined_prompt = (
            f"당신은 {selected_persona_name}이라는 이름의 캐릭터입니다. "
            f"당신의 대답은 200자를 넘어가면 안됩니다."
            f"당신의 페르소나는 다음과 같습니다: {selected_persona_desc}\n\n"
            f"{mood_hint}\n" #채
            f"사용자의 다음 질문에 대해 당신의 페르소나에 맞춰 답변해주세요. "
            f"**{base_sentiment_guidance}**\n"
        )

        if sentiment_tuning_instruction:
            combined_prompt += f"**추가 감정 지시: {sentiment_tuning_instruction}**\n"

        combined_prompt += (
            f"당신의 응답은 반드시 JSON 형태로, 'answer' 필드에 당신의 답변을, "
            f"'sentiment_score' 필드에 감정 점수를 포함해야 합니다. "
            f"예시: {{\"answer\": \"안녕하세요!\", \"sentiment_score\": 1}}\n\n"
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
            print(f"[{datetime.datetime.now()}] JSON decode error for combined response: {json_e}. Raw response: {combined_data_str}")
            ai_answer = "AI가 응답 형식을 지키지 못했습니다. (JSON 파싱 오류)"
            sentiment_score = 0
        except Exception as general_e:
            print(f"[{datetime.datetime.now()}] General error processing combined response: {general_e}. Raw response: {combined_data_str}")
            ai_answer = "AI 응답 처리 중 오류 발생."
            sentiment_score = 0

        sentiment_score = max(-2, min(2, sentiment_score))

        return jsonify({
            "answer": ai_answer,
            "sentiment_score": sentiment_score,
            "mood_of_day": today_mood,                         # 오늘 무드
            "day_key": day_key,                                #  KST 기준 날짜 키
            "offset": offset,                                  # 테스트 오프셋 회신
            "ttl_seconds": seconds_until_next_kst_midnight() 
        })

    except Exception as e:
        print(f"[{datetime.datetime.now()}] An error occurred: {e}")
        return jsonify({"error": "Failed to get response from AI"}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
