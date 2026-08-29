# AIthleewPro

**Plugin Lightroom Classic — Chỉnh màu AI, Lọc ảnh, Chat AI & Tether FTP**

Tự động phân tích ảnh và áp dụng hiệu chỉnh chuyên nghiệp chỉ với một cú click, sử dụng Cloud Vision AI kết hợp Histogram Metering chính xác.

---

## Có gì mới ở V2.0

### Hệ thống AI Đa Nhà Cung Cấp
- Tích hợp **5 nhà cung cấp** với **100+ mô hình Vision AI**: Agnes AI, KiraAI Vietnam, OpenRouter, NVIDIA NIM, Kilo Code
- **Tự động fallback** khi gặp sự cố — không bị gián đoạn khi một provider lỗi

### Adobe Sensei AI Auto Masking
- Tự động nhận diện và tạo mặt nạ cho **Subject**, **Sky**, **Background**
- Trích xuất 100% kết luận từ Vision AI vào preset XMP của Lightroom
- Khắc phục triệt để lỗi *"Requested content was not found in this photo"*

### Hiệu chỉnh Quang học Đa thuộc tính
- Điều chỉnh tinh tế trên toàn bộ thanh trượt: Exposure, Texture, Clarity, Sharpness, Saturation, Dehaze...

### Menu Cân Bằng Trắng Linh Hoạt
- **5 phong cách WB**: Bình thường, Xanh hơn, Vàng hơn, Tím hơn, Xanh lá hơn
- Phản hồi và cập nhật thời gian thực

### Xử lý Hàng loạt (Batch)
- Áp dụng đầy đủ thuật toán nhận diện RAW/Non-RAW, cân bằng trắng và tạo mặt nạ AI cho toàn bộ album

### Giao diện Tinh gọn
- Tách biệt 2 nút áp dụng màu sắc và áp dụng mặt nạ
- Mặc định tắt masking để tối ưu tốc độ

### Cập nhật khác
- Website chính thức mới và tích hợp Changelog trực tiếp trong Plugin Manager

---

## Tính năng chính

### Chỉnh màu AI
- **Phân tích tự động** ảnh và đề xuất hiệu chỉnh White Balance, Tone, Color Grading, HSL
- **Nhận diện Scene** — 26 thể loại: portrait, landscape, night, food, wedding, wildlife...
- **10 Color Look Styles** — Auto Optimal, Cinematic, Korean Pastel, Vintage Film, Moody Emerald, Golden Hour, Urban Cyber, Wedding Romance, B&W Fine Art, Natural
- **5 mức Lighting Bias** — Tối (Low-Key) → Sáng (High-Key)
- **3 Saturation Dynamics** — Pastel Soft, Standard, Rich & Punchy
- **Color Grading 3-way** — Tự động phối màu Shadows/Midtones/Highlights
- **HSL 8 kênh** — Chỉnh Hue/Saturation/Luminance riêng cho từng màu
- **Presence & Detail** — Texture, Clarity, Dehaze, Sharpening, Noise Reduction
- **AI Auto Masking** — Nhận diện Subject, Sky, Background bằng Adobe Sensei
- **Live Preview** — Xem trước hiệu chỉng trước khi áp dụng
- **AI Notes** — Giải thích lý do AI chọn các hiệu chỉnh đó

### Cân bằng trắng tự động (AI Auto WB)
- Phân tích Color Cast bằng AI cho cả RAW và Non-RAW
- **4 WB Bias** — Trung tính, Ấm nhẹ, Ấm vàng, Mát mẻ
- Hiển thị nhiệt độ đề xuất (Kelvin cho RAW, relative cho JPEG/TIFF)

### Lọc ảnh AI (Culling)
- **Chấm điểm 0-100** qua 4 tiêu chí: Sharpness, Exposure, Expression, Composition
- **Phân loại tự động**: Keeper / Acceptable / Reject
- **Gán Rating & Color Label** dựa trên điểm số
- **Batch Culling** — Xử lý hàng loạt với custom rules

### Xử lý hàng loạt (Batch)
- Phân tích & áp dụng AI cho nhiều ảnh cùng lúc
- Áp dụng Style/Lighting/Intensity Bias chung cho toàn bộ batch
- Auto-WB tích hợp trong batch

