--[[
    AIthleewFree - TetherPanel
    Giao diện Panel điều khiển FTP Tether (Free Edition - Dùng thử 1 tiếng):
    - Đếm ngược thời gian dùng thử 1 tiếng (60 phút).
    - Chỉ tính giờ khi Server thực sự đang BẬT. Khi tắt Server, thời gian tạm dừng đếm.
    - Tự động dừng Server và khóa nút Start khi hết tổng cộng 60 phút hoạt động.
]]

local LrView = import "LrView"
local LrBinding = import "LrBinding"
local LrDialogs = import "LrDialogs"
local LrTasks = import "LrTasks"
local LrFunctionContext = import "LrFunctionContext"
local LrColor = import "LrColor"
local LrPathUtils = import "LrPathUtils"
local LrFileUtils = import "LrFileUtils"

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
local Json = loadModule("Utils/Json.lua")
local Config = loadModule("Utils/Config.lua")
local TetherServer = loadModule("TetherServer.lua")

local logger = Logger:getLogger("TetherPanel")

local TetherPanel = {}
TetherPanel.__index = TetherPanel

local function formatPhotoCount(count)
    local num = math.floor(tonumber(count) or 0)
    return string.format("%d ảnh", num)
end

local function formatRemainingTime(seconds, isRunning)
    if seconds <= 0 then
        return "❌ Đã hết 1 tiếng dùng thử Tether"
    end
    local mins = math.floor(seconds / 60)
    local secs = seconds % 60
    if isRunning then
        return string.format("⏱️ Đang chạy: Còn lại %02d:%02d phút (Dùng thử Free 1 tiếng)", mins, secs)
    else
        return string.format("⏱️ Đang tạm dừng: Còn lại %02d:%02d phút (Chỉ tính giờ khi Bật)", mins, secs)
    end
end

local function updateDynamicGuides(props)
    local portNum = tonumber(props.port) or 2121
    local canonPort = string.format("%05d", portNum)
    props.canon_port_display = canonPort
    
    local curIp = (props.ip and props.ip ~= "Chưa khởi động" and props.ip ~= "Chưa bật server" and props.ip ~= "—") and props.ip or "IP_LAN"
    local profile = props.camera_profile or "sony_a7iv"

    local guides = {
        sony_a7iv = string.format("Sony A7 IV / A7C II / A7R V: MENU → Network → FTP Transfer → Host = %s · Port = %d · Dir Hierarchy = Same (Firmware 6.01+)", curIp, portNum),
        sony_a7iii = string.format("Sony A7 III / A7R III: MENU → Network → FTP Transfer → Host = %s · Port = %d · Dir Hierarchy = Same", curIp, portNum),
        canon_r5 = string.format("Canon EOS R5 / R8: MENU → Wi-Fi/Bluetooth → Transfer to FTP → Address = %s · Port = %s · Passive = Enable", curIp, canonPort),
        canon_r6mk2 = string.format("Canon R6 Mark II / R6: MENU → Wi-Fi/Bluetooth → Transfer to FTP → Address = %s · Port = %s · Passive = Enable", curIp, canonPort),
        nikon_z6ii = string.format("Nikon Z6 II / Z7 II: MENU → Network Menu → Transfer/Send → FTP → Host = %s · Port = %d · Passive = ON", curIp, portNum),
        nikon_z8 = string.format("Nikon Z8 / Z9: MENU → Network Menu → Transfer/Send → FTP → Host = %s · Port = %d", curIp, portNum),
        fujifilm_xt5 = string.format("Fujifilm X-T5 / X-H2: MENU → Network → PC Connection → Wi-Fi FTP → Host = %s · Port = %d", curIp, portNum),
        panasonic_s5ii = string.format("Panasonic Lumix S5 II / S5 IIX: MENU → Network → PC Save → Wi-Fi FTP → Host = %s · Port = %d", curIp, portNum),
    }

    props.guide_text = guides[profile] or string.format("Host = %s · Port = %d (Canon: %s)", curIp, portNum, canonPort)
