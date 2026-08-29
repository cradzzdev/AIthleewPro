--[[
    AIthleewPro - Task Runner
    Manages the Python AI engine process and provides async task execution.
    Uses file-based communication (no sockets needed).
]]

local LrTasks = import "LrTasks"
local LrPathUtils = import "LrPathUtils"
local LrFileUtils = import "LrFileUtils"

local pluginDir = (_PLUGIN and _PLUGIN.path) or LrPathUtils.child(LrPathUtils.getStandardFilePath("appData"), "Modules/AIthleewPro.lrplugin")
if not LrPathUtils.isAbsolute(pluginDir) or not LrPathUtils.child(pluginDir, "Info.lua") then
    local fallback = LrPathUtils.child(LrPathUtils.getStandardFilePath("appData"), "Modules/AutoColorPro.lrplugin")
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

local logger = Logger:getLogger("TaskRunner")

local TaskRunner = {}
TaskRunner.__index = TaskRunner

local PROCESS_START_TIMEOUT = 10

function TaskRunner:new(opts)
    opts = opts or {}
    local obj = {
        python_path = opts.python_path or Config:get("python_path"),
        process_running = false,
    }
    setmetatable(obj, self)
    return obj
end

function TaskRunner:getPythonExecutable()
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
        "/usr/local/bin/python3",
        "/opt/homebrew/bin/python3",
    }

    local home = nil
    pcall(function()
        home = LrPathUtils.getStandardFilePath("home")
    end)
    if not home and type(os) == "table" and type(os.getenv) == "function" then
        pcall(function()
            home = os.getenv("HOME") or os.getenv("USERPROFILE")
        end)
    end

    if home and home ~= "" then
        table.insert(candidates, LrPathUtils.child(home, ".pyenv/shims/python3"))
        table.insert(candidates, LrPathUtils.child(home, "miniconda3/bin/python3"))
        table.insert(candidates, LrPathUtils.child(home, "anaconda3/bin/python3"))
    end

    for _, p in ipairs(candidates) do
        if LrFileUtils.exists(p) then
            return p
        end
    end

    return configPath or "python3"
end

function TaskRunner:getPythonScriptPath()
    local internalPath = LrPathUtils.child(pluginDir, "python_engine/main.py")
    if LrFileUtils.exists(internalPath) then
        return internalPath
    end

    local parentDir = LrPathUtils.parent(pluginDir)
    if parentDir then
        local siblingPath = LrPathUtils.child(parentDir, "python_engine/main.py")
        if LrFileUtils.exists(siblingPath) then
            return siblingPath
        end
    end

    return internalPath
end

function TaskRunner:ensure_process_running()
    return true
end

function TaskRunner:resolveApiKey(model)
    Config:load()
    local preferred_model = model or Config:get("preferred_cloud_model") or ""
    local isKilo = (
        preferred_model == "thinkingmachines/inkling:free"
        or preferred_model == "stepfun/step-3.7-flash:free"
        or preferred_model == "thinkingmachines/inkling-small:free"
        or string.find(preferred_model, "thinkingmachines")
        or string.find(preferred_model, "kilo")
    )
    local isOpenRouter = (
        not isKilo and (
            preferred_model == "google/gemma-4-31b-it:free"
            or string.find(preferred_model, ":free")
            or string.find(preferred_model, "openrouter")
        )
    )

    local kiloKey = Config:get("kilo_api_key") or ""
    local orKey = Config:get("openrouter_api_key") or ""
    local nimKey = Config:get("nvidia_api_key") or ""

    if isKilo then
        if kiloKey ~= "" then return kiloKey end
        if orKey ~= "" then return orKey end
        if nimKey ~= "" then return nimKey end
    elseif isOpenRouter then
        if orKey ~= "" then return orKey end
        if kiloKey ~= "" then return kiloKey end
        if nimKey ~= "" then return nimKey end
    else
        if nimKey ~= "" then return nimKey end
        if kiloKey ~= "" then return kiloKey end
        if orKey ~= "" then return orKey end
    end
    return ""
end

