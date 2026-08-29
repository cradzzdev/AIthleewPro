--[[
    AIthleewFree - UI Panel
    Giao diện Chỉnh Màu AI phiên bản Free:
    - Watermark / Header Free Edition
    - Phân tích AI tự động ảnh đơn & Scene Detection
    - Cột 1: Ánh sáng & Sắc độ cơ bản (Exposure, Contrast, Highlights, Shadows, Whites, Blacks, Temp, Tint, Vibrance, Saturation)
    - Khóa các tính năng nâng cao (Color Grading, HSL 8-kênh, AI Auto Masking, Cân bằng trắng linh hoạt, Look Styles, Lighting Bias, Chat AI, Batch)
]]

local LrDialogs = import "LrDialogs"
local LrView = import "LrView"
local LrBinding = import "LrBinding"
local LrFunctionContext = import "LrFunctionContext"
local LrTasks = import "LrTasks"
local LrApplication = import "LrApplication"
local LrPathUtils = import "LrPathUtils"
local LrFileUtils = import "LrFileUtils"
local LrColor = import "LrColor"

local pluginDir = (_PLUGIN and _PLUGIN.path) or LrPathUtils.child(LrPathUtils.getStandardFilePath("appData"), "Modules/AIthleewFree.lrplugin")
if not LrPathUtils.isAbsolute(pluginDir) or not LrPathUtils.child(pluginDir, "Info.lua") then
    local fallback = LrPathUtils.child(LrPathUtils.getStandardFilePath("appData"), "Modules/AutoColorFree.lrplugin")
    if LrPathUtils.isAbsolute(fallback) then pluginDir = fallback end
end
local function loadModule(modulePath)
    local fullPath = LrPathUtils.child(pluginDir, modulePath)
    local chunk, err = loadfile(fullPath)
    if chunk then return chunk() else error("Lỗi nạp module: " .. modulePath .. " - " .. tostring(err)) end
end

local Logger = loadModule("Utils/Logger.lua")
local Export = loadModule("Utils/Export.lua")
local Config = loadModule("Utils/Config.lua")
local Adjuster = loadModule("Core/Adjuster.lua")
local FormatHelper = loadModule("Utils/FormatHelper.lua")

local logger = Logger:getLogger("Panel")

local function translateScene(sceneName)
    if not sceneName or sceneName == "" or sceneName == "Unknown" or sceneName == "unknown" then
        return "Chưa phân tích"
    end
    local s = string.lower(tostring(sceneName))
    local map = {
        portrait = "👤 Chân dung cá nhân (Portrait)",
        group_portrait = "👥 Ảnh nhóm / Gia đình (Group Portrait)",
        wedding = "💍 Ảnh cưới / Cô dâu chú rể (Wedding)",
        fashion = "👗 Thời trang / Lookbook (Fashion)",
        baby_kids = "👶 Trẻ em / Sơ sinh (Baby & Kids)",
        landscape = "🏞️ Phong cảnh thiên nhiên (Landscape)",
        seascape = "🌊 Biển / Bờ biển (Seascape & Beach)",
        beach = "🏖️ Bãi biển (Beach)",
        sunset = "🌅 Hoàng hôn / Bình minh (Sunset & Golden Hour)",
        cityscape = "🏙️ Toàn cảnh đô thị (Cityscape)",
        architecture = "🏛️ Kiến trúc công trình (Architecture)",
        interior = "🛋️ Không gian nội thất (Interior)",
        street = "🚶 Đời thường / Đường phố (Street)",
        documentary = "📰 Phóng sự / Sự kiện (Documentary)",
        night = "🌃 Cảnh đêm / Ánh đèn (Night)",
        astro = "🌌 Thiên văn / Bầu trời sao (Astro)",
        food = "🍲 Ẩm thực / Món ăn (Food)",
        product = "📦 Sản phẩm thương mại (Product)",
        macro = "🔍 Cận cảnh / Macro",
        wildlife = "🦁 Động vật / Thú cưng (Wildlife & Pets)",
        sports = "🏃 Thể thao / Chuyển động (Sports)",
        automotive = "🚗 Xe cộ / Ô tô (Automotive)",
        vintage = "🎞️ Cổ điển / Film hoài niệm (Vintage)",
        black_and_white = "⬛ Đen trắng nghệ thuật (B&W)",
        concert = "🎤 Sân khấu / Ca nhạc (Concert)",
        aerial = "🚁 Flycam / Góc chụp trên không (Aerial)",
        snow = "❄️ Mùa đông / Tuyết trắng (Snow & Winter)",
        indoor = "🏠 Trong nhà (Indoor)",
        general = "📷 Tự nhiên / Đa dụng (General)",
    }
    return map[s] or (sceneName:sub(1,1):upper() .. sceneName:sub(2))
