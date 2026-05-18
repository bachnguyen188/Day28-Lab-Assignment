# scripts/run_kaggle_gateway_cf.py
import os
import subprocess
import threading
import time
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sentence_transformers import SentenceTransformer
import uvicorn

# 1. Thiết lập biến môi trường CUDA để Ninja và linker tìm thấy libcuda.so
os.environ["LIBRARY_PATH"] = "/usr/local/cuda/lib64/stubs:" + os.environ.get("LIBRARY_PATH", "")
os.environ["LD_LIBRARY_PATH"] = "/usr/local/cuda/lib64/stubs:" + os.environ.get("LD_LIBRARY_PATH", "")

# Tạo symlink bổ sung để đảm bảo trình liên kết chắc chắn tìm thấy
subprocess.run("ln -sf /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/libcuda.so", shell=True)
subprocess.run("ln -sf /usr/local/cuda/lib64/stubs/libcuda.so /usr/lib/x86_64-linux-gnu/libcuda.so", shell=True)

# 2. Khởi tạo FastAPI gateway
app = FastAPI(title="Kaggle Hybrid Gateway (Cloudflare Version)")

# Tải model SentenceTransformer cho Embedding Service
print("⚡ Đang tải model Embedding (BAAI/bge-small-en-v1.5)...")
embed_model = SentenceTransformer("BAAI/bge-small-en-v1.5")
print("✅ Tải model Embedding thành công!")

@app.post("/embed")
def embed(body: dict):
    texts = body.get("texts", [])
    embeddings = embed_model.encode(texts).tolist()
    return {"embeddings": embeddings}

# Cổng đích kết nối tới vLLM
VLLM_URL = "http://127.0.0.1:8001"

@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_vllm(path: str, request: Request):
    import httpx
    url = f"{VLLM_URL}/v1/{path}"
    headers = dict(request.headers)
    
    # Loại bỏ các header giao thức có thể gây lỗi httpx
    for h in ["host", "content-length", "connection"]:
        headers.pop(h, None)
        
    method = request.method
    content = await request.body()
    
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                content=content
            )
            return StreamingResponse(
                response.aiter_bytes(),
                status_code=response.status_code,
                media_type=response.headers.get("content-type")
            )
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": f"Lỗi kết nối vLLM: {str(e)}"}
            )

@app.get("/logs")
def get_logs():
    if os.path.exists("vllm.log"):
        with open("vllm.log", "r") as f:
            return f.read()
    return "Không tìm thấy file vllm.log"

def run_vllm():
    print("🚀 Đang khởi động vLLM Server...")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["VLLM_USE_FLASHINFER_SAMPLER"] = "0"
    env["VLLM_ATTENTION_BACKEND"] = "TRITON_ATTN"
    
    with open("vllm.log", "w") as log_file:
        subprocess.run([
            "python3", "-m", "vllm.entrypoints.openai.api_server",
            "--model", "Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4",
            "--port", "8001",
            "--max-model-len", "2048",
            "--enforce-eager",
            "--gpu-memory-utilization", "0.75",
            "--attention-backend", "TRITON_ATTN"
        ], stdout=log_file, stderr=log_file, env=env)

# Chạy Cloudflare Tunnel không chặn (non-blocking) và in ra URL
def run_cloudflare_tunnel():
    print("📥 Kiểm tra và tải cloudflared...")
    if not os.path.exists("cloudflared"):
        subprocess.run("wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared && chmod +x cloudflared", shell=True)
    
    print("🔌 Đang tạo đường truyền Cloudflare Tunnel...")
    # Tắt tiến trình cloudflared cũ nếu có
    subprocess.run("pkill -f cloudflared", shell=True)
    time.sleep(1)
    
    proc = subprocess.Popen(
        ["./cloudflared", "tunnel", "--url", "http://localhost:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    for line in proc.stdout:
        if ".trycloudflare.com" in line:
            # Tìm và trích xuất URL sạch từ dòng log
            words = line.split()
            cf_url = None
            for w in words:
                if "trycloudflare.com" in w:
                    cf_url = w.strip().replace("\x1b", "").replace("[0m", "")
                    if "https://" not in cf_url:
                        cf_url = "https://" + cf_url
                    break
            if cf_url:
                print("\n" + "="*60)
                print(f"🎉 THÀNH CÔNG! ĐƯỜNG LINK CLOUDFLARE TUNNEL CỦA BẠN:")
                print(f"👉 {cf_url}")
                print("="*60 + "\n")
                break

if __name__ == "__main__":
    # Dọn dẹp tài nguyên cũ
    subprocess.run("pkill -f uvicorn", shell=True)
    subprocess.run("pkill -f vllm", shell=True)
    subprocess.run("pkill -f multiprocessing", shell=True)
    time.sleep(2)
    
    # Khởi chạy vLLM ở luồng phụ (port 8001)
    threading.Thread(target=run_vllm, daemon=True).start()
    
    # Khởi chạy Cloudflare Tunnel ở luồng phụ
    threading.Thread(target=run_cloudflare_tunnel, daemon=True).start()
    
    # Khởi chạy FastAPI Gateway ở cổng 8000
    print("⚡ Khởi chạy FastAPI Gateway ở cổng 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