function TaskRunner:analyze(image_path, options)
    options = options or {}

    if not image_path or not LrFileUtils.exists(image_path) then
        return nil, "Không tìm thấy file ảnh xem trước: " .. tostring(image_path)
    end

    local script_path = self:getPythonScriptPath()
    if not LrFileUtils.exists(script_path) then
        return nil, "Không tìm thấy file python engine: " .. script_path
    end

    local python_bin = self:getPythonExecutable()
    local temp_dir = LrPathUtils.getStandardFilePath("temp")
    local request_id = tostring(os.time()) .. "_" .. tostring(math.random(10000))
    local result_path = LrPathUtils.child(temp_dir, "aithleew_result_" .. request_id .. ".json")
    local err_log_path = LrPathUtils.child(temp_dir, "aithleew_err_" .. request_id .. ".log")

    local preferred_model = options.cloud_model or Config:get("preferred_cloud_model") or ""
    local apiKey = self:resolveApiKey(preferred_model)
    local envPrefix = ""
    if apiKey ~= "" then
        if WIN_ENV then
            envPrefix = string.format('set "NVIDIA_API_KEY=%s" && set "NVIDIA_NIM_API_KEY=%s" && set "OPENROUTER_API_KEY=%s" && set "KILO_API_KEY=%s" && ', apiKey, apiKey, apiKey, apiKey)
        else
            envPrefix = string.format('NVIDIA_API_KEY="%s" NVIDIA_NIM_API_KEY="%s" OPENROUTER_API_KEY="%s" KILO_API_KEY="%s" ', apiKey, apiKey, apiKey, apiKey)
        end
    end

    local pathPrefix = ""
    if not WIN_ENV then
        pathPrefix = 'PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin:/Library/Frameworks/Python.framework/Versions/3.13/bin:/Library/Frameworks/Python.framework/Versions/3.12/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH" '
    end

    local cmd = string.format(
        '%s%s"%s" "%s" analyze "%s" --output "%s" --mode %s',
        pathPrefix,
        envPrefix,
        python_bin,
        script_path,
        image_path,
        result_path,
        options.mode or "full"
    )

    if options.use_cloud then
        cmd = cmd .. " --use-cloud"
        local preferred_model = options.cloud_model or Config:get("preferred_cloud_model")
        if preferred_model and preferred_model ~= "" then
            cmd = cmd .. string.format(' --cloud-model "%s"', preferred_model)
        end
    end

    if apiKey ~= "" then
        cmd = cmd .. string.format(' --api-key "%s"', apiKey)
    end

    if options.scene_hint then
        cmd = cmd .. ' --scene-hint "' .. tostring(options.scene_hint) .. '"'
    end

    if options.intensity and options.intensity ~= "" then
        cmd = cmd .. string.format(' --intensity "%s"', options.intensity)
    end

    if options.is_raw then
        cmd = cmd .. " --is-raw"
    end

    if options.original_ext and options.original_ext ~= "" then
        cmd = cmd .. string.format(' --original-ext "%s"', options.original_ext)
    end

    if options.current_temp ~= nil then
        cmd = cmd .. string.format(' --current-temp %s', tostring(options.current_temp))
    end

    if options.current_tint ~= nil then
        cmd = cmd .. string.format(' --current-tint %s', tostring(options.current_tint))
    end

    cmd = cmd .. string.format(' 2> "%s"', err_log_path)

    logger:info("Running: " .. cmd)

    local exit_code = LrTasks.execute(cmd)

    if LrFileUtils.exists(result_path) then
        local result_content = LrFileUtils.readFile(result_path)
        LrFileUtils.delete(result_path)
        if result_content and result_content ~= "" then
            local response = Json.decode(result_content)
            if response then
                if LrFileUtils.exists(err_log_path) then LrFileUtils.delete(err_log_path) end
                if response.status == "error" then
                    return nil, response.error or "Lỗi phân tích từ AI"
                end
                return response.result or response
            end
        end
    end

    if exit_code ~= 0 then
        local err_detail = ""
        if LrFileUtils.exists(err_log_path) then
            local raw_err = LrFileUtils.readFile(err_log_path)
            if raw_err and raw_err ~= "" then
                err_detail = "\n" .. raw_err
            end
            LrFileUtils.delete(err_log_path)
        end
        logger:error("Python execution failed (code: " .. tostring(exit_code) .. "): " .. err_detail)
        return nil, "Lỗi chạy Python Engine (mã: " .. tostring(exit_code) .. ")" .. (err_detail ~= "" and (": " .. err_detail) or "")
    end

    if LrFileUtils.exists(err_log_path) then
        LrFileUtils.delete(err_log_path)
    end

    return nil, "Không có file kết quả JSON được tạo ra"
