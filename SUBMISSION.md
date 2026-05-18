# Hướng Dẫn Nộp Bài - Lab #28: Full Platform Integration Sprint

## Yêu Cầu Nộp Bài

**Full AI infrastructure platform demo** - từ data ingestion đến model serving với full observability.

## Các Artifacts Cần Nộp

### 1. Source Code
- Folder `lab28/` hoàn chỉnh với tất cả files
- Tất cả integration scripts hoạt động
- Prefect flows đã deploy và schedule

### 2. Screenshots Demo
Chụp màn hình các bước:
- Prefect UI: http://localhost:4200 (flow đang chạy)
- API Gateway call: `curl http://localhost:8000/health`
- Grafana dashboard: http://localhost:3000

### 3. Kết Quả Smoke Tests
Chạy và chụp màn hình kết quả:
```bash
cd lab28
pytest smoke-tests/ -v
```
Kỳ vọng: 5/5 tests passing

### 4. Production Readiness Score
```bash
python scripts/production_readiness_check.py
```
Kỳ vọng: Score >80%

### 5. Documentation
- `README.md` giải thích cách:
  - Start platform: `docker compose up -d`
  - Deploy Prefect flows
  - Run smoke tests
  - Access dashboards (Grafana:3000, Prometheus:9090, Prefect:4200)

## Định Dạng Nộp Bài

Tạo Repo GitHub chứa:
```
lab28_submission_[student_id]
├── lab28/                    # Source code hoàn chỉnh
│   ├── docker-compose.yml
│   ├── prefect/flows/
│   ├── scripts/
│   ├── api-gateway/
│   └── monitoring/
├── screenshots/              # Screenshots demo
│   ├── prefect_ui.png
│   ├── api_gateway.png
│   └── grafana_dashboard.png
├── smoke_tests_results.png   # Screenshot kết quả pytest
├── production_readiness.png  # Screenshot readiness score
└── README.md                # Hướng dẫn setup
```

## Địa Điểm Nộp
Nộp link repo GitHub qua LMS

## Tiêu Chí Chấm Điểm

| Tiêu Chí | Trọng Số | Mô Tả |
|----------|----------|-------|
| Integration Completeness | 40% | Tất cả 10 integration points hoạt động, data flow end-to-end |
| Observability | 25% | Logs, metrics, traces hiển thị; alerts configured |
| Performance | 20% | Latency trong SLO; load tested; không có memory leaks |
| Architecture Quality | 15% | Clean separation, GitOps config, documented decisions |

## Các Vấn Đề Cần Tránh

- Config drift giữa các environments
- Thiếu error handling tại integration points
- Monitoring coverage không hoàn chỉnh
- Không có rollback strategy
- Demo không test trước khi nộp

## 5 Câu Hỏi Trả Lời Khi Nộp Bài

### 1. Phân tích các trade-offs trong thiết kế kiến trúc AI platform của bạn. Bạn đã cân bằng giữa performance, reliability, và maintainability như thế nào?
*   **Performance vs Cost (Trade-off lớn nhất)**: Bằng cách tách biệt việc tính toán nặng (vLLM Serving & Embedding) lên môi trường Kaggle GPU miễn phí và chạy các pipeline xử lý dữ liệu khác (Kafka, Prefect, Qdrant, Feast) ở Local, chúng ta đạt được hiệu năng suy luận vượt trội (chạy model 7B thực tế dưới 2 giây) với chi phí tài nguyên local = 0. Đổi lại, hệ thống phải gánh chịu một khoản hao phí trễ mạng (Network Latency) nhỏ thông qua ngrok.
*   **Reliability vs Complexity**: Để tăng độ tin cậy, chúng tôi sử dụng cơ chế Backpressure của Kafka và lập lịch bất đồng bộ của Prefect. Điều này giúp hệ thống tự động phục hồi khi mất kết nối tạm thời hoặc quá tải, đổi lại kiến trúc phức tạp hơn so với gọi API trực tiếp.
*   **Maintainability**: Sử dụng Docker Compose đồng bộ hóa môi trường local giúp loại bỏ hoàn toàn hiện tượng lệch cấu hình (Config Drift). API Gateway được chuẩn hóa bằng Pydantic Model giúp việc bảo trì, cập nhật API cực kỳ dễ dàng mà không làm ảnh hưởng đến các service hạ tầng khác.

### 2. Trong kiến trúc hybrid (Local + Kaggle), bạn xử lý ngắt kết nối giữa local và Kaggle như thế nào? Có cơ chế fallback không?
*   **Nhận diện ngắt kết nối**: API Gateway sử dụng cấu hình `timeout=30` giây khi kết nối thông qua `httpx.AsyncClient`. Nếu có lỗi kết nối (ngrok bị ngắt, tắt session Kaggle), API Gateway sẽ ném ra lỗi Timeout và được xử lý trong khối `try-except` mà không gây treo hay crash toàn bộ hệ thống API Gateway.
*   **Cơ chế Fallback**: 
    1.  **Fallback Cấp 1 (Mock Services)**: Trỏ API Gateway về hệ thống `mock_services.py` chạy cục bộ trên port 8001 của host machine. API Gateway vẫn hoạt động mượt mà, trả về kết quả giả lập chất lượng cao cho việc phát triển và kiểm thử nội bộ.
    2.  **Fallback Cấp 2 (Graceful Degradation)**: Trong trường hợp vLLM bị ngắt kết nối thật nhưng Qdrant và Feast vẫn sống, Gateway có thể trả về phần kết quả tìm kiếm ngữ cảnh (Context) từ Vector database kèm theo thông báo lỗi LLM tạm thời, giúp người dùng cuối vẫn có dữ liệu tra cứu cơ bản thay vì một màn hình trắng lỗi.