### Chat AI — Chỉnh ảnh theo Prompt
- **14 Quick-Prompt buttons** — "Tăng exposure", "Film look", "Golden hour", "Teal & Orange"...
- **Natural Language Edit** — Mô tả mong muốn bằng ngôn ngữ tự nhiên, AI chuyển thành develop settings
- **Workflow tách biệt** — Gửi prompt → Nhận kết quả → Xem trước → Áp dụng

### Tether FTP — Chụp trực tiếp
- **9 Camera Profiles** — Sony A7 III/IV/RV, Canon R5/R6 II, Nikon Z6 II/Z8, Fuji X-T5, Panasonic S5 II
- **Multi-camera** — Hỗ trợ nhiều máy kết nối đồng thời
- **Auto Import** — Tự động import ảnh vào Lightroom catalog khi chụp
- **Hướng dẫn kết nối** — Hiển thị menu path cho từng máy

### Hệ thống Preset
- **9 categories** — Portraits, Landscapes, Night, Food, Product, Macro, Street, Architecture, Custom
- **6 built-in presets** — Natural, Soft, Warm (portraits); Vivid, Golden Hour, Dramatic Sky (landscapes)
- **Lưu preset tùy chỉnh** từ bất kỳ hiệu chỉnh nào
- **Tìm kiếm & lọc** preset theo category

### Undo/Redo
- **50 states** — Hoàn tác/toàn lại toàn bộ hiệu chỉnh từ plugin

---

## Bản Free (AIthleewFree)

Phiên bản miễn phí với các tính năng:

### Chỉnh màu AI Cơ bản
- **10 thanh trượt cơ bản**: Temperature, Tint, Exposure, Contrast, Highlights, Shadows, Whites, Blacks, Vibrance, Saturation
- **Nhận diện Scene** — 26 thể loại
- **Histogram 5-zone analysis**
- **1 model AI**: `meta/llama-3.2-11b-vision-instruct` (NVIDIA NIM)
- Xử lý từng ảnh đơn (không có Batch)

### Tether FTP — Dùng thử 1 tiếng
- **60 phút** sử dụng FTP server (tính thời gian khi server bật)
- Hỗ trợ **9 camera brands**: Sony, Canon, Nikon, Fuji, Panasonic
- Auto-import vào Lightroom catalog

### Cài đặt
- Nhập NVIDIA NIM API Key
- Cấu hình Python path

> **Lưu ý**: Bản Free không có AI Masking, HSL, Color Grading, Chat AI, Batch Processing, Culling, Preset Save, Undo/Redo, và giới hạn 1 model AI. Nâng cấp lên Pro để mở khóa toàn bộ tính năng.

---

## Cloud Vision AI

Hỗ trợ **100+ vision models** từ **5 providers** với **tự động fallback**. Dưới đây là các model đáng dùng nhất (vision input → text output):

### Agnes AI
| Model ID | Đánh giá |
|----------|----------|
| `agnes-2.5-flash` | ✅ **Khuyên dùng** — Nhanh, chuẩn xác, miễn phí |
| `agnes-2.0-flash` | Miễn phí, dự phòng tốt |

### NVIDIA NIM
| Model ID | Đánh giá |
|----------|----------|
| `meta/llama-3.2-11b-vision-instruct` | ✅ **Khuyên dùng** — Cân bằng tốc độ & chất lượng |
| `meta/llama-3.2-90b-vision-instruct` | Chất lượng cao nhất, chậm hơn |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | 30B đa phương thức + reasoning |
| `google/gemma-4-31b-it` | Google Gemma mới, miễn phí |
| `stepfun-ai/step-3.7-flash` | Siêu nhanh, miễn phí |
| `meta/muse-glimmer-30b` | Phong cách nghệ thuật |
| `google/diffusiongemma-26b-a4b-it` | Miễn phí, đa năng |
| `minimaxai/minimax-m3` | Miễn phí, nhanh |

### OpenRouter — Miễn phí
| Model ID | Đánh giá |
|----------|----------|
| `google/gemma-4-31b-it:free` | ✅ **Miễn phí #1** — 31B MoE, context 262K |
| `google/gemma-4-26b-a4b-it:free` | ✅ **Miễn phí #2** — MoE nhẹ, tiết kiệm |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | 30B + reasoning |
| `openrouter/free` | Free Router tự động |
| `minimax/minimax-m3:free` | MiniMax M3 miễn phí |