end

function TaskRunner:get_python_path()
    return self:getPythonExecutable()
end

function TaskRunner:get_python_script_path()
    return self:getPythonScriptPath()
end

function TaskRunner:cull(image_path, options)
    options = options or {}

    if not image_path or not LrFileUtils.exists(image_path) then
        return nil, "Không tìm thấy file ảnh xem trước: " .. tostring(image_path)
    end

    local script_path = self:getPythonScriptPath()
    if not LrFileUtils.exists(script_path) then
        return nil, "Không tìm thấy file python engine: " .. script_path
    end

    local python_bin = self:getPythonExecutable()

    local temp_dir = LrPathUtils.getStandardFilePath("temp")
    local timestamp = os.time()
    local result_path = LrPathUtils.child(temp_dir, string.format("aithleew_cull_%d_%d.json", timestamp, math.random(1000, 9999)))
    local err_log_path = LrPathUtils.child(temp_dir, string.format("aithleew_cull_err_%d_%d.log", timestamp, math.random(1000, 9999)))

    local preferred_model = options.cloud_model or Config:get("preferred_cloud_model") or ""
    local apiKey = self:resolveApiKey(preferred_model)
    local envPrefix = ""
    if apiKey ~= "" then
        if WIN_ENV then
            envPrefix = string.format('set "NVIDIA_API_KEY=%s" && set "NVIDIA_NIM_API_KEY=%s" && set "OPENROUTER_API_KEY=%s" && set "KILO_API_KEY=%s" && ', apiKey, apiKey, apiKey, apiKey)
        else
            envPrefix = string.format('NVIDIA_API_KEY="%s" NVIDIA_NIM_API_KEY="%s" OPENROUTER_API_KEY="%s" KILO_API_KEY="%s" ', apiKey, apiKey, apiKey, apiKey)
        end
    end

    local pathPrefix = ""
    if not WIN_ENV then
        pathPrefix = 'PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin:/Library/Frameworks/Python.framework/Versions/3.13/bin:/Library/Frameworks/Python.framework/Versions/3.12/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH" '
    end

    local cmd = string.format(
        '%s%s"%s" "%s" cull "%s" --output "%s"',
        pathPrefix,
        envPrefix,
        python_bin,
        script_path,
        image_path,
        result_path
    )

    if options.use_cloud then
        cmd = cmd .. " --use-cloud"
        local preferred_model = options.cloud_model or Config:get("preferred_cloud_model")
        if preferred_model and preferred_model ~= "" then
            cmd = cmd .. string.format(' --cloud-model "%s"', preferred_model)
        end
    end

    if apiKey ~= "" then
        cmd = cmd .. string.format(' --api-key "%s"', apiKey)
    end

    cmd = cmd .. string.format(' 2> "%s"', err_log_path)

    logger:info("Culling command: " .. cmd)

    local exit_code = LrTasks.execute(cmd)

    if LrFileUtils.exists(result_path) then
        local result_content = LrFileUtils.readFile(result_path)
        LrFileUtils.delete(result_path)
        if result_content and result_content ~= "" then
            local response = Json.decode(result_content)
            if response then
                if LrFileUtils.exists(err_log_path) then LrFileUtils.delete(err_log_path) end
                if response.status == "error" then
                    return nil, response.error or "Lỗi chấm điểm ảnh AI"
                end
                return response.result or response
            end
        end
    end

    if exit_code ~= 0 then
        local err_detail = ""
        if LrFileUtils.exists(err_log_path) then
            local raw_err = LrFileUtils.readFile(err_log_path)
            if raw_err and raw_err ~= "" then
                err_detail = "\n" .. raw_err
            end
            LrFileUtils.delete(err_log_path)
        end
        logger:error("Python culling execution failed (code: " .. tostring(exit_code) .. "): " .. err_detail)
        return nil, "Lỗi chạy Python Culling Engine (mã: " .. tostring(exit_code) .. ")" .. (err_detail ~= "" and (": " .. err_detail) or "")
    end

    if LrFileUtils.exists(err_log_path) then
        LrFileUtils.delete(err_log_path)
    end

    return nil, "Không có file kết quả JSON culling"