end

local function formatSigned(val, unit)
    val = tonumber(val) or 0
    unit = unit or ""
    if val > 0 then
        return string.format("+%s%s", tostring(val), unit)
    else
        return string.format("%s%s", tostring(val), unit)
    end
end

local Panel = {}
Panel.__index = Panel

function Panel:show(context, task_runner)
    Config:load()

    local catalog = LrApplication.activeCatalog()
    local target_photos = catalog:getTargetPhotos()

    if #target_photos == 0 then
        LrDialogs.message("Chưa chọn ảnh", "Vui lòng chọn 1 bức ảnh trong thư viện trước khi mở bảng điều khiển.")
        return
    end

    local current_photo = target_photos[1]
    local adjuster = Adjuster:new()

    local props = LrBinding.makePropertyTable(context)
    props.status_text = "Sẵn sàng phân tích..."
    props.progress_number_display = "[ 0% ]"
    props.progress_stage_text = "Đang chờ khởi tạo..."
    props.detected_scene = "Đang quét..."
    props.confidence_text = "--"
    props.active_model_name = "Meta Llama 3.2 11B Vision (Free Edition Model)"
    props.is_analyzing = false

    -- Column 1 Properties (Basic Tone)
    props.val_exposure = "--"
    props.val_contrast = "--"
    props.val_highlights = "--"
    props.val_shadows = "--"
    props.val_whites = "--"
    props.val_blacks = "--"
    props.val_temp = "--"
    props.val_tint = "--"
    props.val_vibrance = "--"
    props.val_saturation = "--"

    local f = LrView.osFactory()
    local fileName = current_photo:getFormattedMetadata("fileName") or "Ảnh đang chọn"
    local dialog_title = "AIthleewFree - " .. fileName

    local dialog_contents = f:column {
        bind_to_object = props,
        spacing = f:control_spacing(),
        width = 680,

        -- 0. Watermark & Free Badge Header
        f:row {
            f:static_text {
                title = "✨ AIthleewFree — Phiên bản Miễn phí (Basic Edition)",
                font = "<system/bold>",
                text_color = LrColor(0.1, 0.5, 0.9),
                size = "large",
            },
            f:static_text {
                title = "🎁 [Gói Free]",
                font = "<system/bold>",
                text_color = LrColor(0.85, 0.45, 0.1),
                alignment = "right",
                fill_horizontal = true,
            },
        },

        f:separator { fill_horizontal = 1 },

        -- 1. Header & Status
        f:row {
            f:static_text {
                title = "📷 Đang chọn: ",
                font = "<system/bold>",
            },
            f:static_text {
                title = fileName,
                font = "<system/bold>",
                width = 250,
            },
            f:static_text {
                title = LrView.bind "status_text",
                font = "<system/small>",
                text_color = LrColor(0.2, 0.5, 0.8),
                fill_horizontal = true,
            },
        },

        -- Active Model Row (Read-only)
        f:row {
            f:static_text {
                title = "🤖 Model AI Vision:",
                font = "<system/bold>",
                width = 135,
            },
            f:static_text {
                title = LrView.bind "active_model_name",
                font = "<system/small>",
                text_color = LrColor(0.15, 0.65, 0.25),
                fill_horizontal = true,
            },
        },

        f:row {
            f:static_text {
                title = "🏷️ Bối cảnh ảnh:",
                font = "<system/bold>",
                width = 135,
            },
            f:static_text {
                title = LrView.bind "detected_scene",
                font = "<system/bold>",
                text_color = LrColor(0.15, 0.65, 0.25),
                width = 200,
            },
            f:static_text {
                title = "🎯 Độ chính xác: ",
                font = "<system/bold>",
            },
            f:static_text {
                title = LrView.bind "confidence_text",
                font = "<system/bold>",
                text_color = LrColor(0.1, 0.5, 0.9),
                fill_horizontal = true,
            },
        },

        f:separator { fill_horizontal = 1 },

        -- 2. BẢNG HIỂN THỊ THÔNG SỐ TONE & PRESENCE CƠ BẢN
        f:row {
            spacing = 10,
            width = 670,

            -- CỘT TRÁI: ÁNH SÁNG & SẮC ĐỘ CƠ BẢN (FREE ENABLED)
            f:group_box {
                title = "☀️ 1. ÁNH SÁNG & SẮC ĐỘ CƠ BẢN (FREE)",
                width = 330,
                f:column {
                    spacing = 2,
                    width = 310,

                    f:row {
                        f:static_text { title = "• Nhiệt độ màu (Temp):", width = 165, font = "<system/bold>" },
                        f:static_text { title = LrView.bind "val_temp", width = 135, text_color = LrColor(0.15, 0.5, 0.85) },
                    },
                    f:row {
                        f:static_text { title = "• Sắc thái màu (Tint):", width = 165, font = "<system/bold>" },
                        f:static_text { title = LrView.bind "val_tint", width = 135, text_color = LrColor(0.75, 0.25, 0.55) },
                    },
                    f:separator { fill_horizontal = 1 },
                    f:row {
                        f:static_text { title = "• Phơi sáng (Exposure):", width = 165, font = "<system/bold>" },
                        f:static_text { title = LrView.bind "val_exposure", width = 135 },
                    },
                    f:row {
                        f:static_text { title = "• Tương phản (Contrast):", width = 165, font = "<system/bold>" },
                        f:static_text { title = LrView.bind "val_contrast", width = 135 },
                    },
                    f:row {
                        f:static_text { title = "• Vùng sáng (Highlights):", width = 165, font = "<system/bold>" },
                        f:static_text { title = LrView.bind "val_highlights", width = 135 },
                    },
                    f:row {
                        f:static_text { title = "• Vùng tối (Shadows):", width = 165, font = "<system/bold>" },
                        f:static_text { title = LrView.bind "val_shadows", width = 135 },
                    },
                    f:row {
                        f:static_text { title = "• Sắc trắng (Whites):", width = 165, font = "<system/bold>" },
                        f:static_text { title = LrView.bind "val_whites", width = 135 },
                    },
                    f:row {
                        f:static_text { title = "• Sắc đen (Blacks):", width = 165, font = "<system/bold>" },
                        f:static_text { title = LrView.bind "val_blacks", width = 135 },
                    },
                    f:separator { fill_horizontal = 1 },
                    f:row {
                        f:static_text { title = "• Độ rực tươi (Vibrance):", width = 165, font = "<system/bold>" },
                        f:static_text { title = LrView.bind "val_vibrance", width = 135 },
                    },
                    f:row {
                        f:static_text { title = "• Độ bão hòa (Saturation):", width = 165, font = "<system/bold>" },
                        f:static_text { title = LrView.bind "val_saturation", width = 135 },
                    },
                },
            },

            -- CỘT PHẢI: TÍNH NĂNG NÂNG CAO (LOCKED - PRO ONLY)
            f:group_box {
                title = "🔒 TÍNH NĂNG NÂNG CAO (BẢN PRO)",
                width = 330,
                f:column {
                    spacing = 5,
                    width = 310,

                    f:static_text {
                        title = "💎 Nâng cấp lên AIthleewPro để mở khóa:",
                        font = "<system/bold>",
                        text_color = LrColor(0.85, 0.45, 0.1),
                    },
                    f:static_text {
                        title = "• 🎭 AI Auto Masking (Chủ thể, Hậu cảnh, Bầu trời)\n" ..
                                "• 🌡️ Tùy biến Cân bằng trắng (Cooler, Warmer...)\n" ..
                                "• 🎨 Color Grading 3-Way & 8 Kênh HSL\n" ..
                                "• 🎬 10 Phong cách Cinematic, Film, Pastel...\n" ..
                                "• 💡 Tùy biến Mức độ ánh sáng & Bão hòa\n" ..
                                "• 🔬 Presence (Texture, Clarity, Dehaze)\n" ..
                                "• 💬 Chat AI Prompt & Batch không giới hạn",
                        size = "small",
                        text_color = LrColor(0.4, 0.4, 0.4),
                    },
                    f:push_button {
                        title = "⭐ Tìm hiểu thêm về bản Pro",
                        action = function()
                            LrDialogs.message(
                                "AIthleewPro Feature Suite",
                                "Bản Pro bao gồm toàn bộ tính năng cao cấp:\n" ..
                                "- AI Auto Masking toàn diện (Chủ thể, Hậu cảnh, Bầu trời)\n" ..
                                "- Menu tùy biến Cân bằng trắng linh hoạt 5 phong cách\n" ..
                                "- Chỉnh màu 8-kênh HSL & Color Grading 3 vùng\n" ..
                                "- 10 Phong cách điện ảnh và mức độ ánh sáng tùy biến\n" ..
                                "- Chat AI chỉnh sửa trực tiếp bằng câu lệnh ngôn ngữ tự nhiên\n" ..
                                "- Sử dụng hơn 47 mô hình Vision AI tiên tiến."
                            )
                        end,
                    },
                },
            },
        },

        -- 3. Bottom Action Button
        f:row {
            spacing = 10,
            f:spacer { fill_horizontal = 1 },
            f:push_button {
                title = "🎨  Áp dụng thông số màu vào ảnh",
                width = 320,
                font = "<system/bold>",
                action = function()
                    self:applyAdjustments(current_photo, adjuster, props)
                end,
            },
            f:spacer { fill_horizontal = 1 },
        },
    }

    -- Auto-analyze photo right when panel opens
    self:analyzePhoto(current_photo, task_runner, adjuster, props, context)

    LrDialogs.presentModalDialog({
        title = dialog_title,
        contents = dialog_contents,
        actionVerb = "Đóng",
        resizable = true,
    })

    logger:info("Free Panel closed")
