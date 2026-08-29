--[[
    AIthleewFree - Plugin Manager Info Provider
    Bảng hiển thị trạng thái hệ thống Read-Only Dashboard trong Plugin Manager cho AIthleewFree.
]]

local LrView = import "LrView"
local LrBinding = import "LrBinding"
local LrDialogs = import "LrDialogs"
local LrTasks = import "LrTasks"
local LrColor = import "LrColor"
local LrPathUtils = import "LrPathUtils"
local LrFunctionContext = import "LrFunctionContext"

local pluginDir = (_PLUGIN and _PLUGIN.path) or LrPathUtils.child(LrPathUtils.getStandardFilePath("appData"), "Modules/AIthleewFree.lrplugin")
if not LrPathUtils.isAbsolute(pluginDir) or not LrPathUtils.child(pluginDir, "Info.lua") then
    local fallback = LrPathUtils.child(LrPathUtils.getStandardFilePath("appData"), "Modules/AutoColorFree.lrplugin")
    if LrPathUtils.isAbsolute(fallback) then pluginDir = fallback end
end
local function loadModule(modulePath)
    local fullPath = LrPathUtils.child(pluginDir, modulePath)
    local chunk, err = loadfile(fullPath)
    if chunk then return chunk() else error("Failed to load: " .. modulePath .. " - " .. tostring(err)) end
end

local Logger = loadModule("Utils/Logger.lua")
local Config = loadModule("Utils/Config.lua")
local TaskRunner = loadModule("Bridge/TaskRunner.lua")
local TetherServer = loadModule("TetherServer.lua")

local logger = Logger:getLogger("PluginManagerProvider")