end

function TaskRunner:analyzeWhiteBalance(image_path, options)
    options = options or {}
    local script_path = self:getPythonScriptPath()
    if not LrFileUtils.exists(script_path) then
        return nil, "Không tìm thấy file python engine: " .. script_path
    end

    local python_bin = self:getPythonExecutable()
    local temp_dir = LrPathUtils.getStandardFilePath("temp")
    local timestamp = os.time()
    local result_path = LrPathUtils.child(temp_dir, string.format("aithleew_wb_%d_%d.json", timestamp, math.random(1000, 9999)))
    local err_log_path = LrPathUtils.child(temp_dir, string.format("aithleew_wb_err_%d_%d.log", timestamp, math.random(1000, 9999)))

    local preferred_model = options.cloud_model or Config:get("preferred_cloud_model") or ""
    local apiKey = self:resolveApiKey(preferred_model)
    local envPrefix = ""
    if apiKey ~= "" then
        if WIN_ENV then
            envPrefix = string.format('set "NVIDIA_API_KEY=%s" && set "NVIDIA_NIM_API_KEY=%s" && set "OPENROUTER_API_KEY=%s" && set "KILO_API_KEY=%s" && ', apiKey, apiKey, apiKey, apiKey)
        else
            envPrefix = string.format('NVIDIA_API_KEY="%s" NVIDIA_NIM_API_KEY="%s" OPENROUTER_API_KEY="%s" KILO_API_KEY="%s" ', apiKey, apiKey, apiKey, apiKey)
        end
    end

    local pathPrefix = ""
    if not WIN_ENV then
        pathPrefix = 'PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin:/Library/Frameworks/Python.framework/Versions/3.13/bin:/Library/Frameworks/Python.framework/Versions/3.12/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH" '
    end

    local cmd = string.format(
        '%s%s"%s" "%s" wb "%s" --output "%s"',
        pathPrefix,
        envPrefix,
        python_bin,
        script_path,
        image_path,
        result_path
    )

    if options.is_raw then
        cmd = cmd .. " --is-raw"
    end
    if options.original_ext and options.original_ext ~= "" then
        cmd = cmd .. string.format(' --original-ext "%s"', options.original_ext)
    end
    if options.current_temp ~= nil then
        cmd = cmd .. string.format(' --current-temp %s', tostring(options.current_temp))
    end
    if options.current_tint ~= nil then
        cmd = cmd .. string.format(' --current-tint %s', tostring(options.current_tint))
    end
    if preferred_model and preferred_model ~= "" then
        cmd = cmd .. string.format(' --cloud-model "%s"', preferred_model)
    end
    if apiKey ~= "" then
        cmd = cmd .. string.format(' --api-key "%s"', apiKey)
    end

    cmd = cmd .. string.format(' 2> "%s"', err_log_path)
    logger:info("White Balance command: " .. cmd)

    local exit_code = LrTasks.execute(cmd)

    if LrFileUtils.exists(result_path) then
        local result_content = LrFileUtils.readFile(result_path)
        LrFileUtils.delete(result_path)
        if result_content and result_content ~= "" then
            local response = Json.decode(result_content)
            if response then
                if LrFileUtils.exists(err_log_path) then LrFileUtils.delete(err_log_path) end
                if response.status == "error" then
                    return nil, response.error or "Lỗi không xác định từ WB Engine"
                end
                return response.result or response
            end
        end
    end

    if exit_code ~= 0 then
        local err_detail = ""
        if LrFileUtils.exists(err_log_path) then
            local raw_err = LrFileUtils.readFile(err_log_path)
            if raw_err and raw_err ~= "" then
                err_detail = "\n" .. raw_err
            end
            LrFileUtils.delete(err_log_path)
        end
        logger:error("Python WB execution failed (code: " .. tostring(exit_code) .. "): " .. err_detail)
        return nil, "Lỗi chạy Python WB Engine (mã: " .. tostring(exit_code) .. ")" .. (err_detail ~= "" and (": " .. err_detail) or "")
    end

    if LrFileUtils.exists(err_log_path) then
        LrFileUtils.delete(err_log_path)
    end

    return nil, "Không có file kết quả JSON WB"