### 3. Giải thích cách event-driven architecture với Kafka giúp decouple các components trong AI platform của bạn.
*   **Decoupling về Thời Gian (Temporal Decoupling)**: Ứng dụng nguồn đẩy dữ liệu thô trực tiếp vào Kafka Topic `data.raw` mà không cần biết khi nào hay làm thế nào dữ liệu được xử lý. Các service tiêu thụ dữ liệu (Prefect flow) có thể chạy bất đồng bộ theo lịch trình hoặc sự kiện bất cứ lúc nào.
*   **Decoupling về Không Gian (Space Decoupling)**: Producer của ứng dụng nguồn và Consumer (Prefect worker) không cần biết địa chỉ IP hay sự tồn tại của nhau, tất cả giao tiếp đều qua Broker trung gian Kafka.
*   **Xử lý Backpressure**: Khi dữ liệu thô đổ về với số lượng cực lớn, Kafka đóng vai trò như một bộ đệm lưu trữ an toàn (Buffer). Prefect consumer có thể kéo dữ liệu (fetch) theo lô (batch) vừa sức xử lý của nó, tránh việc hệ thống hạ tầng bị sập do quá tải (Spike in traffic).
*   **Data Replayability**: Dữ liệu trong Kafka có thể được lưu trữ dài hạn. Nếu một module xử lý (như Qdrant) bị lỗi, chúng ta hoàn toàn có thể cấu hình reset offset của Consumer để chạy lại toàn bộ luồng dữ liệu từ quá khứ mà không cần yêu cầu ứng dụng nguồn gửi lại.

### 4. Bạn đã implement observability như thế nào? Logs, metrics, và traces được thu thập và visualized ra sao?
*   **Metrics**: Sử dụng `prometheus-fastapi-instrumentator` tích hợp trong API Gateway để tự động thu thập các chỉ số RED (Rate - Tần suất request, Errors - Tỷ lệ lỗi, Duration - Thời gian phản hồi). Prometheus liên tục scrape dữ liệu từ cổng `/metrics` của API Gateway và Grafana sẽ trực quan hóa các metrics này lên dashboard trực quan thời gian thực.
*   **Traces (LLM Tracing)**: Tích hợp thư viện `langsmith` vào mã nguồn API Gateway. Mọi luồng suy luận RAG (gồm: Embedding nhận được -> Vector Search trên Qdrant thu được Context gì -> Prompt gửi đi -> LLM hoàn thiện phản hồi gì) đều được LangSmith ghi nhận chi tiết, phân tích rõ độ trễ của từng bước và kiểm soát chi phí token.
*   **Logs**: Toàn bộ hệ thống container (Kafka, Prefect, Qdrant, Redis) được Docker cấu hình tập trung hóa logs. Có thể dễ dàng truy xuất logs qua lệnh `docker compose logs -f <service>` để gỡ lỗi tức thời.

### 5. Nếu một service trong stack (ví dụ: Qdrant hoặc Kafka) bị crash, hệ thống của bạn sẽ xử lý như thế nào? Có graceful degradation không?
*   **Trường hợp Kafka bị crash**: Luồng đẩy dữ liệu vào topic bị gián đoạn, tuy nhiên API Gateway vẫn có thể phục vụ các request truy vấn dữ liệu cũ đã lưu sẵn trong Feast (Redis) và Qdrant bình thường. Hệ thống Prefect worker sẽ liên tục thử kết nối lại (reconnect) và xử lý bù dữ liệu ngay khi Kafka hoạt động trở lại.
*   **Trường hợp Qdrant (Vector DB) bị crash**: Khi API Gateway gọi sang Qdrant bị lỗi kết nối, hệ thống sẽ thực hiện **Graceful Degradation** bằng cách bắt exception, tự động bỏ qua bước Vector Search lấy Context, và chuyển thẳng Query gốc của người dùng sang cho LLM xử lý trực tiếp kèm theo tag cảnh báo `[No Context Available]`. 
*   **Tính kiên cố của container**: Nhờ cơ chế `restart: on-failure` được cấu hình chi tiết cho các container trong `docker-compose.yml`, các service bị sập sẽ tự động được Docker daemon khởi động lại ngay lập tức mà không cần sự can thiệp thủ công của quản trị viên.

## Câu Hỏi Thêm?
Liên hệ giảng viên qua LMS hoặc office hours.
