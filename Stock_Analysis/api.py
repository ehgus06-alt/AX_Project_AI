from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import json
import os

app = FastAPI(
    title="Samsung Stock AI API",
    description="삼성전자 주식 5차원 AI 분석 결과를 제공하는 FAST API 서버입니다.",
    version="1.0.0"
)

# CORS 설정 (프론트엔드 연동을 위함)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 모든 도메인 허용 (실서버 배포 시 특정 도메인으로 제한 권장)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Samsung Stock AI API 서버가 정상적으로 실행 중입니다. /api/analyze 엔드포인트를 호출하세요."}

@app.get("/api/analyze")
def get_analysis_result():
    """
    AI 분석 파이프라인(main.py)을 실행하고 JSON 결과값을 반환합니다.
    """
    json_path = "analysis_result.json"
    
    try:
        # main.py를 --json 옵션과 함께 서브프로세스로 실행
        # 딥러닝(KR-FinBERT) 모델의 메모리 관리를 위해 독립 프로세스 실행이 안전합니다.
        result = subprocess.run(
            ["python", "main.py", "--json"], 
            check=True, 
            capture_output=True, 
            text=True
        )
        
        # 생성된 JSON 파일 읽기
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        else:
            raise HTTPException(status_code=500, detail="분석 결과 파일이 생성되지 않았습니다.")
            
    except subprocess.CalledProcessError as e:
        print("[오류] main.py 실행 중 예기치 않은 에러:", e.stderr)
        raise HTTPException(status_code=500, detail=f"분석 파이프라인 실행 중 오류가 발생했습니다: {e.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # 기본 포트 8080번으로 서버 실행 (8000번 포트 충돌 방지)
    uvicorn.run(app, host="0.0.0.0", port=8080)