end

function TaskRunner:chat_edit(image_path, prompt, options)
    options = options or {}

    if not image_path or not LrFileUtils.exists(image_path) then
        return nil, "Không tìm thấy file ảnh xem trước: " .. tostring(image_path)
    end

    local script_path = self:getPythonScriptPath()
    if not LrFileUtils.exists(script_path) then
        return nil, "Không tìm thấy file python engine: " .. script_path
    end

    local python_bin = self:getPythonExecutable()

    local temp_dir = LrPathUtils.getStandardFilePath("temp")
    local timestamp = os.time()
    local result_path = LrPathUtils.child(temp_dir, string.format("aithleew_chat_%d_%d.json", timestamp, math.random(1000, 9999)))
    local err_log_path = LrPathUtils.child(temp_dir, string.format("aithleew_chat_err_%d_%d.log", timestamp, math.random(1000, 9999)))
    local prompt_file = LrPathUtils.child(temp_dir, string.format("aithleew_prompt_%d_%d.txt", timestamp, math.random(1000, 9999)))

    local pf = io.open(prompt_file, "w")
    if pf then
        pf:write(prompt or "")
        pf:close()
    end

    local preferred_model = options.cloud_model or Config:get("preferred_cloud_model") or ""
    local apiKey = self:resolveApiKey(preferred_model)
    local envPrefix = ""
    if apiKey ~= "" then
        if WIN_ENV then
            envPrefix = string.format('set "NVIDIA_API_KEY=%s" && set "NVIDIA_NIM_API_KEY=%s" && set "OPENROUTER_API_KEY=%s" && set "KILO_API_KEY=%s" && ', apiKey, apiKey, apiKey, apiKey)
        else
            envPrefix = string.format('NVIDIA_API_KEY="%s" NVIDIA_NIM_API_KEY="%s" OPENROUTER_API_KEY="%s" KILO_API_KEY="%s" ', apiKey, apiKey, apiKey, apiKey)
        end
    end

    local pathPrefix = ""
    if not WIN_ENV then
        pathPrefix = 'PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin:/Library/Frameworks/Python.framework/Versions/3.13/bin:/Library/Frameworks/Python.framework/Versions/3.12/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH" '
    end

    local cmd = string.format(
        '%s%s"%s" "%s" chat-edit "%s" --output "%s" --prompt-file "%s"',
        pathPrefix,
        envPrefix,
        python_bin,
        script_path,
        image_path,
        result_path,
        prompt_file
    )

    if preferred_model and preferred_model ~= "" then
        cmd = cmd .. string.format(' --cloud-model "%s"', preferred_model)
    end

    if apiKey ~= "" then
        cmd = cmd .. string.format(' --api-key "%s"', apiKey)
    end

    cmd = cmd .. string.format(' 2> "%s"', err_log_path)
    logger:info("Chat Edit command: " .. cmd)

    local exit_code = LrTasks.execute(cmd)

    if LrFileUtils.exists(prompt_file) then
        LrFileUtils.delete(prompt_file)
    end

    if LrFileUtils.exists(result_path) then
        local result_content = LrFileUtils.readFile(result_path)
        LrFileUtils.delete(result_path)
        if result_content and result_content ~= "" then
            local response = Json.decode(result_content)
            if response then
                if LrFileUtils.exists(err_log_path) then LrFileUtils.delete(err_log_path) end
                if response.status == "error" then
                    return nil, response.error or "Lỗi từ mô hình AI"
                end
                return response.result or response
            end
        end
    end

    if exit_code ~= 0 then
        local err_detail = ""
        if LrFileUtils.exists(err_log_path) then
            local raw_err = LrFileUtils.readFile(err_log_path)
            if raw_err and raw_err ~= "" then
                err_detail = "\n" .. raw_err
            end
            LrFileUtils.delete(err_log_path)
        end
        logger:error("Python chat-edit execution failed (code: " .. tostring(exit_code) .. "): " .. err_detail)
        return nil, "Lỗi chạy AI Chat Edit (mã: " .. tostring(exit_code) .. ")" .. (err_detail ~= "" and (": " .. err_detail) or "")
    end

    if LrFileUtils.exists(err_log_path) then
        LrFileUtils.delete(err_log_path)
    end

    return nil, "Không có file kết quả JSON từ AI"
