# AIthleewPro

**Plugin Lightroom Classic — Chỉnh màu AI, Lọc ảnh, Chat AI & Tether FTP**

Tự động phân tích ảnh và áp dụng hiệu chỉnh chuyên nghiệp chỉ với một cú click, sử dụng Cloud Vision AI kết hợp Histogram Metering chính xác.

---

## Tính năng chính

### Phân tích & Chỉnh màu AI
- **Tự động phân tích** ảnh và đề xuất hiệu chỉnh White Balance, Tone, Color Grading, HSL
- **Nhận diện Scene** — 26 thể loại: portrait, landscape, night, food, wedding, wildlife...
- **10 Color Look Styles** — Natural, Cinematic, Vintage, Moody, Film Look, Teal & Orange...
- **5 mức Lighting Bias** — Tối (Low-Key) → Sáng (High-Key)
- **4 mức Intensity** — Nhẹ → Cực mạnh
- **Color Grading 3-way** — Tự động phối màu Shadows/Midtones/Highlights
- **HSL 8 kênh** — Chỉnh Hue/Saturation/Luminance riêng cho Red, Orange, Yellow, Green, Aqua, Blue, Purple, Magenta
- **Presence & Detail** — Texture, Clarity, Dehaze, Sharpening, Noise Reduction
- **Effects** — Vignette, Grain
- **Live Preview** — Xem trước hiệu chỉnh trước khi áp dụng
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

---

## Cloud Vision AI

Hỗ trợ **13 vision models** từ 3 providers với **tự động fallback**:

### NVIDIA NIM (Cần NVIDIA API Key)

| Model ID | Nhà cung cấp | Mô tả | Khuyên dùng |
|----------|--------------|-------|-------------|
| `meta/llama-3.2-11b-vision-instruct` | Meta | 11B Vision — nhanh, chuẩn xác, tiết kiệm token | ✅ Mặc định |
| `meta/llama-3.2-90b-vision-instruct` | Meta | 90B Vision — chất lượng cao nhất, chậm hơn | Chất lượng cao |
| `minimaxai/minimax-m3` | MiniMax | MiniMax M3 Vision | Nhanh & đa năng |
| `meta/muse-glimmer-30b` | Meta | Meta Muse Glimmer 30B | Nghệ thuật |
| `google/diffusiongemma-26b-a4b-it` | Google | DiffusionGemma 26B A4B IT | Cân bằng |
| `google/gemma-4-31b-it` | Google | Gemma 4 31B IT | Đa phương thức |
| `stepfun-ai/step-3.7-flash` | StepFun | Step 3.7 Flash | Siêu nhanh |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | NVIDIA | 30B đa phương thức (ảnh/video/audio) + reasoning | Đa năng |

### OpenRouter — Free Tier (Cần OpenRouter API Key)

| Model ID | Nhà cung cấp | Mô tả | Khuyên dùng |
|----------|--------------|-------|-------------|
| `google/gemma-4-31b-it:free` | Google | Gemma 4 31B MoE — context 262K, chất lượng tốt | ✅ Miễn phí #1 |
| `google/gemma-4-26b-a4b-it:free` | Google | Gemma 4 26B A4B — MoE nhẹ, tiết kiệm | ✅ Miễn phí #2 |

### Kilo Code — Free Tier (Cần Kilo Code API Key)

| Model ID | Nhà cung cấp | Mô tả | Cảnh báo |
|----------|--------------|-------|----------|
| `thinkingmachines/inkling:free` | ThinkingMachines | Inkling Vision Free | ⚠️ Dữ liệu ảnh có thể bị khai thác bởi bên thứ 3 |
| `stepfun/step-3.7-flash:free` | StepFun | Step 3.7 Flash Free | Nhanh & ổn định |
| `thinkingmachines/inkling-small:free` | ThinkingMachines | Inkling Small Free | ⚠️ Dữ liệu ảnh có thể bị khai thác bởi bên thứ 3 |

**Offline Fallback** — Hoạt động không cần internet qua Traditional CV + Histogram.

---

## Cài đặt

1. Tải `AIthleewPro-1.0.0.zip` và giải nén vào:
   - **macOS:** `~/Library/Application Support/Adobe/Lightroom/Modules/`
   - **Windows:** `%APPDATA%\Adobe\Lightroom/Modules/`
2. Cài Python dependencies: `cd python_engine && pip install -r requirements.txt`
3. Nhập API Key trong **Plugin Extras → ⚙️ Cài đặt hệ thống**

---

## Yêu cầu

- Lightroom Classic 10.0+
- Python 3.9+
- API Key từ NVIDIA NIM hoặc OpenRouter (có free tier)

---

## Phiên bản

| | Pro | Plus | Free |
|--|-----|------|------|
| **Giá** | N/A | N/A | Miễn phí |
| **Chỉnh màu AI** | Full | Full | Mục 1 cơ bản (Tone & Exposure) |
| **Auto White Balance** | ✅ | ✅ | ❌ |
| **Color Look Style** | 10 styles | 10 styles | ❌ |
| **Color Grading + HSL** | ✅ | ✅ | ❌ |
| **Chat AI** | ✅ | ❌ | ❌ |
| **Tether FTP** | ✅ (9 cameras) | ✅ (9 cameras) | ⏱️ Dùng thử 30 phút |
| **Batch Processing** | Unlimited | Unlimited | ❌ |
| **AI Culling** | Full + Rules | Full | Giới hạn 20 ảnh |
| **Cloud Models** | 13 | 5 | 1 (llama-3.2-11b) |
| **Undo/Redo** | ✅ | ✅ | ❌ |
| **Custom Preset Save** | ✅ | ❌ | ❌ |