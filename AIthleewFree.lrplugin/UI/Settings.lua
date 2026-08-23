--[[
    AIthleewFree - Settings UI (Cài đặt)
    Cấu hình kết nối Cloud Vision AI cho phiên bản Free:
    - Khóa chọn model: Chỉ dùng duy nhất mô hình Meta Llama 3.2 11B Vision Instruct.
    - Cấu hình NVIDIA NIM API Key & Test Connection.
    - Cấu hình đường dẫn Python.
]]

local LrDialogs = import "LrDialogs"
local LrView = import "LrView"
local LrBinding = import "LrBinding"
local LrFunctionContext = import "LrFunctionContext"
local LrTasks = import "LrTasks"
local LrColor = import "LrColor"
local LrPathUtils = import "LrPathUtils"

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
local Config = loadModule("Utils/Config.lua")

local logger = Logger:getLogger("Settings")

local Settings = {}
Settings.__index = Settings

function Settings:show(context)
    Config:load()
    local config = Config:getAll()

    local props = LrBinding.makePropertyTable(context)

    props.socket_host = config.socket_host or "127.0.0.1"
    props.socket_port = config.socket_port or 9876
    props.python_path = config.python_path or "python3"
    props.preferred_cloud_model = "meta/llama-3.2-11b-vision-instruct"

    local envNv = ""
    if type(os) == "table" and type(os.getenv) == "function" then
        pcall(function()
            envNv = os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_NIM_API_KEY") or ""
        end)
    end

    props.nvidia_api_key = config.nvidia_api_key or envNv or ""
    props.status_text = ""
    props.test_nv_status = "Chưa kiểm tra NVIDIA NIM"
    props.is_testing_nv = false

    local f = LrView.osFactory()
    local dialog_contents = f:column {
        bind_to_object = props,
        spacing = f:control_spacing(),
        width = 650,

        f:row {
            f:static_text {
                title = "⚙️ CÀI ĐẶT HỆ THỐNG — AITHLEEW FREE",
                font = "<system/bold>",
                text_color = LrColor(0.1, 0.5, 0.9),
                size = "large",
            },
        },

        f:separator { title = "1. MÔ HÌNH CLOUD VISION AI (FREE EDITION)" },

        f:row {
            f:static_text {
                title = "Mô hình AI:",
                width = 130,
                font = "<system/bold>",
            },
            f:static_text {
                title = "🌟 [NVIDIA NIM] Meta Llama 3.2 11B Vision Instruct (Mặc định bản Free)",
                font = "<system/bold>",
                text_color = LrColor(0.15, 0.65, 0.25),
                width = 500,
            },
        },
        f:row {
            f:static_text {
                title = "💡 Lưu ý:",
                width = 130,
                font = "<system/small>",
                text_color = LrColor(0.5, 0.5, 0.5),
            },
            f:static_text {
                title = "Bản Free chỉ hỗ trợ 1 mô hình Vision AI tiêu chuẩn. Nâng cấp Pro để mở khóa 30+ mô hình khác.",
                font = "<system/small>",
                text_color = LrColor(0.5, 0.5, 0.5),
                width = 500,
            },
        },

        f:separator { title = "2. KHÓA API & KIỂM TRA KẾT NỐI (NVIDIA NIM)" },

        f:static_text {
            title = "🟢 Mã khóa NVIDIA NIM API Key (nvapi-...):",
            font = "<system/bold>",
            text_color = LrColor(0.15, 0.65, 0.25),
        },
        f:edit_field {
            value = LrView.bind "nvidia_api_key",
            width = 630,
            font = "<system/small>",
            immediate = true,
        },
        f:row {
            spacing = 10,
            f:push_button {
                title = "🟢  Test Kết Nối NVIDIA NIM",
                width = 240,
                font = "<system/bold>",
                action = function()
                    self:testNvidiaConnection(props)
                end,
            },
            f:static_text {
                title = LrView.bind "test_nv_status",
                width = 380,
                height_in_lines = 2,
                font = "<system/small>",
            },
        },

        f:separator { title = "3. MÔI TRƯỜNG PYTHON" },

        f:row {
            f:static_text {
                title = "Đường dẫn Python:",
                width = 130,
            },
            f:edit_field {
                value = LrView.bind "python_path",
                width = 500,
            },
        },

        f:separator { fill_horizontal = 1 },

        -- Status & Reset
        f:row {
            f:static_text {
                title = LrView.bind "status_text",
                font = "<system/bold>",
                text_color = LrColor(0.15, 0.65, 0.25),
                width = 410,
            },
            f:push_button {
                title = "↺  Khôi phục mặc định",
                width = 210,
                action = function()
                    self:resetSettings(props)
                end,
            },
        },
    }

    local dlgResult = LrDialogs.presentModalDialog({
        title = "AIthleewFree - Cài Đặt Hệ Thống",
        contents = dialog_contents,
        actionVerb = "💾  LƯU CÀI ĐẶT",
        cancelVerb = "Đóng",
    })

    if dlgResult == "ok" then
        self:saveSettings(props)
    end

    logger:info("Free Settings dialog closed")