end

function TaskRunner:get_presets(category)
    return {
        portraits = {
            {name = "Natural Portrait", settings = {}},
            {name = "Warm Portrait", settings = {}},
        },
        landscapes = {
            {name = "Vivid Landscape", settings = {}},
        },
    }
end

function TaskRunner:get_status()
    return {
        status = "online",
        models_loaded = false,
        cloud_available = true,
    }
end

function TaskRunner:test_connection(api_key, model)
    local python_bin = self:getPythonExecutable()
    local script_path = self:getPythonScriptPath()
    local temp_dir = LrPathUtils.getStandardFilePath("temp")
    local timestamp = os.time()
    local result_path = LrPathUtils.child(temp_dir, string.format("acp_test_conn_%d_%d.json", timestamp, math.random(1000, 9999)))
    local err_log_path = LrPathUtils.child(temp_dir, string.format("acp_test_conn_err_%d_%d.log", timestamp, math.random(1000, 9999)))

    local pathPrefix = ""
    if not WIN_ENV then
        pathPrefix = 'PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin:/Library/Frameworks/Python.framework/Versions/3.13/bin:/Library/Frameworks/Python.framework/Versions/3.12/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/Users/cradzz/.gemini/antigravity/bin:/Users/cradzz/.kilo/bin:/Users/cradzz/.supercode/bin:/Users/cradzz/.local/bin:/Users/cradzz/.antigravity-ide/antigravity-ide/bin:/Users/cradzz/.local/bin:/Users/cradzz/Library/pnpm/bin:/Users/cradzz/.local/bin:/Library/Frameworks/Python.framework/Versions/3.14/bin:/Library/Frameworks/Python.framework/Versions/2.7/bin:/Users/cradzz/.local/bin:/Library/Frameworks/Python.framework/Versions/3.13/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/System/Cryptexes/App/usr/bin:/usr/bin:/bin:/usr/sbin:/sbin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/local/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/appleinternal/bin:/pkg/env/global/bin://Applications/Topaz Photo AI.app/Contents/Resources/bin:/Library/Apple/usr/bin:/Users/cradzz/.cargo/bin:/Users/cradzz/.lmstudio/bin" '
    end

    local cmd = string.format(
        '%s"%s" "%s" test-connection --output "%s"',
        pathPrefix,
        python_bin,
        script_path,
        result_path
    )

    if api_key and api_key ~= "" then
        cmd = cmd .. string.format(' --api-key "%s"', api_key)
    end
    if model and model ~= "" then
        cmd = cmd .. string.format(' --model "%s"', model)
    end

    cmd = cmd .. string.format(' 2> "%s"', err_log_path)

    logger:info("Testing API connection: " .. cmd)
    local exit_code = LrTasks.execute(cmd)

    if LrFileUtils.exists(err_log_path) then
        LrFileUtils.delete(err_log_path)
    end

    if not LrFileUtils.exists(result_path) then
        return false, { error = "Không nhận được phản hồi từ Python Engine. Vui lòng kiểm tra môi trường Python." }
    end

    local result_content = LrFileUtils.readFile(result_path)
    LrFileUtils.delete(result_path)

    local res = Json.decode(result_content)
    if not res then
        return false, { error = "Không thể phân tích dữ liệu JSON phản hồi từ API." }
    end

    if res.status == "ok" then
        return true, res
    else
        return false, res
    end
end

return TaskRunner
