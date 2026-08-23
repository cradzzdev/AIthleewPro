--[[
    AIthleewFree - TetherServer
    Điều khiển FTP Server Tethering cho Lightroom Classic (Phiên bản Free - Dùng thử 1 tiếng / 3600s):
    - Giới hạn 1 tiếng (3600s) tổng thời gian server thực sự chạy.
    - Khi BẬT Server: bắt đầu tính giờ tiêu hao.
    - Khi TẮT Server: dừng đếm và lưu lại số giây đã sử dụng (không bị trừ khi tắt).
    - Hết 3600s tự động dừng Server và khóa phiên.
]]

local LrTasks = import "LrTasks"
local LrFileUtils = import "LrFileUtils"
local LrPathUtils = import "LrPathUtils"

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
local Json = loadModule("Utils/Json.lua")

local logger = Logger:getLogger("TetherServer")

local TetherServer = {}
TetherServer.__index = TetherServer

local BASE_TETHER_DIR = LrPathUtils.child(LrPathUtils.getStandardFilePath("home"), "AIthleewTether")
local PID_FILE = LrPathUtils.child(BASE_TETHER_DIR, "tether.pid")
local STATUS_FILE = LrPathUtils.child(BASE_TETHER_DIR, "tether_status.json")
local CONN_FILE = LrPathUtils.child(BASE_TETHER_DIR, "connection.json")
local TRIAL_FILE = LrPathUtils.child(BASE_TETHER_DIR, "tether_free_trial.json")

local MAX_TRIAL_SECONDS = 3600 -- 1 hour (60 minutes)

local function readTextFile(filePath)
    if not filePath or not LrFileUtils.exists(filePath) then return nil end
    local content = nil
    pcall(function()
        local f = io.open(filePath, "r")
        if f then
            content = f:read("*a")
            f:close()
        end
    end)
    return content
end

local function writeTextFile(filePath, text, mode)
    mode = mode or "w"
    local ok = false
    pcall(function()
        local dir = LrPathUtils.parent(filePath)
        if dir and not LrFileUtils.exists(dir) then
            LrFileUtils.createAllDirectories(dir)
        end
        local f = io.open(filePath, mode)
        if f then
            f:write(text)
            f:close()
            ok = true
        end
    end)
    return ok
end

function TetherServer:new()
    local obj = {
        base_dir = BASE_TETHER_DIR,
        inbox_dir = LrPathUtils.child(BASE_TETHER_DIR, "1-inbox"),
        lightroom_dir = LrPathUtils.child(BASE_TETHER_DIR, "2-lightroom"),
    }
    setmetatable(obj, self)
    obj:ensureDirectories()
    return obj
end

function TetherServer:getPythonExecutable()
    Config:load()
    local configPath = Config:get("python_path")
    if configPath and configPath ~= "" and configPath ~= "python3" and configPath ~= "python" then
        if LrFileUtils.exists(configPath) then
            return configPath
        end
    end

    local candidates = {
        "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3",
        "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3",
        "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",
        "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3",
        "/Library/Frameworks/Python.framework/Versions/Current/bin/python3",
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
    }

    local home = nil
    pcall(function() home = LrPathUtils.getStandardFilePath("home") end)
    if home then
        table.insert(candidates, 1, LrPathUtils.child(home, "miniconda3/bin/python3"))
        table.insert(candidates, 1, LrPathUtils.child(home, "anaconda3/bin/python3"))
        table.insert(candidates, 1, LrPathUtils.child(home, ".pyenv/shims/python3"))
    end

    for _, c in ipairs(candidates) do
        if LrFileUtils.exists(c) then
            return c
        end
    end

    return "python3"
end

function TetherServer:getPythonScriptPath()
    local path = LrPathUtils.child(pluginDir, "python_engine/main.py")
    if LrFileUtils.exists(path) then
        return path
    end
    return "python_engine/main.py"
end

function TetherServer:ensureDirectories()
    pcall(function()
        if not LrFileUtils.exists(self.base_dir) then
            LrFileUtils.createAllDirectories(self.base_dir)
        end
        if not LrFileUtils.exists(self.inbox_dir) then
            LrFileUtils.createAllDirectories(self.inbox_dir)
        end
        if not LrFileUtils.exists(self.lightroom_dir) then
            LrFileUtils.createAllDirectories(self.lightroom_dir)
        end
    end)
end

