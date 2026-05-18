# mock_services.py
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Mock Kaggle GPU Services")

@app.post("/embed")
def embed(body: dict):
    texts = body.get("texts", [])
    # Return mock 384-dimensional embeddings
    return {"embeddings": [[0.1] * 384 for _ in texts]}

@app.post("/v1/chat/completions")
def chat_completions(body: dict):
    return {
      "choices": [
        {
          "message": {
            "content": "This is a mock response from the platform vLLM model."
          }
        }
      ],
      "model": "Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