end

function Settings:testNvidiaConnection(props)
    if props.is_testing_nv then return end
    props.is_testing_nv = true
    props.test_nv_status = "⏳ Đang kết nối NVIDIA NIM..."

    local apiKey = props.nvidia_api_key or ""
    if apiKey == "" then
        props.test_nv_status = "❌ Chưa nhập NVIDIA NIM API Key (nvapi-...)"
        props.is_testing_nv = false
        return
    end

    local model = "meta/llama-3.2-11b-vision-instruct"

    LrTasks.startAsyncTask(function()
        local TaskRunner = loadModule("Bridge/TaskRunner.lua")
        local tr = TaskRunner:new({ python_path = props.python_path })
        local ok, res = tr:test_connection(apiKey, model)

        if ok and res and res.status == "ok" then
            local ms = res.latency_ms or 0
            local mName = res.model or model
            props.test_nv_status = string.format("✓ [NVIDIA NIM] Kết nối tốt (%dms) — %s", ms, mName)
        else
            local errStr = (res and (res.error or res.message)) or "Không thể kết nối đến NVIDIA NIM."
            props.test_nv_status = "❌ [NVIDIA NIM] Thất bại: " .. tostring(errStr)
        end

        props.is_testing_nv = false
    end)
end

function Settings:saveSettings(props)
    local values = {
        socket_host = props.socket_host,
        socket_port = tonumber(props.socket_port) or 9876,
        python_path = props.python_path,
        use_cloud = true,
        preferred_cloud_model = "meta/llama-3.2-11b-vision-instruct",
        custom_cloud_model = "",
        nvidia_api_key = props.nvidia_api_key,
        openrouter_api_key = "",
        kilo_api_key = "",
        preview_size = 1024,
        cache_results = false,
        auto_analyze_on_select = false,
        log_level = "INFO",
    }

    Config:setAll(values)
    local saved = Config:save()

    if saved then
        props.status_text = "✓ Đã lưu cài đặt thành công (" .. os.date("%H:%M:%S") .. ")"
        logger:info("AIthleewFree: Settings saved successfully")
    else
        props.status_text = "Lỗi khi lưu cài đặt!"
        logger:error("AIthleewFree: Failed to save settings")
    end
end

function Settings:resetSettings(props)
    local confirmed = LrDialogs.confirm(
        "Khôi phục mặc định?",
        "Tất cả cài đặt sẽ trở về giá trị ban đầu của AIthleewFree. Bạn có chắc chắn?",
        "Khôi phục",
        "Hủy"
    )

    if confirmed ~= "ok" then return end

    Config:reset()
    local config = Config:getAll()

    props.socket_host = config.socket_host or "127.0.0.1"
    props.socket_port = config.socket_port or 9876
    props.python_path = config.python_path or "python3"
    props.preferred_cloud_model = "meta/llama-3.2-11b-vision-instruct"
    props.nvidia_api_key = ""
    props.test_nv_status = "Chưa kiểm tra NVIDIA NIM"
    props.status_text = "Đã khôi phục cài đặt mặc định"

    logger:info("AIthleewFree: Settings reset to defaults")
end

return Settings