end

function Panel:updateUIWithAdjustments(adj, props)
    local isRaw = props.is_raw or false
    if adj.temperature ~= nil then
        if isRaw or (tonumber(adj.temperature) and tonumber(adj.temperature) > 1000) then
            props.val_temp = string.format("%d K", math.floor(tonumber(adj.temperature) or 5500))
        else
            props.val_temp = formatSigned(math.floor(tonumber(adj.temperature) or 0))
        end
    else
        props.val_temp = "--"
    end

    if adj.tint ~= nil then
        props.val_tint = formatSigned(math.floor(tonumber(adj.tint) or 0))
    else
        props.val_tint = "--"
    end

    props.val_exposure = formatSigned(string.format("%.2f", adj.exposure or 0), " EV")
    props.val_contrast = formatSigned(adj.contrast or 0)
    props.val_highlights = formatSigned(adj.highlights or 0)
    props.val_shadows = formatSigned(adj.shadows or 0)
    props.val_whites = formatSigned(adj.whites or 0)
    props.val_blacks = formatSigned(adj.blacks or 0)
    props.val_vibrance = formatSigned(adj.vibrance or 0)
    props.val_saturation = formatSigned(adj.saturation or 0)
end

function Panel:analyzePhoto(photo, task_runner, adjuster, props, context)
    if not photo then return end

    props.is_analyzing = true
    props.progress_number_display = "[ 10% ]"
    props.progress_stage_text = "Bước 1/3: Đang trích xuất ảnh xem trước..."
    props.status_text = "Đang xuất bản xem trước của ảnh..."

    local isDone = false
    local preview_path = nil

    LrTasks.startAsyncTask(function()
        local percent = 15
        while not isDone and props.is_analyzing do
            LrTasks.sleep(0.3)
            if isDone or not props.is_analyzing then break end
            if percent < 90 then
                percent = percent + 8
                props.progress_number_display = string.format("[ %d%% ]", percent)
                if percent < 40 then
                    props.progress_stage_text = "Bước 1/3: Đang trích xuất ảnh xem trước..."
                elseif percent < 75 then
                    props.progress_stage_text = "Bước 2/3: AI đo dải sáng Histogram & phân tích thị giác..."
                else
                    props.progress_stage_text = "Bước 3/3: Tối ưu thông số Tone cơ bản..."
                end
            end
        end
    end)

    LrTasks.startAsyncTask(function()
        local export = Export:new()
        preview_path = export:exportPhoto(photo, { max_dimension = 1024, quality = 85 })

        if not preview_path then
            isDone = true
            props.is_analyzing = false
            props.progress_number_display = "[ 0% ]"
            props.progress_stage_text = "Lỗi xuất ảnh xem trước"
            props.status_text = "Lỗi xuất ảnh xem trước"
            LrDialogs.message("Lỗi xuất ảnh", "Không thể xuất bản xem trước của ảnh để AI phân tích.")
            return
        end

        props.progress_number_display = "[ 45% ]"
        props.progress_stage_text = "Bước 2/3: AI đang phân tích cảnh & dải sáng..."
        props.status_text = "AI đang quét Histogram & đo lường dải sáng..."

        local isRaw, fileExt = FormatHelper.isRawPhoto(photo)
        local fileName = photo:getFormattedMetadata("fileName") or "Ảnh đang chọn"

        if not isRaw and fileName and fileName ~= "" then
            local uName = string.upper(fileName)
            for _, rawExt in ipairs(FormatHelper.RAW_LIST) do
                if uName:find("%." .. rawExt) then
                    isRaw = true
                    fileExt = rawExt
                    break
                end
            end
        end

        local devSettings = {}
        local okDev, ds = pcall(function() return photo:getDevelopSettings() end)
        if okDev and type(ds) == "table" then
            devSettings = ds
        end
        local curTemp = isRaw and devSettings.Temperature or devSettings.IncrementalTemperature
        local curTint = isRaw and devSettings.Tint or devSettings.IncrementalTint

        if curTemp == nil then curTemp = isRaw and 5500 or 0 end
        if curTint == nil then curTint = 0 end

        props.is_raw = isRaw
        props.file_ext = fileExt

        local chosen_model = "meta/llama-3.2-11b-vision-instruct"

        local result, err = task_runner:analyze(preview_path, {
            mode = "full",
            use_cloud = true,
            cloud_model = chosen_model,
            intensity = "normal",
            is_raw = isRaw,
            original_ext = fileExt,
            current_temp = curTemp,
            current_tint = curTint,
        })

        isDone = true

        if preview_path then
            export:cleanup({ preview_path })
            preview_path = nil
        end

        if result then
            props.progress_number_display = "[ 100% ]"
            props.progress_stage_text = "Hoàn tất"
            props.analysis_result = result
            props.raw_ai_adjustments = result.adjustments
            props.status_text = "✓ Hoàn tất"

            if result.scene then
                props.detected_scene = translateScene(result.scene)
            end
            if result.confidence then
                local c = (tonumber(result.confidence) or 0) * 100
                props.confidence_text = string.format("%.0f%%", c)
            end

            self:updateUIWithAdjustments(result.adjustments or {}, props)

            logger:info("AIthleewFree: Phân tích thành công cho ảnh: " .. photo:getFormattedMetadata("fileName"))
        else
            props.progress_number_display = "[ 0% ]"
            props.progress_stage_text = "❌ Thất bại: " .. tostring(err or "Không xác định")
            props.status_text = "Lỗi phân tích: " .. (err or "Không xác định")
            logger:error("Phân tích thất bại: " .. (err or "unknown"))
            LrDialogs.message("Lỗi phân tích AI", "Không thể hoàn thành phân tích: " .. tostring(err))
        end

        props.is_analyzing = false
    end)
