--[[
    AIthleewFree - Config Utility
    Handles loading and saving plugin configuration for AIthleewFree edition.
]]

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

local logger = Logger:getLogger("Config")

local Config = {}

local DEFAULTS = {
    socket_host = "127.0.0.1",
    socket_port = 9876,
    python_path = "python3",
    use_cloud = true,
    preferred_cloud_model = "meta/llama-3.2-11b-vision-instruct",
    custom_cloud_model = "",
    custom_plugin_name = "AIthleewFree",
    nvidia_api_key = "",
    openrouter_api_key = "",
    kilo_api_key = "",
    auto_analyze_on_select = false,
    preview_size = 1024,
    cache_results = false,
    log_level = "INFO",
}

local current_config = {}

local function getConfigDir()
    local lrConfigPath = LrPathUtils.getStandardFilePath("appData")
    local configPath = LrPathUtils.child(lrConfigPath, "AIthleewFree")
    return configPath
end

local function getConfigPath()
    return LrPathUtils.child(getConfigDir(), "config.json")
end

function Config:load()
    for k, v in pairs(DEFAULTS) do
        current_config[k] = v
    end

    local config_path = getConfigPath()

    if LrFileUtils.exists(config_path) then
        local content = LrFileUtils.readFile(config_path)
        if content and content ~= "" then
            local parsed = Json.decode(content)
            if type(parsed) == "table" then
                for k, v in pairs(parsed) do
                    current_config[k] = v
                end
                logger:info("Configuration loaded from " .. config_path)
            end
        end
    else
        logger:info("Using default configuration for AIthleewFree")
    end

    -- Free edition enforces the single standard model
    current_config.preferred_cloud_model = "meta/llama-3.2-11b-vision-instruct"
    current_config.custom_cloud_model = ""

    -- Fallback to system environment variables if API keys are not present
    if type(os) == "table" and type(os.getenv) == "function" then
        pcall(function()
            if not current_config.nvidia_api_key or current_config.nvidia_api_key == "" then
                local envNv = os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_NIM_API_KEY") or ""
                if envNv ~= "" then
                    current_config.nvidia_api_key = envNv
                end
            end
            if not current_config.openrouter_api_key or current_config.openrouter_api_key == "" then
                local envOr = os.getenv("OPENROUTER_API_KEY") or ""
                if envOr ~= "" then
                    current_config.openrouter_api_key = envOr
                end
            end
            if not current_config.kilo_api_key or current_config.kilo_api_key == "" then
                local envKilo = os.getenv("KILO_API_KEY") or os.getenv("KILO_CODE_API_KEY") or ""
                if envKilo ~= "" then
                    current_config.kilo_api_key = envKilo
                end
            end
        end)
    end

    return current_config
end

function Config:save()
    local config_dir = getConfigDir()
    LrFileUtils.createAllDirectories(config_dir)

    local config_path = getConfigPath()
    local json_str = Json.encode(current_config)

    local file = io.open(config_path, "w")
    if not file then
        logger:error("Failed to open config file for writing: " .. config_path)
        return false
    end

    file:write(json_str)
    file:close()

    logger:info("Configuration saved to " .. config_path)
    return true
end

function Config:get(key)
    if not current_config or next(current_config) == nil then
        self:load()
    end
    return current_config[key]
end

function Config:set(key, value)
    if not current_config or next(current_config) == nil then
        self:load()
    end
    current_config[key] = value
end

function Config:setAll(values)
    if not current_config or next(current_config) == nil then
        self:load()
    end
    if type(values) == "table" then
        for k, v in pairs(values) do
            current_config[k] = v
        end
    end
end

function Config:getAll()
    if not current_config or next(current_config) == nil then
        self:load()
    end
    return current_config
end

function Config:reset()
    for k, v in pairs(DEFAULTS) do
        current_config[k] = v
    end
    logger:info("Configuration reset to defaults")
end

function Config:getPluginName()
    return "AIthleewFree"
end

return Config