-- Lấy số giây còn lại và trạng thái hết hạn. Chỉ trừ thời gian thực chạy khi server đang online.
function TetherServer:getTrialRemainingSeconds(isRunning)
    local trialContent = readTextFile(TRIAL_FILE)
    if not trialContent or trialContent == "" then
        return MAX_TRIAL_SECONDS, false
    end
    local trialData = Json.decode(trialContent)
    if not trialData then
        return MAX_TRIAL_SECONDS, false
    end

    if trialData.expired then
        return 0, true
    end

    local usedSeconds = tonumber(trialData.used_seconds) or 0

    -- Nếu server đang chạy và có mốc active_since, cộng thêm thời gian chạy trong phiên hiện tại
    if isRunning and trialData.active_since then
        local currentRun = os.time() - tonumber(trialData.active_since)
        if currentRun > 0 then
            usedSeconds = usedSeconds + currentRun
        end
    end

    local remaining = MAX_TRIAL_SECONDS - usedSeconds
    if remaining <= 0 then
        trialData.expired = true
        trialData.used_seconds = MAX_TRIAL_SECONDS
        trialData.active_since = nil
        writeTextFile(TRIAL_FILE, Json.encode(trialData), "w")
        return 0, true
    end

    return remaining, false
end

function TetherServer:start(options)
    local remaining, isExpired = self:getTrialRemainingSeconds(false)
    if isExpired or remaining <= 0 then
        self:appendConsole("❌ Đã hết 1 tiếng dùng thử Tether Free. Vui lòng nâng cấp lên bản Pro để sử dụng không giới hạn.")
        return false, "Trial expired"
    end

    options = options or {}
    local port = options.port or "2121"
    local username = options.username or "a7"
    local password = options.password or "12345678"
    local camera_profile = options.camera_profile or "sony_a7iv"

    local portNum = tonumber(port) or 2121
    if portNum < 1024 or portNum > 65535 then
        portNum = 2121
        port = "2121"
        self:appendConsole("⚠️ Port phải nằm trong khoảng 1024 - 65535 (Đã tự động chuyển về 2121).")
    end

    self:ensureDirectories()

    -- Clean old processes
    pcall(function()
        LrTasks.execute("pkill -9 -f 'python.*tether' 2>/dev/null")
        LrTasks.execute(string.format("/usr/sbin/lsof -ti :%s | xargs kill -9 2>/dev/null", tostring(port)))
    end)
    if LrFileUtils.exists(PID_FILE) then
        pcall(function() LrFileUtils.delete(PID_FILE) end)
    end
    writeTextFile(CONN_FILE, Json.encode({ status = "starting", port = tonumber(port) or 2121 }), "w")
    if LrTasks.canYield() then
        LrTasks.sleep(0.3)
    end

    -- Bắt đầu tính giờ chạy cho phiên này
    local trialContent = readTextFile(TRIAL_FILE)
    local trialData = (trialContent and trialContent ~= "") and Json.decode(trialContent) or {}
    if not trialData then trialData = {} end
    trialData.used_seconds = tonumber(trialData.used_seconds) or 0
    trialData.active_since = os.time()
    trialData.expired = false
    writeTextFile(TRIAL_FILE, Json.encode(trialData), "w")

    local pyExe = self:getPythonExecutable()
    local mainPy = self:getPythonScriptPath()
    local logPath = LrPathUtils.child(self.base_dir, "tether_server.log")
    local launcherScript = LrPathUtils.child(self.base_dir, "launch_ftp.sh")

    writeTextFile(logPath, "", "w")

    self:appendConsole(string.format("⚙️ AIthleewFree Môi trường: Python=%s", pyExe))
    self:appendConsole(string.format("🚀 Khởi chạy Free Tether trên Port %s (User: %s)...", tostring(port), tostring(username)))

    local scriptBody = string.format([[#!/bin/bash
export PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin:/Library/Frameworks/Python.framework/Versions/3.13/bin:/Library/Frameworks/Python.framework/Versions/3.12/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
cd "%s"
exec "%s" "%s" tether --port %s --user "%s" --pass "%s" --output "%s" --profile "%s" > "%s" 2>&1
]], pluginDir, pyExe, mainPy, tostring(port), username, password, self.inbox_dir, camera_profile, logPath)

    writeTextFile(launcherScript, scriptBody, "w")
    pcall(function()
        LrTasks.execute(string.format('chmod +x "%s"', launcherScript))
    end)

    local launchCmd = string.format('nohup "/bin/bash" "%s" < /dev/null > /dev/null 2>&1 &', launcherScript)
    logger:info("AIthleewFree: Khởi động Tether FTP qua launcher: " .. launchCmd)
    pcall(function()
        LrTasks.execute(launchCmd)
    end)

    local verified = false
    for i = 1, 15 do
        if LrTasks.canYield() then
            LrTasks.sleep(0.3)
        end
        local connData = readTextFile(CONN_FILE)
        if connData and connData ~= "" then
            local parsed = Json.decode(connData)
            if parsed and parsed.status == "running" then
                verified = true
                break
            end
        end
    end

    if verified then
        self:appendConsole(string.format("🟢 FTP Server đã khởi động thành công trên Port %s (Dùng thử 1 tiếng - chỉ tính giờ khi bật).", tostring(port)))
        return true, nil
    else
        self:appendConsole("❌ Không thể xác minh trạng thái Server. Vui lòng xem log bên dưới.")
        return false, "Start verification failed"
    end