end

function Panel:applyAdjustments(photo, adjuster, props)
    if not props.analysis_result or not props.analysis_result.adjustments then
        LrDialogs.message("Chưa có dữ liệu", "Vui lòng chờ AI hoàn tất phân tích trước khi áp dụng.")
        return
    end

    local adjustments = props.analysis_result.adjustments
    adjustments.is_raw = props.is_raw

    LrTasks.startAsyncTask(function()
        props.progress_number_display = "[ 50% ]"
        props.progress_stage_text = "Đang áp dụng thông số màu vào ảnh..."
        props.status_text = "Đang áp dụng thông số màu vào ảnh..."

        local catalog = LrApplication.activeCatalog()
        local targetPhoto = catalog:getTargetPhoto() or photo

        local ok, err = adjuster:applyColors(targetPhoto, adjustments)
        if ok then
            props.progress_number_display = "[ 100% ]"
            props.progress_stage_text = "Hoàn tất"
            props.status_text = "✓ Hoàn tất"
            logger:info("AIthleewFree: Đã áp dụng thông số vào ảnh: " .. targetPhoto:getFormattedMetadata("fileName"))
            LrDialogs.showBezel("✓ Đã áp dụng màu sắc thành công!")
        else
            props.progress_number_display = "[ 0% ]"
            props.progress_stage_text = "Lỗi áp dụng: " .. tostring(err)
            props.status_text = "Lỗi áp dụng: " .. tostring(err)
            logger:error("AIthleewFree: Không thể áp dụng thông số: " .. tostring(err))
            LrDialogs.showError("Không thể áp dụng thông số: " .. tostring(err))
        end
    end)
end

return Panel