end

function TetherPanel:show(context)
    local tether = TetherServer:new()
    local props = LrBinding.makePropertyTable(context)
    local f = LrView.osFactory()

    local initialStatus = tether:getStatus()
    local liveIp = tether:getLiveLanIp()
    local remainingSec, isExpired = tether:getTrialRemainingSeconds(initialStatus.running)

    props.trial_expired = isExpired
    props.server_running = initialStatus.running or false
    props.trial_time_text = formatRemainingTime(remainingSec, props.server_running)

    local effectiveIp = "Chưa kết nối Wi-Fi"
    if liveIp and liveIp ~= "" and not liveIp:match("^127%.") and liveIp ~= "Chưa kết nối Wi-Fi" then
        effectiveIp = liveIp
    elseif initialStatus.ip and initialStatus.ip ~= "" and not initialStatus.ip:match("^127%.") and initialStatus.ip ~= "Chưa kết nối Wi-Fi" then
        effectiveIp = initialStatus.ip
    end
    props.ip = effectiveIp
    props.port = initialStatus.port or "2121"
    props.canon_port_display = string.format("%05d", tonumber(props.port) or 2121)
    props.username = initialStatus.username or "a7"
    props.password = initialStatus.password or "12345678"
    props.files_received = initialStatus.files_received or 0
    props.files_received_display = formatPhotoCount(props.files_received)
    props.last_file = initialStatus.last_file or "Chưa có ảnh"
    props.camera_profile = "sony_a7iv"
    props.status_badge = props.server_running and "🟢 SERVER ĐANG CHẠY" or "⚪ SERVER ĐANG TẮT"
    props.status_color = props.server_running and LrColor(0.0, 0.7, 0.3) or LrColor(0.5, 0.5, 0.5)
    props.error_msg = ""
    props.console_output = tether:getConsoleLog(50)
    props.auto_poll_active = true
    props.can_start = (not props.server_running) and (not isExpired)
    props.can_edit = not props.server_running

    updateDynamicGuides(props)

    props:addObserver("camera_profile", function(propertyTable, key, value)
        updateDynamicGuides(props)
    end)
    props:addObserver("port", function(propertyTable, key, value)
        updateDynamicGuides(props)
    end)
    props:addObserver("ip", function(propertyTable, key, value)
        updateDynamicGuides(props)
    end)

    props:addObserver("server_running", function(propertyTable, key, value)
        props.can_edit = not value
        props.can_start = (not value) and (not props.trial_expired)
        local rem, exp = tether:getTrialRemainingSeconds(value)
        props.trial_time_text = formatRemainingTime(rem, value)
        if value then
            props.status_badge = "🟢 SERVER ĐANG CHẠY"
            props.status_color = LrColor(0.0, 0.7, 0.3)
        else
            props.status_badge = "⚪ SERVER ĐANG TẮT"
            props.status_color = LrColor(0.5, 0.5, 0.5)
        end
    end)

    -- Poller cập nhật trạng thái & đếm ngược trial mỗi 2 giây
    LrTasks.startAsyncTask(function()
        while props.auto_poll_active do
            LrTasks.sleep(2.0)
            LrFunctionContext.callWithContext("TetherPollFree", function(ctx)
                if props.auto_poll_active then
                    local rem, exp = tether:getTrialRemainingSeconds(props.server_running)
                    props.trial_expired = exp
                    props.trial_time_text = formatRemainingTime(rem, props.server_running)
                    props.can_start = (not props.server_running) and (not exp)

                    -- Kiểm tra hết thời gian dùng thử khi server đang chạy
                    if exp and props.server_running then
                        tether:stop(props.port)
                        props.server_running = false
                        props.can_edit = false
                        props.can_start = false
                        props.status_badge = "⚪ SERVER ĐÃ DỪNG (HẾT HẠN TRIAL)"
                        props.status_color = LrColor(0.8, 0.2, 0.2)
                        props.error_msg = "🎁 Đã hết 1 tiếng dùng thử Tether Free. Nâng cấp Pro để sử dụng không giới hạn."
                        LrDialogs.message(
                            "Hết thời gian dùng thử",
                            "🎁 Bạn đã sử dụng hết 1 tiếng dùng thử tính năng Tether FTP trên AIthleewFree.\n\nVui lòng nâng cấp lên bản AIthleewPro để sử dụng không giới hạn thời gian."
                        )
                    end

                    local status = tether:getStatus()
                    local curLiveIp = tether:getLiveLanIp()
                    if status then
                        props.server_running = status.running
                        props.files_received = status.files_received or 0
                        props.files_received_display = formatPhotoCount(props.files_received)
                        if status.last_file and status.last_file ~= "" then
                            props.last_file = status.last_file
                        end
                        if curLiveIp and curLiveIp ~= "" and not curLiveIp:match("^127%.") then
                            props.ip = curLiveIp
                        elseif status.ip and status.ip ~= "" and not status.ip:match("^127%.") then
                            props.ip = status.ip
                        end
                        updateDynamicGuides(props)
                        props.console_output = tether:getConsoleLog(50)
                    end
                end
            end)
        end
    end)

    local PANEL_WIDTH = 800
    local BOX_WIDTH = 780
    local ROW_WIDTH = 756

    local contents = f:column {
        bind_to_object = props,
        spacing = 6,
        width = PANEL_WIDTH,
        fill_horizontal = true,

        -- 1. Header Banner + Timer Countdown
        f:row {
            spacing = 15,
            width = BOX_WIDTH,
            fill_horizontal = true,
            f:static_text {
                title = "📡 TETHER (FTP) — BẮN ẢNH KHÔNG DÂY (DÙNG THỬ 1 TIẾNG)",
                font = "<system/bold>",
                text_color = LrColor(0.1, 0.5, 0.9),
                fill_horizontal = true,
            },
            f:static_text {
                title = LrView.bind "status_badge",
                font = "<system/bold>",
                text_color = LrView.bind "status_color",
            },
        },

        f:row {
            spacing = 10,
            width = BOX_WIDTH,
            f:static_text {
                title = LrView.bind "trial_time_text",
                font = "<system/bold>",
                text_color = LrColor(0.85, 0.35, 0.1),
                width = 460,
            },
            f:push_button {
                title = "⭐ Nâng cấp lên Pro (Không giới hạn)",
                action = function()
                    LrDialogs.message(
                        "Nâng cấp AIthleewPro",
                        "Phiên bản Pro cho phép:\n" ..
                        "- Sử dụng Tether FTP bắn ảnh không giới hạn thời gian\n" ..
                        "- Tự động đổi tên và phân loại theo mã máy ảnh\n" ..
                        "- Tích hợp toàn diện với các mô hình Vision AI đỉnh cao."
                    )
                end,
            },
        },

        f:separator { width = BOX_WIDTH, fill_horizontal = true },

        -- 2. KHU VỰC 1: THIẾT LẬP KẾT NỐI & ĐIỀU KHIỂN
        f:group_box {
            title = "1. CẤU HÌNH KẾT NỐI & ĐIỀU KHIỂN SERVER",
            width = BOX_WIDTH,
            fill_horizontal = true,
            spacing = 6,

            -- Hàng 1: Nút Bật/Tắt & Thông tin IP/Port
            f:row {
                spacing = 10,
                width = ROW_WIDTH,
                fill_horizontal = true,
                f:push_button {
                    title = "▶ Khởi động FTP Server",
                    font = "<system/bold>",
                    enabled = LrView.bind "can_start",
                    width = 180,
                    action = function()
                        props.error_msg = ""
                        props.status_badge = "🟡 ĐANG KHỞI ĐỘNG..."
                        props.status_color = LrColor(0.9, 0.6, 0.0)
                        LrTasks.startAsyncTask(function()
                            props.console_output = tether:getConsoleLog(50)
                            local ok, err = tether:start({
                                port = props.port,
                                username = props.username,
                                password = props.password,
                                camera_profile = props.camera_profile,
                            })
                            props.console_output = tether:getConsoleLog(50)
                            if ok then
                                props.server_running = true
                                props.can_edit = false
                                props.error_msg = ""
                                local s = tether:getStatus()
                                if s.ip then props.ip = s.ip end
                                props.status_badge = "🟢 SERVER ĐANG CHẠY"
                                props.status_color = LrColor(0.0, 0.7, 0.3)
                                updateDynamicGuides(props)
                                LrDialogs.showBezel("✓ FTP Server đã sẵn sàng nhận ảnh! (Bắt đầu tính giờ)")
                            else
                                props.server_running = false
                                props.can_edit = true
                                props.status_badge = "⚪ SERVER ĐANG TẮT"
                                props.status_color = LrColor(0.5, 0.5, 0.5)
                                props.error_msg = "❌ Khởi động thất bại. " .. tostring(err or "")
                            end
                        end)
                    end,
                },
                f:push_button {
                    title = "⏹ Dừng Server",
                    font = "<system/bold>",
                    enabled = LrView.bind "server_running",
                    width = 110,
                    action = function()
                        LrTasks.startAsyncTask(function()
                            tether:stop(props.port)
                            props.server_running = false
                            props.can_edit = true
                            props.ip = tether:getLiveLanIp() or "127.0.0.1"
                            props.status_badge = "⚪ SERVER ĐANG TẮT"
                            props.status_color = LrColor(0.5, 0.5, 0.5)
                            updateDynamicGuides(props)
                            props.console_output = tether:getConsoleLog(50)
                            LrDialogs.showBezel("⏹ Đã dừng FTP Server. (Đã tạm dừng đếm ngược)")
                        end)
                    end,
                },
                f:static_text { title = "IP LAN:", font = "<system/bold>" },
                f:static_text {
                    title = LrView.bind "ip",
                    font = "<system/bold>",
                    text_color = LrColor(0.0, 0.6, 0.2),
                    width = 130,
                },
                f:static_text { title = "Port:", font = "<system/bold>" },
                f:edit_field {
                    value = LrView.bind "port",
                    width = 50,
                    enabled = LrView.bind "can_edit",
                },
                f:static_text { title = "Canon (5 số):", font = "<system/bold>" },
                f:static_text {
                    title = LrView.bind "canon_port_display",
                    font = "<system/bold>",
                    text_color = LrColor(0.8, 0.2, 0.2),
                    width = 50,
                },
            },

            -- Hàng 2: User/Pass
            f:row {
                spacing = 10,
                width = ROW_WIDTH,
                fill_horizontal = true,
                f:static_text { title = "Tài khoản (User):", width = 110 },
                f:edit_field {
                    value = LrView.bind "username",
                    width = 110,
                    enabled = LrView.bind "can_edit",
                },
                f:static_text { title = "Mật khẩu (Pass):", width = 100 },
                f:edit_field {
                    value = LrView.bind "password",
                    width = 110,
                    enabled = LrView.bind "can_edit",
                },
            },

            -- Hàng 3: Chọn máy ảnh & Hướng dẫn
            f:row {
                spacing = 10,
                width = ROW_WIDTH,
                fill_horizontal = true,
                f:static_text { title = "Dòng máy ảnh:", width = 110, font = "<system/bold>" },
                f:popup_menu {
                    value = LrView.bind "camera_profile",
                    items = {
                        { value = "sony_a7iv", title = "Sony A7 IV / A7C II / A7R V" },
                        { value = "sony_a7iii", title = "Sony A7 III / A7R III" },
                        { value = "canon_r5", title = "Canon EOS R5 / R8" },
                        { value = "canon_r6mk2", title = "Canon R6 Mark II / R6" },
                        { value = "nikon_z6ii", title = "Nikon Z6 II / Z7 II" },
                        { value = "nikon_z8", title = "Nikon Z8 / Z9" },
                        { value = "fujifilm_xt5", title = "Fujifilm X-T5 / X-H2" },
                        { value = "panasonic_s5ii", title = "Panasonic Lumix S5 II / S5 IIX" },
                    },
                    enabled = LrView.bind "can_edit",
                    fill_horizontal = true,
                },
            },
            f:row {
                width = ROW_WIDTH,
                fill_horizontal = true,
                f:static_text {
                    title = LrView.bind "guide_text",
                    font = "<system/small>",
                    text_color = LrColor(0.1, 0.4, 0.8),
                    fill_horizontal = true,
                },
            },
        },

        -- 3. KHU VỰC 2: TIẾN ĐỘ NHẬN ẢNH
        f:group_box {
            title = "2. TIẾN ĐỘ NHẬN ẢNH & AUTO IMPORT",
            width = BOX_WIDTH,
            fill_horizontal = true,
            spacing = 6,

            f:row {
                spacing = 12,
                width = ROW_WIDTH,
                fill_horizontal = true,
                f:static_text { title = "Số ảnh đã nhận:", font = "<system/bold>" },
                f:static_text {
                    title = LrView.bind "files_received_display",
                    font = "<system/bold>",
                    text_color = LrColor(0.9, 0.4, 0.0),
                    width = 85,
                },
                f:static_text { title = "Ảnh mới nhất:", font = "<system/bold>" },
                f:static_text {
                    title = LrView.bind "last_file",
                    font = "<system/bold>",
                    fill_horizontal = true,
                },
            },
            f:row {
                spacing = 6,
                width = ROW_WIDTH,
                fill_horizontal = true,
                f:static_text {
                    title = "📁 Watched Folder:",
                    font = "<system/small>",
                    text_color = LrColor(0.3, 0.3, 0.3),
                },
                f:static_text {
                    title = "~/AIthleewTether/1-inbox",
                    font = "<system/small>",
                    text_color = LrColor(0.1, 0.4, 0.8),
                },
            },
        },

        -- 4. KHU VỰC 3: CONSOLE
        f:group_box {
            title = "3. CONSOLE HOẠT ĐỘNG (Live Stream)",
            width = BOX_WIDTH,
            fill_horizontal = true,
            spacing = 5,

            f:row {
                width = ROW_WIDTH,
                fill_horizontal = true,
                f:push_button {
                    title = "📂 Mở thư mục Tether",
                    action = function()
                        tether:openFolder()
                    end,
                },
                f:push_button {
                    title = "🗑️ Xóa Console",
                    action = function()
                        tether:clearConsole()
                        props.console_output = tether:getConsoleLog(50)
                    end,
                },
                f:push_button {
                    title = "🔄 Làm mới",
                    action = function()
                        props.console_output = tether:getConsoleLog(50)
                    end,
                },
            },

            f:scrolled_view {
                width = ROW_WIDTH,
                height = 160,
                f:static_text {
                    title = LrView.bind "console_output",
                    font = "<system/small>",
                    text_color = LrColor(0.1, 0.1, 0.1),
                    width = ROW_WIDTH - 25,
                    fill_horizontal = true,
                },
            },
        },

        -- Báo lỗi nếu có
        f:row {
            width = BOX_WIDTH,
            fill_horizontal = true,
            f:static_text {
                title = LrView.bind "error_msg",
                text_color = LrColor(0.9, 0.1, 0.1),
                font = "<system/small>",
                fill_horizontal = true,
            },
        },
    }

    local res = LrDialogs.presentModalDialog {
        title = "AIthleewFree — Tether (FTP)",
        contents = contents,
        actionVerb = "Ẩn xuống chạy nền",
        cancelVerb = "Dừng Server & Đóng",
    }

    props.auto_poll_active = false

    if res == "cancel" then
        LrTasks.startAsyncTask(function()
            tether:stop(props.port)
            LrDialogs.showBezel("⏹ Đã dừng FTP Server.")
        end)
    end
end

return TetherPanel