local function maskApiKey(key)
    if not key or key == "" then
        return "⚠️ Chưa thiết lập API Key"
    end
    if #key <= 12 then
        return string.sub(key, 1, 4) .. "..."
    end
    local prefix = string.sub(key, 1, 8)
    local suffix = string.sub(key, -4)
    return prefix .. "..." .. suffix .. string.format(" (%d ký tự)", #key)
end

return {
    startDialog = function(propertyTable)
        Config:load()
        local config = Config:getAll()

        propertyTable.plugin_name_display = "AIthleewFree (Basic Edition)"
        propertyTable.plugin_version = "2.0 (Free)"
        propertyTable.website = "https://aithleewpro.vercel.app/"
        propertyTable.model_display = "meta/llama-3.2-11b-vision-instruct"

        local nvKey = config.nvidia_api_key or ""
        propertyTable.nv_key_masked = maskApiKey(nvKey)
        propertyTable.provider_display = (nvKey ~= "") and "NVIDIA NIM Cloud API" or "Chưa kích hoạt"

        propertyTable.python_path = config.python_path or "python3"
        propertyTable.python_engine_status = "⏳ Đang kiểm tra..."

        -- Tether Status Fields
        local tether = TetherServer:new()
        local tStatus = tether:getStatus()
        local remSec, isExp = tether:getTrialRemainingSeconds(tStatus.running)
        propertyTable.tether_running = tStatus.running or false
        propertyTable.tether_status_text = propertyTable.tether_running and "🟢 Đang hoạt động (Online)" or "⚪ Đang tắt (Offline)"
        propertyTable.tether_status_color = propertyTable.tether_running and LrColor(0.0, 0.7, 0.3) or LrColor(0.5, 0.5, 0.5)
        propertyTable.tether_ip = tStatus.ip or "—"
        propertyTable.tether_port = tStatus.port or "2121"
        propertyTable.tether_endpoint = propertyTable.tether_running and (tostring(propertyTable.tether_ip) .. " : " .. tostring(propertyTable.tether_port)) or "— (Chưa bật server)"
        propertyTable.tether_user = tStatus.username or "a7"
        propertyTable.tether_pass = tStatus.password or "12345678"
        propertyTable.tether_credentials = string.format("%s / %s", tostring(propertyTable.tether_user), tostring(propertyTable.tether_pass))
        propertyTable.tether_received = string.format("%d ảnh", math.floor(tonumber(tStatus.files_received) or 0))
        propertyTable.tether_last_file = tStatus.last_file or "Chưa có ảnh"
        propertyTable.tether_trial_info = isExp and "❌ Đã hết 1 tiếng dùng thử" or string.format("⏱️ Dùng thử: %d phút còn lại (Chỉ tính khi bật)", math.floor(remSec / 60))

        LrTasks.startAsyncTask(function()
            local tr = TaskRunner:new({ python_path = propertyTable.python_path })
            local envOk = tr:ensure_process_running()
            if envOk then
                propertyTable.python_engine_status = "🟢 Sẵn sàng (Python 3)"
            else
                propertyTable.python_engine_status = "🟡 Chưa khởi tạo"
            end

            local liveIp = tether:getLiveLanIp()
            if liveIp and liveIp ~= "" and not liveIp:match("^127%.") then
                propertyTable.tether_ip = liveIp
                if propertyTable.tether_running then
                    propertyTable.tether_endpoint = string.format("%s : %s", liveIp, tostring(propertyTable.tether_port))
                end
            end
        end)
    end,

    sectionsForTopOfDialog = function(f, propertyTable)
        return {
            {
                title = "Trạng Thái AI Engine & Cloud API (Free Edition)",
                synopsis = "Xem trạng thái hệ thống phiên bản AIthleewFree",
                f:column {
                    bind_to_object = propertyTable,
                    spacing = 8,
                    fill_horizontal = true,

                    f:row {
                        f:static_text {
                            title = "Phiên bản Plugin:",
                            width = 140,
                            font = "<system/bold>",
                        },
                        f:static_text {
                            title = LrView.bind "plugin_version",
                            font = "<system/bold>",
                            text_color = LrColor(0.1, 0.5, 0.9),
                            fill_horizontal = true,
                        },
                    },

                    f:row {
                        f:static_text {
                            title = "Website chính thức:",
                            width = 140,
                            font = "<system/bold>",
                        },
                        f:static_text {
                            title = LrView.bind "website",
                            font = "<system/bold>",
                            text_color = LrColor(0.15, 0.5, 0.85),
                            fill_horizontal = true,
                        },
                    },

                    f:row {
                        f:static_text {
                            title = "Python Engine:",
                            width = 140,
                            font = "<system/bold>",
                        },
                        f:static_text {
                            title = LrView.bind "python_engine_status",
                            font = "<system/bold>",
                            fill_horizontal = true,
                        },
                    },

                    f:row {
                        f:static_text {
                            title = "Mô hình Cloud AI:",
                            width = 140,
                            font = "<system/bold>",
                        },
                        f:static_text {
                            title = LrView.bind "model_display",
                            font = "<system/bold>",
                            text_color = LrColor(0.15, 0.65, 0.25),
                            fill_horizontal = true,
                        },
                    },

                    f:row {
                        f:static_text {
                            title = "NVIDIA NIM Key:",
                            width = 140,
                            font = "<system/bold>",
                        },
                        f:static_text {
                            title = LrView.bind "nv_key_masked",
                            font = "<system/small>",
                            fill_horizontal = true,
                        },
                    },
                },
            },

            {
                title = "Trạng Thái Tether FTP (Dùng thử 1 tiếng)",
                synopsis = "Trạng thái kết nối Tether FTP trên bản Free (Chỉ tính giờ khi bật)",
                f:column {
                    bind_to_object = propertyTable,
                    spacing = 6,
                    fill_horizontal = true,

                    f:row {
                        f:static_text { title = "Trạng thái Server:", width = 140, font = "<system/bold>" },
                        f:static_text {
                            title = LrView.bind "tether_status_text",
                            font = "<system/bold>",
                            text_color = LrView.bind "tether_status_color",
                            fill_horizontal = true,
                        },
                    },
                    f:row {
                        f:static_text { title = "Thời gian dùng thử:", width = 140, font = "<system/bold>" },
                        f:static_text {
                            title = LrView.bind "tether_trial_info",
                            font = "<system/bold>",
                            text_color = LrColor(0.85, 0.35, 0.1),
                            fill_horizontal = true,
                        },
                    },
                    f:row {
                        f:static_text { title = "Địa chỉ kết nối:", width = 140, font = "<system/bold>" },
                        f:static_text {
                            title = LrView.bind "tether_endpoint",
                            font = "<system/bold>",
                            text_color = LrColor(0.0, 0.6, 0.2),
                            fill_horizontal = true,
                        },
                    },
                    f:row {
                        f:static_text { title = "Ảnh đã nhận:", width = 140, font = "<system/bold>" },
                        f:static_text {
                            title = LrView.bind "tether_received",
                            font = "<system/bold>",
                            text_color = LrColor(0.9, 0.4, 0.0),
                            fill_horizontal = true,
                        },
                    },
                },
            },

            {
                title = "Nhật Ký Cập Nhật (Changelog)",
                synopsis = "Tính năng mới của AIthleewFree phiên bản 2.0.0",
                f:column {
                    bind_to_object = propertyTable,
                    spacing = 6,
                    fill_horizontal = true,

                    f:row {
                        f:static_text {
                            title = "🌟 Phiên bản 2.0.0:",
                            font = "<system/bold>",
                            text_color = LrColor(0.1, 0.5, 0.9),
                            width = 200,
                        },
                    },
                    f:static_text {
                        title = "• 🧠 Nâng cấp Vision AI Model tối ưu phân tích hình ảnh và bối cảnh chuẩn xác.\n" ..
                                "• ☀️ Tự động cân bằng trắng Hybrid & cân chỉnh Tone cơ bản chuẩn xác.\n" ..
                                "• 🎨 Giao diện tinh gọn, tập trung và trực quan hơn.\n" ..
                                "• 🌐 Cập nhật Website chính thức https://aithleewpro.vercel.app/",
                        font = "<system/small>",
                        fill_horizontal = true,
                    },
                },
            },
        }
    end,
}