### OpenRouter — Trả phí (đáng dùng)
| Model ID | Giá/1M | Đánh giá |
|----------|--------|----------|
| `google/gemini-2.5-flash` | $0.30 | ✅ **Chất lượng cao** — Google Gemini mới nhất |
| `openai/gpt-4o-mini` | $0.15 | Rẻ, chất lượng tốt |
| `openai/gpt-5-mini` | $0.25 | Nhanh, giá rẻ |
| `qwen/qwen3.7-flash` | $0.03 | ✅ **Rẻ nhất** — Qwen 3.7 chuyên ảnh |
| `qwen/qwen3-vl-32b-instruct` | $0.10 | Vision-Language chuyên biệt |
| `qwen/qwen3.8-flash` | $0.15 | Qwen mới, cân bằng |
| `deepseek/deepseek-v4-flash-vision-exp` | $0.22 | DeepSeek mới, giá hợp lý |
| `anthropic/claude-3-haiku` | $0.25 | Claude nhẹ, nhanh |
| `anthropic/claude-haiku-4.5` | $1.00 | Claude mới nhất |
| `meta-llama/llama-4-maverick` | $0.20 | Meta Llama 4 mới |
| `google/gemini-2.5-pro` | $1.25 | Chất lượng cao |
| `openai/gpt-4o` | $2.50 | GPT-4o chính thức |
| `anthropic/claude-sonnet-4` | $3.00 | Claude Sonnet mới |

### KiraAI Vietnam
| Model ID | Đánh giá |
|----------|----------|
| `deepseek-v4-flash-vision-exp` | ✅ Miễn phí, DeepSeek mới |
| `glm-5.3-flash` | Miễn phí, Z.ai nhanh |
| `qwen3.8-flash` | Miễn phí, Qwen 3.8 |
| `mimo-v2.5` | Miễn phí, Xiaomi |

### Kilo Code
| Model ID | Đánh giá |
|----------|----------|
| `stepfun/step-3.7-flash:free` | Miễn phí, siêu nhanh |
| `thinkingmachines/inkling:free` | Miễn phí ⚠️ Dữ liệu có thể bị khai thác |
| `thinkingmachines/inkling-small:free` | Miễn phí ⚠️ Dữ liệu có thể bị khai thác |
| `kilo-auto/balanced` | Auto-routing, tự đọc model tốt nhất |
| `kilo-auto/frontier` | Auto-routing, ưu tiên chất lượng |
| `kilo-auto/efficient` | Auto-routing, tiết kiệm chi phí |

**Offline Fallback** — Hoạt động không cần internet qua Traditional CV + Histogram.

---

## Cài đặt

1. Copy thư mục `AutoColorPro.lrplugin` vào:
   - **macOS:** `~/Library/Application Support/Adobe/Lightroom/Modules/`
   - **Windows:** `%APPDATA%\Adobe/Lightroom/Modules/`
2. Cài Python dependencies: `cd python_engine && pip install -r requirements.txt`
3. Nhập API Key trong **Plugin Extras → Cài đặt hệ thống**
4. Khởi động lại Lightroom Classic

---

## Yêu cầu

- Lightroom Classic 10.0+
- Python 3.9+ (khuyến nghị 3.11)
- API Key từ Agnes AI, OpenRouter, NVIDIA NIM, KiraAI hoặc Kilo Code (đều có free tier)

---

## Phiên bản

| | Pro | Plus | Free |
|--|-----|------|------|
| **Giá** | N/A | N/A | Miễn phí |
| **Chỉnh màu AI** | Full (3 sections) | Full | Mục 1 cơ bản (Tone & Exposure) |
| **Auto White Balance** | ✅ | ✅ | ❌ |
| **Color Look Styles (10)** | ✅ | ✅ | ❌ |
| **Color Grading + HSL** | ✅ | ✅ | ❌ |
| **AI Auto Masking** | ✅ | ✅ | ❌ |
| **Chat AI** | ✅ | ❌ | ❌ |
| **Tether FTP** | Unlimited | Unlimited | Dùng thử 30 phút |
| **Batch Processing** | Unlimited | Unlimited | ❌ |
| **AI Culling** | Full + Rules | Full | Giới hạn 20 ảnh |
| **Cloud Models** | 100+ | 5 | 1 (llama-3.2-11b) |
| **Undo/Redo (50 states)** | ✅ | ✅ | ❌ |
| **Custom Preset Save** | ✅ | ❌ | ❌ |
| **Live Preview** | ✅ | ❌ | ❌ |
| **AI Notes** | ✅ | ❌ | ❌ |
| **Custom Model Input** | ✅ | ❌ | ❌ |
| **Watermark** | ❌ | ❌ | ✅ |