end

function TetherServer:stop(port)
    port = port or "2121"
    self:appendConsole(string.format("⏹ Đang dừng FTP Server (Port %s)...", tostring(port)))

    -- Khi dừng server: tích lũy số giây đã chạy vào used_seconds và xóa active_since (dừng countdown)
    local trialContent = readTextFile(TRIAL_FILE)
    if trialContent and trialContent ~= "" then
        local trialData = Json.decode(trialContent)
        if trialData and trialData.active_since then
            local elapsed = os.time() - tonumber(trialData.active_since)
            if elapsed > 0 then
                trialData.used_seconds = (tonumber(trialData.used_seconds) or 0) + elapsed
            end
            trialData.active_since = nil
            if trialData.used_seconds >= MAX_TRIAL_SECONDS then
                trialData.expired = true
                trialData.used_seconds = MAX_TRIAL_SECONDS
            end
            writeTextFile(TRIAL_FILE, Json.encode(trialData), "w")
        end
    end

    pcall(function()
        LrTasks.execute("pkill -9 -f 'python.*tether' 2>/dev/null")
        LrTasks.execute(string.format("/usr/sbin/lsof -ti :%s | xargs kill -9 2>/dev/null", tostring(port)))
    end)
    if LrFileUtils.exists(PID_FILE) then
        pcall(function() LrFileUtils.delete(PID_FILE) end)
    end
    writeTextFile(CONN_FILE, Json.encode({ status = "stopped" }), "w")
    self:appendConsole("⚪ Server đã tắt (Đã tạm dừng đếm ngược thời gian).")
    return true
end

function TetherServer:getStatus()
    local s = {
        running = false,
        ip = "127.0.0.1",
        port = "2121",
        username = "a7",
        password = "12345678",
        files_received = 0,
        last_file = "Chưa có ảnh",
    }

    local connContent = readTextFile(CONN_FILE)
    if connContent and connContent ~= "" then
        local conn = Json.decode(connContent)
        if conn and conn.status == "running" then
            s.running = true
            s.ip = conn.ip or s.ip
            s.port = tostring(conn.port or s.port)
            s.username = conn.username or s.username
            s.password = conn.password or s.password
        end
    end

    local statusContent = readTextFile(STATUS_FILE)
    if statusContent and statusContent ~= "" then
        local stat = Json.decode(statusContent)
        if stat then
            s.files_received = stat.files_received or 0
            s.last_file = stat.last_file or s.last_file
            if stat.ip and stat.ip ~= "" then s.ip = stat.ip end
        end
    end

    return s
end

function TetherServer:getLiveLanIp()
    local tmpOut = LrPathUtils.child(self.base_dir, "lan_ip.tmp")
    pcall(function()
        LrTasks.execute(string.format("/sbin/ifconfig | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2}' | head -n 1 > \"%s\"", tmpOut))
    end)
    local ip = readTextFile(tmpOut)
    if ip then
        ip = ip:gsub("%s+", "")
        if ip ~= "" and not ip:match("^127%.") then
            return ip
        end
    end
    return nil
end

function TetherServer:appendConsole(msg)
    local logPath = LrPathUtils.child(self.base_dir, "tether_server.log")
    local timestamp = os.date("%H:%M:%S")
    local line = string.format("[%s] %s\n", timestamp, msg)
    writeTextFile(logPath, line, "a")
end

function TetherServer:getConsoleLog(maxLines)
    maxLines = maxLines or 50
    local logPath = LrPathUtils.child(self.base_dir, "tether_server.log")
    local content = readTextFile(logPath)
    if not content or content == "" then
        return "Console trống. Bấm 'Khởi động FTP Server' để bắt đầu..."
    end

    local lines = {}
    for line in content:gmatch("[^\r\n]+") do
        table.insert(lines, line)
    end

    local startIdx = math.max(1, #lines - maxLines + 1)
    local out = {}
    for i = startIdx, #lines do
        table.insert(out, lines[i])
    end
    return table.concat(out, "\n")
end

function TetherServer:clearConsole()
    local logPath = LrPathUtils.child(self.base_dir, "tether_server.log")
    writeTextFile(logPath, "", "w")
end

function TetherServer:resetStats()
    local s = { files_received = 0, last_file = "" }
    writeTextFile(STATUS_FILE, Json.encode(s), "w")
end

function TetherServer:openFolder()
    pcall(function()
        LrTasks.execute(string.format('open "%s"', self.base_dir))
    end)
end

return TetherServer
